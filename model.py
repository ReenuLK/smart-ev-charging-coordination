"""
model.py
--------
Mesa model and orchestration for the Smart EV Charging Coordination
simulation.
"""

import math

import mesa
import networkx as nx
import numpy as np

from agents import (
    EVAgent,
    GridAgent,
    StationAgent,
    TrafficAgent,
)


class EVChargingModel(mesa.Model):

    def __init__(
        self,
        num_evs=10,
        num_stations=4,
        chargers_per_station=2,
        grid_peak_threshold=10,
        deadlock_timeout=6,
        rng=None,
        seed=None,
    ):

        if rng is None and seed is not None:
            rng = np.random.default_rng(seed)

        super().__init__(rng=rng)

        self.tick = 0

        self.deadlock_timeout = deadlock_timeout

        # ==============================================================
        # Create city road network
        # ==============================================================

        self.graph = self._create_city_graph(
            num_evs=num_evs,
            num_stations=num_stations,
        )

        # ==============================================================
        # Create system-level agents
        # ==============================================================

        self.grid_agent = GridAgent(
            self,
            peak_threshold=grid_peak_threshold,
        )

        self.traffic_agent = TrafficAgent(
            self
        )

        # ==============================================================
        # Create charging stations
        # ==============================================================

        station_nodes = list(
            self.graph.nodes
        )[:num_stations]

        self.stations = []

        for i, node in enumerate(station_nodes):

            station = StationAgent(
                self,
                node=node,
                num_chargers=chargers_per_station,
                base_price=1.0 + i * 0.2,
            )

            self.stations.append(station)

        # ==============================================================
        # Create EVs
        # ==============================================================

        self.evs = []

        for _ in range(num_evs):
            self.add_ev()

        # ==============================================================
        # Data collection
        # ==============================================================

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "AvgQueueLength": self.avg_queue_length,

                "AvgWaitTicks": self.avg_wait_ticks,

                "GridLoad": (
                    lambda model: model.grid_agent.current_load
                ),

                "AvgPrice": self.avg_price,

                "EVsCharging": (
                    lambda model: sum(
                        ev.status == "CHARGING"
                        for ev in model.evs
                    )
                ),

                "EVsDone": (
                    lambda model: sum(
                        ev.status == "DONE"
                        for ev in model.evs
                    )
                ),

                "EVsNegotiating": (
                    lambda model: sum(
                        ev.status == "NEGOTIATING"
                        for ev in model.evs
                    )
                ),

                "EVsQueued": (
                    lambda model: sum(
                        ev.status == "QUEUED"
                        for ev in model.evs
                    )
                ),

                "EVsTraveling": (
                    lambda model: sum(
                        ev.status in (
                            "TRAVELING",
                            "TRAVELING_TO_DEST",
                        )
                        for ev in model.evs
                    )
                ),

                "ThrottledStations": (
                    lambda model: sum(
                        station.throttled
                        for station in model.stations
                    )
                ),
            }
        )

        # Initial data point.
        self.datacollector.collect(self)

    # ==================================================================
    # City graph
    # ==================================================================

    def _create_city_graph(
        self,
        num_evs,
        num_stations,
    ):
        """
        Create a connected road network with alternative routes.

        The original path graph:

            0 -- 1 -- 2 -- 3 -- 4 ...

        had only one possible route between nodes.

        This graph retains the main road but adds shortcut edges,
        allowing A* to make meaningful route decisions.
        """

        required_nodes = max(
            16,
            num_evs + num_stations + 2,
        )

        graph = nx.path_graph(
            required_nodes
        )

        # --------------------------------------------------------------
        # Add alternative road connections.
        # --------------------------------------------------------------

        # Shortcuts of length 2.
        for i in range(
            required_nodes - 2
        ):

            if not graph.has_edge(i, i + 2):

                graph.add_edge(
                    i,
                    i + 2,
                    weight=1.5,
                )

        # Longer shortcuts.
        for i in range(
            required_nodes - 3
        ):

            if i % 2 == 0:

                if not graph.has_edge(
                    i,
                    i + 3,
                ):

                    graph.add_edge(
                        i,
                        i + 3,
                        weight=2.0,
                    )

        # --------------------------------------------------------------
        # Ensure every edge has a valid weight.
        # --------------------------------------------------------------

        for u, v in graph.edges:

            if "weight" not in graph[u][v]:
                graph[u][v]["weight"] = 1.0

        return graph

    # ==================================================================
    # EV creation
    # ==================================================================

    def add_ev(self):

        nodes = list(
            self.graph.nodes
        )

        start_node, dest_node = (
            self.random.sample(
                nodes,
                2,
            )
        )

        ev = EVAgent(
            self,
            start_node=start_node,
            dest_node=dest_node,
            battery=self.random.uniform(
                15,
                60,
            ),
            urgency=self.random.uniform(
                0,
                1,
            ),
        )

        self.evs.append(ev)

        return ev

    # ==================================================================
    # Station discovery
    # ==================================================================

    def get_open_stations(self):

        return [
            station
            for station in self.stations
            if station.operational
        ]

    # ==================================================================
    # Main simulation step
    # ==================================================================

    def step(self):

        # --------------------------------------------------------------
        # 1. EV decisions
        # --------------------------------------------------------------

        for ev in list(self.evs):
            ev.step()

        # --------------------------------------------------------------
        # 2. Station scheduling
        # --------------------------------------------------------------

        for station in self.stations:
            station.step()

        # --------------------------------------------------------------
        # 3. Grid feedback
        # --------------------------------------------------------------

        self.grid_agent.step()

        # --------------------------------------------------------------
        # 4. Traffic dynamics
        # --------------------------------------------------------------

        self.traffic_agent.step()

        # --------------------------------------------------------------
        # 5. Advance simulation clock
        # --------------------------------------------------------------

        self.tick += 1

        # --------------------------------------------------------------
        # 6. Collect telemetry
        # --------------------------------------------------------------

        self.datacollector.collect(self)

    # ==================================================================
    # Dynamic event: new EV arrivals
    # ==================================================================

    def inject_new_arrivals(self, n=6):

        for _ in range(n):
            self.add_ev()

    # ==================================================================
    # Dynamic event: station failure
    # ==================================================================

    def inject_station_failure(self):

        operational = [
            station
            for station in self.stations
            if station.operational
        ]

        if operational:

            failed_station = self.random.choice(
                operational
            )

            failed_station.fail_station()

            return failed_station

        return None

    # ==================================================================
    # Restore stations
    # ==================================================================

    def restore_all_stations(self):

        for station in self.stations:
            station.restore_station()

    # ==================================================================
    # Dynamic event: power outage
    # ==================================================================

    def inject_power_outage(self):

        self.grid_agent.trigger_outage()

    # ==================================================================
    # Clear power outage
    # ==================================================================

    def clear_power_outage(self):

        self.grid_agent.clear_outage()

    # ==================================================================
    # Dynamic event: traffic congestion
    # ==================================================================

    def inject_traffic_congestion(
        self,
        n_edges=3,
    ):

        self.traffic_agent.trigger_congestion(
            n_edges=n_edges
        )

    # ==================================================================
    # Clear traffic congestion
    # ==================================================================

    def clear_traffic_congestion(self):

        self.traffic_agent.clear_congestion()

    # ==================================================================
    # Metrics
    # ==================================================================

    def avg_queue_length(self):

        if not self.stations:
            return 0

        return (
            sum(
                len(station.queue)
                for station in self.stations
            )
            / len(self.stations)
        )

    def avg_wait_ticks(self):

        if not self.evs:
            return 0

        return (
            sum(
                ev.wait_ticks
                for ev in self.evs
            )
            / len(self.evs)
        )

    def avg_price(self):

        if not self.stations:
            return 0

        return (
            sum(
                station.current_price()
                for station in self.stations
            )
            / len(self.stations)
        )