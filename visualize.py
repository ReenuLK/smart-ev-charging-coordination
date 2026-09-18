"""
visualize.py
------------
Streamlit dashboard for the Smart EV Charging Coordination simulation.

Run with:

    streamlit run visualize.py

Provides:

    - Simulation-scale configuration
    - Step / multi-step controls
    - New EV arrival surge
    - Charging-station failure
    - Station restoration
    - Power outage / recovery
    - Traffic congestion / recovery
    - Live telemetry
    - EV state distribution
    - City graph visualization
    - Traffic-weight visualization
    - EV status table
    - Event log
"""

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import streamlit as st

from model import EVChargingModel
from agents import EVAgent


# ==========================================================================
# Page configuration
# ==========================================================================

st.set_page_config(
    page_title="Smart EV Charging Coordination",
    layout="wide",
)

st.title(
    "🔌 Smart EV Charging Coordination — Multi-Agent Simulation"
)


# ==========================================================================
# Helper functions
# ==========================================================================

def initialize_model(
    num_evs,
    num_stations,
    chargers_per_station,
    grid_peak_threshold,
    deadlock_timeout,
):
    """
    Create a new simulation model.
    """

    return EVChargingModel(
        num_evs=num_evs,
        num_stations=num_stations,
        chargers_per_station=chargers_per_station,
        grid_peak_threshold=grid_peak_threshold,
        deadlock_timeout=deadlock_timeout,
        rng=np.random.default_rng(42),
    )


def log_event(message):
    """
    Add an event to the dashboard event log.
    """

    if "log" not in st.session_state:
        st.session_state.log = []

    st.session_state.log.append(
        f"Tick {model.tick}: {message}"
    )


# ==========================================================================
# Sidebar configuration
# ==========================================================================

with st.sidebar:

    st.header("⚙️ Simulation Configuration")

    num_evs = st.slider(
        "Number of EVs",
        min_value=5,
        max_value=50,
        value=14,
    )

    num_stations = st.slider(
        "Number of Stations",
        min_value=2,
        max_value=15,
        value=4,
    )

    chargers_per_station = st.slider(
        "Chargers per Station",
        min_value=1,
        max_value=5,
        value=2,
    )

    grid_peak_threshold = st.slider(
        "Grid Peak Threshold",
        min_value=2,
        max_value=20,
        value=5,
        help=(
            "Maximum aggregate charging power before "
            "demand-response throttling begins."
        ),
    )

    deadlock_timeout = st.slider(
        "Deadlock Timeout (ticks)",
        min_value=2,
        max_value=15,
        value=6,
    )

    st.divider()

    if st.button(
        "🔄 Initialize / Reset Simulation",
        width='stretch',
    ):

        st.session_state.model = initialize_model(
            num_evs=num_evs,
            num_stations=num_stations,
            chargers_per_station=chargers_per_station,
            grid_peak_threshold=grid_peak_threshold,
            deadlock_timeout=deadlock_timeout,
        )

        st.session_state.log = []

        st.rerun()


# ==========================================================================
# Initial model creation
# ==========================================================================

if "model" not in st.session_state:

    st.session_state.model = initialize_model(
        num_evs=num_evs,
        num_stations=num_stations,
        chargers_per_station=chargers_per_station,
        grid_peak_threshold=grid_peak_threshold,
        deadlock_timeout=deadlock_timeout,
    )

    st.session_state.log = []


model = st.session_state.model


# ==========================================================================
# Simulation controls
# ==========================================================================

st.subheader("🎮 Simulation Controls")


# --------------------------------------------------------------------------
# Normal simulation controls
# --------------------------------------------------------------------------

control_row_1 = st.columns(4)


with control_row_1[0]:

    if st.button(
        "▶ Step ×1",
        width='stretch',
    ):

        model.step()


with control_row_1[1]:

    if st.button(
        "⏩ Step ×10",
        width='stretch',
    ):

        for _ in range(10):
            model.step()


