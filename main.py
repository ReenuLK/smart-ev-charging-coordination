"""
main.py
-------
Quick terminal-based run of the Smart EV Charging Coordination simulation.

Demonstrates:

    1. Normal operation
    2. Surge / stress test with new EV arrivals
    3. Traffic congestion
    4. Charging-station failure
    5. Power-grid outage and recovery

The terminal output provides telemetry for each tick.
"""

from model import EVChargingModel


# ==========================================================================
# Simulation
# ==========================================================================

def run_demo(ticks=35):

    model = EVChargingModel(
        num_evs=10,
        num_stations=4,
        chargers_per_station=2,
        grid_peak_threshold=8,
        deadlock_timeout=6,
        seed=42,
    )

    # ======================================================================
    # Scenario 1 — Normal operation
    # ======================================================================

    print("=" * 70)
    print("SCENARIO 1: NORMAL OPERATION")
    print("=" * 70)

    for t in range(1, 9):

        model.step()

        report(model, t)

    # ======================================================================
    # Scenario 2 — New EV arrivals
    # ======================================================================

    print("\n" + "=" * 70)
    print("SCENARIO 2: SURGE / STRESS TEST")
    print("=" * 70)

    print("Injecting 6 new EVs...")

    model.inject_new_arrivals(n=6)

    for t in range(9, 17):

        model.step()

        report(model, t)

    # ======================================================================
    # Scenario 3 — Traffic congestion
    # ======================================================================

    print("\n" + "=" * 70)
    print("SCENARIO 3: TRAFFIC CONGESTION")
    print("=" * 70)

    print("Injecting traffic congestion...")

    model.inject_traffic_congestion(
        n_edges=3
    )

    for t in range(17, 21):

        model.step()

        report(model, t)

    # ======================================================================
    # Scenario 4 — Charging station failure
    # ======================================================================

    print("\n" + "=" * 70)
    print("SCENARIO 4: CHARGING-STATION FAILURE")
    print("=" * 70)

    failed_station = model.inject_station_failure()

    if failed_station:

        print(
            f"Station {failed_station.unique_id} "
            f"at node {failed_station.node} failed."
        )

    else:

        print("No operational station available for failure.")

    for t in range(21, 26):

        model.step()

        report(model, t)

    # ======================================================================
    # Scenario 5 — Power outage
    # ======================================================================

    print("\n" + "=" * 70)
    print("SCENARIO 5: POWER-GRID OUTAGE")
    print("=" * 70)

    print("Triggering power outage...")

    model.inject_power_outage()

    for t in range(26, 29):

        model.step()

        report(model, t)

    # ======================================================================
    # Scenario 6 — Recovery
    # ======================================================================

    print("\n" + "=" * 70)
    print("SCENARIO 6: SYSTEM RECOVERY")
    print("=" * 70)

    print("Clearing power outage...")
    model.clear_power_outage()

    print("Restoring charging stations...")
    model.restore_all_stations()

    print("Clearing traffic congestion...")
    model.clear_traffic_congestion()

    for t in range(29, ticks + 1):

        model.step()

        report(model, t)

    # ======================================================================
    # Final summary
    # ======================================================================

    print("\n" + "=" * 70)
    print("FINAL SIMULATION SUMMARY")
    print("=" * 70)

    final_report(model)

    print("\nSimulation complete.")


# ==========================================================================
# Per-tick telemetry
# ==========================================================================

def report(model, t):

    status_counts = {
        "TRAVELING": 0,
        "NEGOTIATING": 0,
        "QUEUED": 0,
        "CHARGING": 0,
        "TRAVELING_TO_DEST": 0,
        "DONE": 0,
    }

    for ev in model.evs:

        if ev.status in status_counts:
            status_counts[ev.status] += 1

    operational_stations = sum(
        station.operational
        for station in model.stations
    )

    throttled_stations = sum(
        station.throttled
        for station in model.stations
    )

    print(
        {
            "tick": t,
            "avg_queue": round(
                model.avg_queue_length(),
                2,
            ),
            "avg_wait": round(
                model.avg_wait_ticks(),
                2,
            ),
            "grid_load": round(
                model.grid_agent.current_load,
                2,
            ),
            "avg_price": round(
                model.avg_price(),
                2,
            ),
            "operational_stations": operational_stations,
            "throttled_stations": throttled_stations,
            "EVs": status_counts,
        }
    )


# ==========================================================================
# Final summary
# ==========================================================================

def final_report(model):

    total_evs = len(model.evs)

    completed = sum(
        ev.status == "DONE"
        for ev in model.evs
    )

    charging = sum(
        ev.status == "CHARGING"
        for ev in model.evs
    )

    queued = sum(
        ev.status == "QUEUED"
        for ev in model.evs
    )

    negotiating = sum(
        ev.status == "NEGOTIATING"
        for ev in model.evs
    )

    traveling = sum(
        ev.status in (
            "TRAVELING",
            "TRAVELING_TO_DEST",
        )
        for ev in model.evs
    )

    print(
        f"Total EVs             : {total_evs}"
    )

    print(
        f"Completed             : {completed}"
    )

    print(
        f"Traveling             : {traveling}"
    )

    print(
        f"Negotiating           : {negotiating}"
    )

    print(
        f"Queued                : {queued}"
    )

    print(
        f"Charging             : {charging}"
    )

    print(
        f"Average queue length  : "
        f"{model.avg_queue_length():.2f}"
    )

    print(
        f"Average wait ticks    : "
        f"{model.avg_wait_ticks():.2f}"
    )

    print(
        f"Current grid load     : "
        f"{model.grid_agent.current_load:.2f}"
    )

    print(
        f"Average station price : "
        f"{model.avg_price():.2f}"
    )


# ==========================================================================
# Entry point
# ==========================================================================

if __name__ == "__main__":
    run_demo()