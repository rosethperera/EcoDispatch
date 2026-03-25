# EcoDispatch Presentation Guide

## Safe Opening

"EcoDispatch is a simulation prototype for exploring how data centers might coordinate grid power, solar, battery storage, and flexible workloads to study carbon and cost tradeoffs."

## 5-Minute Demo Flow

### 1. Problem

- Data centers use large amounts of electricity.
- Grid carbon intensity and electricity price change hour by hour.
- Solar and batteries add flexibility, but they also add operational complexity.

### 2. What the prototype does

- Simulates hourly demand, solar, battery, carbon intensity, and price.
- Compares five dispatch strategies on the same demand profile.
- Shows emissions, cost, peak grid draw, renewable share, load served, and unmet demand.

### 3. Demo commands

```bash
python demo.py
```

```bash
streamlit run dashboard.py
```

### 4. What to point out

- The project is a scenario-analysis tool, not a production controller.
- The dashboard now exposes strategy logic more honestly.
- The comparison is auditable because load-served and unmet-demand are shown explicitly.
- Scenario presets help make the differences between strategies easier to inspect.

## Technical Talking Points

- Time-series simulation in Python.
- Battery state-of-charge tracking and simple degradation effects.
- Weather-aware solar generation model.
- Flexible workload shifting experiments.
- Strategy-specific charging and discharging behavior.
- Rolling-horizon optimized dispatch logic.
- Optional real weather and optional Electricity Maps inputs.

## Safe Claims

- "Prototype"
- "Simulation platform"
- "Scenario-analysis tool"
- "Compares five strategies"
- "Includes a Streamlit dashboard"
- "Supports optional external data feeds"

## Claims To Avoid

- Any fixed universal savings percentages.
- "Production-ready"
- "Validated with real operator deployment"
- "98% test coverage" or "42 tests"
- "Live deployment" unless you separately verify it.