with control_row_1[2]:

    if st.button(
        "🚗 Surge +6 EVs",
        width='stretch',
    ):

        model.inject_new_arrivals(6)

        log_event(
            "Surge event — 6 new EVs arrived"
        )


with control_row_1[3]:

    if st.button(
        "💥 Fail Station",
        width='stretch',
    ):

        failed_station = (
            model.inject_station_failure()
        )

        if failed_station:

            log_event(
                f"Station {failed_station.unique_id} "
                f"failed at node {failed_station.node}"
            )

        else:

            log_event(
                "Station failure requested, "
                "but no operational station was available"
            )


# --------------------------------------------------------------------------
# Infrastructure / environmental controls
# --------------------------------------------------------------------------

control_row_2 = st.columns(4)


with control_row_2[0]:

    if st.button(
        "🔧 Restore Stations",
        width='stretch',
    ):

        model.restore_all_stations()

        log_event(
            "All charging stations restored"
        )


with control_row_2[1]:

    if st.button(
        "⚡ Power Outage",
        width='stretch',
    ):

        model.inject_power_outage()

        log_event(
            "Grid-wide power outage triggered"
        )


with control_row_2[2]:

    if st.button(
        "🔋 Clear Outage",
        width='stretch',
    ):

        model.clear_power_outage()

        log_event(
            "Power outage cleared"
        )


with control_row_2[3]:

    if st.button(
        "🚦 Traffic Congestion",
        width='stretch',
    ):

        model.inject_traffic_congestion(
            n_edges=3
        )

        log_event(
            "Traffic congestion injected"
        )


# --------------------------------------------------------------------------
# Traffic recovery
# --------------------------------------------------------------------------

control_row_3 = st.columns(4)


with control_row_3[0]:

    if st.button(
        "🛣️ Clear Traffic",
        width='stretch',
    ):

        model.clear_traffic_congestion()

        log_event(
            "Traffic congestion cleared"
        )


# ==========================================================================
# Current simulation state
# ==========================================================================

st.divider()

st.subheader(
    f"Simulation Tick: {model.tick}"
)


# ==========================================================================
# Model telemetry
# ==========================================================================

df = model.datacollector.get_model_vars_dataframe()


if not df.empty:

    latest = df.iloc[-1]

    # ----------------------------------------------------------------------
    # Primary metrics
    # ----------------------------------------------------------------------

    metric_cols = st.columns(4)

    metric_cols[0].metric(
        "Avg Queue Length",
        f"{latest['AvgQueueLength']:.2f}",
    )

    metric_cols[1].metric(
        "Avg Wait",
        f"{latest['AvgWaitTicks']:.2f} ticks",
    )

    metric_cols[2].metric(
        "Grid Load",
        f"{latest['GridLoad']:.2f}",
    )

    metric_cols[3].metric(
        "Avg Price",
        f"${latest['AvgPrice']:.2f}",
    )


    # ----------------------------------------------------------------------
    # Secondary metrics
    # ----------------------------------------------------------------------

    metric_cols_2 = st.columns(5)

    metric_cols_2[0].metric(
        "EVs Charging",
        int(latest["EVsCharging"]),
    )

    metric_cols_2[1].metric(
        "EVs Queued",
        int(latest["EVsQueued"]),
    )

    metric_cols_2[2].metric(
        "EVs Negotiating",
        int(latest["EVsNegotiating"]),
    )

    metric_cols_2[3].metric(
        "EVs Traveling",
        int(latest["EVsTraveling"]),
    )

    metric_cols_2[4].metric(
        "EVs Done",
        int(latest["EVsDone"]),
    )


    # ----------------------------------------------------------------------
    # Infrastructure metrics
    # ----------------------------------------------------------------------

    metric_cols_3 = st.columns(3)

    metric_cols_3[0].metric(
        "Throttled Stations",
        int(latest["ThrottledStations"]),
    )

    metric_cols_3[1].metric(
        "Operational Stations",
        sum(
            station.operational
            for station in model.stations
        ),
    )

    metric_cols_3[2].metric(
        "Congested Roads",
        len(
            model.traffic_agent.congested_edges
        ),
    )


