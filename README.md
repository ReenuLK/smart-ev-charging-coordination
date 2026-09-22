# Smart EV Charging Coordination

A multi-agent simulation framework for optimizing electric vehicle charging decisions in a smart city environment. The project models EVs, charging stations, the power grid, and traffic conditions as interacting agents that respond dynamically to congestion, station failures, grid stress, and demand spikes.

This application demonstrates how intelligent coordination can reduce waiting times, manage charging demand, and adapt to real-world disruptions in a distributed EV charging ecosystem.

---

## 1. Project Title & Description

### Smart EV Charging Coordination

The system simulates a network of electric vehicles trying to find and charge at the most suitable station while balancing:

- vehicle battery constraints
- station queue lengths and pricing
- power grid load limits
- traffic travel time and route conditions
- station failures and outages

The simulation is built using the Mesa agent-based modeling framework and uses NetworkX for city-road routing and path planning. It can be run in two modes:

- terminal-based scenario execution via `main.py`
- interactive dashboard via `visualize.py`

---

## 2. Key Features

- Multi-agent EV scheduling and charging negotiation
- Dynamic station pricing based on queue length and grid conditions
- Queue management and charger allocation for each station
- Grid demand-response logic with throttling when load exceeds threshold
- Traffic congestion simulation that alters route weights and travel times
- Randomized disruption events such as:
  - new EV arrivals
  - station failures
  - power outages
  - traffic spikes
- Real-time simulation telemetry and status metrics
- Interactive Streamlit dashboard for monitoring system behavior
- Clear event logging and EV state tracking over time

---

## 3. Tech Stack Used

- Python 3
- Mesa - agent-based simulation framework
- NetworkX - graph routing and shortest-path planning
- NumPy - random generation and simulation data support
- Streamlit - interactive visualization dashboard
- Matplotlib - graph and network plotting

### Core project files

- `main.py` - terminal demo of simulation scenarios
- `model.py` - model orchestration and environment setup
- `agents.py` - EV, station, grid, and traffic agent logic
- `visualize.py` - Streamlit dashboard user interface
- `requirements.txt` - Python dependencies

---

## 4. Step-by-step Setup & Installation Instructions

### Prerequisites

- Python 3.9 or newer
- pip package manager
- A terminal or command prompt

### Step 1: Open the project folder

Navigate to the root directory of the project in your terminal:

```bash
cd smart-ev-charging-coordination
```

### Step 2: Create a virtual environment

It is recommended to create an isolated environment before installing dependencies:

```bash
python -m venv .venv
```

### Step 3: Activate the virtual environment

On Windows (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

On Windows (Command Prompt):

```cmd
.venv\Scripts\activate.bat
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

### Step 4: Install project dependencies

```bash
pip install -r requirements.txt
```

If you want to upgrade the package installer first:

```bash
python -m pip install --upgrade pip
```

### Step 5: Run the terminal simulation

To execute the command-line demo with pre-defined scenarios:

```bash
python main.py
```

This will simulate:

- normal operation
- EV surge / stress test
- traffic congestion
- station failure
- power outage
- recovery and final summary

### Step 6: Run the interactive dashboard

To launch the Streamlit app:

```bash
streamlit run visualize.py
```

Then open the local URL shown in the terminal, typically:

```text
http://localhost:8501
```

### Step 7: Use the dashboard

The dashboard lets you:

- adjust EV count, stations, chargers, and grid threshold
- step the simulation manually
- trigger new EV surges
- fail or restore stations
- simulate outages and traffic events
- visualize queue growth, charging load, station status, and EV state transitions

---

## Example Workflow

1. Install dependencies.
2. Run the CLI simulation to inspect scenario behavior:
   ```bash
   python main.py
   ```
3. Launch the dashboard for an interactive view:
   ```bash
   streamlit run visualize.py
   ```
4. Tune the simulation parameters and observe how the system reacts to environmental and operational stress.

---

## Project Outcome

This project demonstrates how agent-based coordination can model a realistic smart charging network where EVs negotiate for charging access while the grid and road network impose dynamic constraints. It is useful for understanding how decentralized decision-making can be used to manage energy demand, reduce congestion, and improve reliability in EV infrastructure.
