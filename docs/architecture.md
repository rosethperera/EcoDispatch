# EcoDispatch Architecture

## Overview

EcoDispatch is structured as a modular Python package for simulating carbon-aware energy dispatch in data centers. The current codebase is best understood as a scenario-analysis prototype: it compares dispatch strategies under modeled conditions rather than acting as a production control system.

## Core Modules

### simulation.py
- `EcoDispatch` class: Main simulation orchestrator
- Handles time-series data processing
- Coordinates between models, dispatch logic, charging behavior, and metrics

### models.py
- `Battery`: Models battery storage with capacity, efficiency, and power constraints
- `SolarPV`: Calculates photovoltaic generation based on irradiance and temperature
- `DemandProfile`: Generates data center load profiles

### dispatch.py
- `DispatchStrategy`: Implements different optimization strategies
- Strategies: baseline, carbon-minimizing, cost-minimizing, balanced, optimized
- Decision logic for energy-source prioritization plus strategy-specific charging behavior
- Includes a rolling-horizon optimized mode that uses a short future window when evaluating battery use

### metrics.py
- KPI calculations: emissions, costs, utilization rates
- Performance analysis functions

### visualization.py
- Plotting functions for results analysis
- Dashboard generation

### data_integration.py
- Loads real or synthetic weather, carbon intensity, and electricity price data
- Supports optional Electricity Maps configuration with synthetic fallback

## Data Flow

1. Input data (demand, carbon intensity, solar, price) loaded
2. Models initialized with system parameters
3. For each time step:
   - Dispatch strategy decides energy sources for the current demand
   - Charging logic optionally stores energy for future hours
   - Battery state updated
   - Metrics accumulated
4. Results visualized and reported, including load-served accounting

## Dependencies

- pandas: Time-series data handling
- numpy: Numerical computations
- matplotlib: Visualization
- scipy: Optimization utilities
- streamlit: Interactive dashboard