# ==========================================================================
# Charts
# ==========================================================================

if not df.empty:

    st.subheader("📊 Simulation Telemetry")

    # ----------------------------------------------------------------------
    # Queue / waiting
    # ----------------------------------------------------------------------

    chart_col_1, chart_col_2 = st.columns(2)

    with chart_col_1:

        st.markdown("**Queue & Waiting Time**")

        st.line_chart(
            df[
                [
                    "AvgQueueLength",
                    "AvgWaitTicks",
                ]
            ]
        )

    # ----------------------------------------------------------------------
    # Grid / pricing
    # ----------------------------------------------------------------------

    with chart_col_2:

        st.markdown("**Grid Load & Charging Price**")

        st.line_chart(
            df[
                [
                    "GridLoad",
                    "AvgPrice",
                ]
            ]
        )


    # ----------------------------------------------------------------------
    # EV states
    # ----------------------------------------------------------------------

    st.markdown("**EV State Distribution**")

    state_columns = [
        "EVsCharging",
        "EVsQueued",
        "EVsNegotiating",
        "EVsTraveling",
        "EVsDone",
    ]

    st.line_chart(
        df[state_columns]
    )


    # ----------------------------------------------------------------------
    # Grid throttling
    # ----------------------------------------------------------------------

    st.markdown(
        "**Grid Demand-Response Activity**"
    )

    st.line_chart(
        df[
            [
                "GridLoad",
                "ThrottledStations",
            ]
        ]
    )


# ==========================================================================
# City graph
# ==========================================================================

st.divider()

st.subheader(
    "🗺️ City Graph & Traffic State"
)

st.caption(
    "Green = operational station | "
    "Orange = throttled station | "
    "Red = failed station | "
    "Darker/thicker roads = higher traffic weight"
)


fig, ax = plt.subplots(
    figsize=(12, 7)
)


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------

pos = nx.spring_layout(
    model.graph,
    seed=42,
    k=1.5,
)


# --------------------------------------------------------------------------
# Draw normal graph edges
# --------------------------------------------------------------------------

normal_edges = []
congested_edges = []

for u, v in model.graph.edges():

    if (u, v) in model.traffic_agent.congested_edges:

        congested_edges.append((u, v))

    else:

        normal_edges.append((u, v))


# Normal roads.

nx.draw_networkx_edges(
    model.graph,
    pos,
    edgelist=normal_edges,
    ax=ax,
    width=1.5,
)


# Congested roads.

if congested_edges:

    nx.draw_networkx_edges(
        model.graph,
        pos,
        edgelist=congested_edges,
        ax=ax,
        width=4,
    )


# --------------------------------------------------------------------------
# Draw all nodes
# --------------------------------------------------------------------------

nx.draw_networkx_nodes(
    model.graph,
    pos,
    ax=ax,
    node_size=400,
)


# --------------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------------

nx.draw_networkx_labels(
    model.graph,
    pos,
    ax=ax,
    font_size=8,
)


# --------------------------------------------------------------------------
# Station nodes
# --------------------------------------------------------------------------

station_nodes = []
station_colors = []

for station in model.stations:

    station_nodes.append(
        station.node
    )

    if not station.operational:

        station_colors.append("red")

    elif station.throttled:

        station_colors.append("orange")

    else:

        station_colors.append("green")


nx.draw_networkx_nodes(
    model.graph,
    pos,
    nodelist=station_nodes,
    node_color=station_colors,
    node_size=700,
    edgecolors="black",
    ax=ax,
)


# --------------------------------------------------------------------------
# EV locations
# --------------------------------------------------------------------------

