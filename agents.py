"""
agents.py
---------
Defines all agent classes for the Smart EV Charging Coordination simulation:
    - EVAgent: an electric vehicle seeking a charge
    - StationAgent: a charging station managing a queue and pricing
    - GridAgent: the power grid, monitoring and throttling total load
    - TrafficAgent: predicts congestion and adjusts travel time estimates

Built for Mesa 3.x, where agents are created as `Agent(model)` and
automatically registered in `model.agents` (an AgentSet) — no manual
scheduler bookkeeping required.
"""

import math
import random
import networkx as nx
import mesa


ENERGY_PER_TICK = 0.5
SAFETY_RESERVE = 5
NORMAL_CHARGING_POWER = 1.0
THROTTLED_CHARGING_POWER = 0.5


# --------------------------------------------------------------------------
# Utility helpers
# --------------------------------------------------------------------------

def ev_utility(price, wait_estimate, eta, urgency):
    """
    Utility function used by an EV to score a station offer.
    Higher urgency makes the EV penalize waiting time more heavily.
    Returns a score where HIGHER is better for the EV.
    """
    price_weight = 1.0
    wait_weight = 0.5 + urgency
    travel_weight = 0.3
    return -(
        price_weight * price
        + wait_weight * wait_estimate
        + travel_weight * eta
    )


# --------------------------------------------------------------------------
# Electric Vehicle Agent
# --------------------------------------------------------------------------