ev_positions = [
    ev.pos_node
    for ev in model.evs
    if ev.status != "DONE"
]

if ev_positions:

    nx.draw_networkx_nodes(
        model.graph,
        pos,
        nodelist=ev_positions,
        node_color="blue",
        node_size=120,
        alpha=0.7,
        ax=ax,
    )


ax.set_axis_off()

st.pyplot(
    fig,
    width='stretch',
)

plt.close(fig)


# ==========================================================================
# Traffic information
# ==========================================================================

st.subheader(
    "🚦 Traffic Information"
)

traffic_rows = []

for u, v, data in model.graph.edges(
    data=True
):

    traffic_rows.append(
        {
            "Road": f"{u} → {v}",
            "Weight / ETA": round(
                data["weight"],
                2,
            ),
            "Congested": (
                (u, v)
                in model.traffic_agent.congested_edges
            ),
        }
    )

if traffic_rows:

    st.dataframe(
        traffic_rows,
        width='stretch',
        height=250,
    )


# ==========================================================================
# Charging station information
# ==========================================================================

st.subheader(
    "🔌 Charging Station Status"
)

station_rows = []

for station in model.stations:

    station_rows.append(
        {
            "Station": station.unique_id,
            "Node": station.node,
            "Operational": station.operational,
            "Throttled": station.throttled,
            "Chargers": station.num_chargers,
            "Available": station.available_chargers,
            "Charging": len(
                station.charging
            ),
            "Queue": len(
                station.queue
            ),
            "Price": round(
                station.current_price(),
                2,
            ),
        }
    )

st.dataframe(
    station_rows,
    width='stretch',
)


# ==========================================================================
# Event log
# ==========================================================================

st.subheader(
    "📜 Event Log"
)

if st.session_state.log:

    for entry in reversed(
        st.session_state.log[-15:]
    ):

        st.text(entry)

else:

    st.caption(
        "No manually triggered events yet."
    )


# ==========================================================================
# EV status table
# ==========================================================================

st.subheader(
    "🚗 EV Status"
)


ev_rows = []

for ev in model.evs:

    target_station = (
        str(ev.target_station.unique_id)
        if ev.target_station
        else "-"
    )

    ev_rows.append(
        {
            "EV": ev.unique_id,
            "Status": ev.status,
            "Current Node": ev.pos_node,
            "Destination": ev.dest_node,
            "Battery": round(
                ev.battery,
                1,
            ),
            "Urgency": round(
                ev.urgency,
                2,
            ),
            "Wait Ticks": ev.wait_ticks,
            "Deadlock Timer": ev.deadlock_timer,
            "Target Station": target_station,
        }
    )


st.dataframe(
    ev_rows,
    width='stretch',
    height=350,
)


# ==========================================================================
# Explanation panel
# ==========================================================================

st.divider()

with st.expander(
    "ℹ️ How the Multi-Agent Decision Process Works"
):

    st.markdown(
        """
### EV decision process

Each EV independently evaluates available charging stations.

**1. Discover stations**

Only operational stations are considered.

**2. Route planning**

The EV calculates an A* route to every candidate station.

**3. Traffic-aware ETA**

Current road weights are used to estimate travel time.

**4. Constraint filtering**

A station is rejected if the EV cannot reach it while maintaining
the required battery reserve.

**5. Station negotiation**

Each feasible station provides:

- charging price
- estimated waiting time

**6. Utility calculation**

The EV evaluates:

`Utility = -(price + urgency-weighted wait + travel cost)`

The highest-utility feasible station is selected.

**7. Queueing and charging**

The station manages its own charger allocation and queue.

**8. Grid feedback**

If aggregate charging power exceeds the grid threshold,
selected stations are throttled.

**9. Dynamic adaptation**

Station failure, power outages, traffic congestion, and queue
deadlocks can trigger EV renegotiation.

**10. Destination**

After charging, the EV uses A* again to travel to its final
destination.
"""
    )