class EVAgent(mesa.Agent):
    """
    Represents a single electric vehicle.

    State machine: TRAVELING -> NEGOTIATING -> QUEUED -> CHARGING ->
    TRAVELING_TO_DEST -> DONE
    """

    def __init__(self, model, start_node, dest_node, battery=None, urgency=None):
        super().__init__(model)
        self.pos_node = start_node
        self.dest_node = dest_node
        self.battery = battery if battery is not None else self.random.uniform(15, 60)
        self.urgency = urgency if urgency is not None else self.random.uniform(0, 1)
        self.status = "TRAVELING"
        self.target_station = None
        self.wait_ticks = 0
        self.charge_ticks_needed = 0
        self.path = []
        self.deadlock_timer = 0

    # ---- decision logic -------------------------------------------------

    def plan_route(self):
        """Use A* (via NetworkX) to plan a path toward the destination or a station."""
        try:
            self.path = nx.astar_path(
                self.model.graph,
                self.pos_node,
                self.dest_node,
                heuristic=self.astar_heuristic,
                weight="weight",
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            self.path = [self.pos_node]

    @staticmethod
    def astar_heuristic(node, target):
        return abs(node - target) if isinstance(node, int) and isinstance(target, int) else 0

    def move_along_path(self):
        if len(self.path) > 1:
            self.path.pop(0)
            self.pos_node = self.path[0]

    def get_station_route_info(self, station):
        try:
            path = nx.astar_path(
                self.model.graph,
                self.pos_node,
                station.node,
                heuristic=self.astar_heuristic,
                weight="weight",
            )
            eta = self.model.traffic_agent.predict_eta(path)
            return path, eta
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None, float("inf")

    def can_reach_station(self, eta):
        required_battery = eta * ENERGY_PER_TICK
        return self.battery >= required_battery + SAFETY_RESERVE

    def request_charge(self):
        """
        Contract-net style negotiation:
        EV broadcasts urgency + battery to nearby stations, collects offers,
        picks the best by utility function.
        """
        candidates = self.model.get_open_stations()
        if not candidates:
            return  # no stations available this tick, stay in queue-seeking mode

        offers = []
        for station in candidates:
            path, eta = self.get_station_route_info(station)
            if path is None or not self.can_reach_station(eta):
                continue

            price, wait_est = station.make_offer(self)
            score = ev_utility(price, wait_est, eta, self.urgency)
            offers.append((score, station, price, wait_est, eta, path))

        if not offers:
            return

        offers.sort(key=lambda x: x[0], reverse=True)
        best_score, best_station, price, wait_est, eta, path = offers[0]

        self.target_station = best_station
        self.path = path
        if self.pos_node == best_station.node and best_station.accept_ev(self):
            self.path = []
            self.target_station = best_station
            self.status = "QUEUED"
        else:
            self.status = "TRAVELING"

    def handle_renegotiation(self):
        """Triggered when the assigned station fails or becomes unavailable mid-wait/charge."""
        self.status = "NEGOTIATING"
        self.target_station = None
        self.path = []
        self.deadlock_timer = 0

    def step(self):
        if self.status == "TRAVELING":
            if not self.path:
                if self.target_station:
                    self.path, _ = self.get_station_route_info(self.target_station)
                    if self.path is None:
                        self.handle_renegotiation()
                        return
                else:
                    self.plan_route()

            self.move_along_path()
            self.battery = max(0, self.battery - self.random.uniform(0.5, 1.5))

            if self.target_station and self.pos_node == self.target_station.node:
                if self.target_station.accept_ev(self):
                    self.status = "QUEUED"
                    self.path = []
                else:
                    self.handle_renegotiation()
            elif self.battery < 30 or self.pos_node == self.dest_node:
                self.status = "NEGOTIATING"

        elif self.status == "NEGOTIATING":
            self.request_charge()

        elif self.status == "QUEUED":
            self.wait_ticks += 1
            self.deadlock_timer += 1
            # Deadlock resolution: if stuck waiting too long, abandon and re-negotiate
            if self.deadlock_timer > self.model.deadlock_timeout:
                if self.target_station:
                    self.target_station.remove_from_queue(self)
                self.handle_renegotiation()

        elif self.status == "CHARGING":
            if self.target_station and self.target_station.throttled:
                charge_rate = self.random.uniform(4, 8)
            else:
                charge_rate = self.random.uniform(8, 15)
            self.charge_ticks_needed -= 1
            self.battery = min(100, self.battery + charge_rate)
            if self.charge_ticks_needed <= 0 or self.battery >= 100:
                if self.target_station:
                    self.target_station.release_charger(self)
                self.target_station = None
                self.path = []
                self.status = "TRAVELING_TO_DEST"

        elif self.status == "TRAVELING_TO_DEST":
            if not self.path:
                self.plan_route()
            self.move_along_path()
            self.battery = max(0, self.battery - self.random.uniform(0.5, 1.5))
            if self.pos_node == self.dest_node:
                self.status = "DONE"


# --------------------------------------------------------------------------
# Charging Station Agent
# --------------------------------------------------------------------------

class StationAgent(mesa.Agent):
    """
    Manages a fixed number of chargers, a waiting queue, and dynamic pricing.
    """

    def __init__(self, model, node, num_chargers=2, base_price=1.0):
        super().__init__(model)
        self.node = node
        self.num_chargers = num_chargers
        self.available_chargers = num_chargers
        self.base_price = base_price
        self.queue = []
        self.charging = []  # EVs currently charging here
        self.operational = True
        self.throttled = False

    def current_price(self):
        """Surge pricing: price rises with queue length and grid throttling."""
        surge = 1 + 0.15 * len(self.queue)
        if self.throttled:
            surge *= 1.5
        return round(self.base_price * surge, 2)

    def make_offer(self, ev_agent):
        price = self.current_price()
        total_ahead = len(self.queue)
        busy = len(self.charging)
        available = max(1, self.num_chargers)
        batches = math.ceil((total_ahead + busy) / available)
        wait_estimate = batches * 4
        return price, wait_estimate

    def accept_ev(self, ev_agent):
        if not self.operational:
            return False
        self.queue.append(ev_agent)
        return True

    def remove_from_queue(self, ev_agent):
        if ev_agent in self.queue:
            self.queue.remove(ev_agent)

    def release_charger(self, ev_agent):
        if ev_agent in self.charging:
            self.charging.remove(ev_agent)
            self.available_chargers += 1

    def fail_station(self):
        """Simulate a station failure (dynamic event)."""
        self.operational = False
        for ev in list(self.queue) + list(self.charging):
            ev.handle_renegotiation()
        self.queue.clear()
        self.charging.clear()
        self.available_chargers = 0
        self.throttled = False

    def restore_station(self):
        self.operational = True
        self.throttled = False
        self.available_chargers = self.num_chargers - len(self.charging)

    def step(self):
        if not self.operational:
            return

        # Promote queued EVs into free chargers
        while self.available_chargers > 0 and self.queue:
            ev = self.queue.pop(0)
            ev.status = "CHARGING"
            ev.charge_ticks_needed = self.random.randint(3, 6)
            self.available_chargers -= 1
            self.charging.append(ev)

        power = THROTTLED_CHARGING_POWER if self.throttled else NORMAL_CHARGING_POWER
        self.model.grid_agent.report_load(self, len(self.charging) * power)


# --------------------------------------------------------------------------
# Power Grid Agent
# --------------------------------------------------------------------------

class GridAgent(mesa.Agent):
    """
    Monitors aggregate load across all stations and throttles stations
    that push total demand above the safe peak threshold.
    """

    def __init__(self, model, peak_threshold=10):
        super().__init__(model)
        self.peak_threshold = peak_threshold
        self.current_load = 0
        self._load_this_tick = {}
        self.outage = False

    def report_load(self, station, active_chargers):
        self._load_this_tick[station.unique_id] = active_chargers

    def trigger_outage(self):
        self.outage = True

    def clear_outage(self):
        self.outage = False

    def step(self):
        self.current_load = sum(self._load_this_tick.values())
        self._load_this_tick = {}

        stations = [a for a in self.model.agents if isinstance(a, StationAgent)]

        if self.outage:
            for s in stations:
                for ev in list(s.queue) + list(s.charging):
                    ev.handle_renegotiation()
                s.queue.clear()
                s.charging.clear()
                s.available_chargers = 0
                s.throttled = True
                s.operational = False
            return

        if self.current_load > self.peak_threshold:
            # Throttle the busiest stations first (demand-response)
            stations_sorted = sorted(stations, key=lambda s: len(s.charging), reverse=True)
            for s in stations_sorted[: max(1, len(stations_sorted) // 3)]:
                s.throttled = True
        else:
            for s in stations:
                s.throttled = False


# --------------------------------------------------------------------------
# Traffic Agent
# --------------------------------------------------------------------------

class TrafficAgent(mesa.Agent):
    """
    Predicts congestion by randomly adjusting edge weights on the city graph,
    simulating traffic build-up and dissipation over time.
    """

    def __init__(self, model):
        super().__init__(model)
        self.congested_edges = set()
        self.base_weights = {
            (u, v): data["weight"]
            for u, v, data in model.graph.edges(data=True)
        }

    def trigger_congestion(self, n_edges=3):
        edges = list(self.model.graph.edges())
        chosen = self.random.sample(edges, min(n_edges, len(edges)))
        for u, v in chosen:
            self.model.graph[u][v]["weight"] = self.base_weights[(u, v)] * 3
            self.congested_edges.add((u, v))

    def clear_congestion(self):
        for u, v in self.congested_edges:
            self.model.graph[u][v]["weight"] = self.base_weights[(u, v)]
        self.congested_edges.clear()

    def predict_eta(self, path):
        """Sum weighted edges along a path as a naive ETA prediction."""
        total = 0
        for i in range(len(path) - 1):
            total += self.model.graph[path[i]][path[i + 1]]["weight"]
        return total

    def step(self):
        # Small random chance of organic congestion each tick
        if self.random.random() < 0.05:
            self.trigger_congestion(n_edges=1)