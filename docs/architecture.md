# EcoDispatch Architecture

## Overview

EcoDispatch is structured as a modular Python package for simulating carbon-aware energy dispatch in data centers.

## Core Modules

### simulation.py
- `EcoDispatch` class: Main simulation orchestrator
- Handles time-series data processing
- Coordinates between models, dispatch logic, and metrics

### models.py
- `Battery`: Models battery storage with capacity, efficiency, and power constraints
- `SolarPV`: Calculates photovoltaic generation based on irradiance and temperature
- `DemandProfile`: Generates data center load profiles

### dispatch.py
- `DispatchStrategy`: Implements different optimization strategies
- Strategies: baseline, carbon-minimizing, cost-minimizing, balanced
- Decision logic for energy source prioritization

### metrics.py
- KPI calculations: emissions, costs, utilization rates
- Performance analysis functions

### visualization.py
- Plotting functions for results analysis
- Dashboard generation

## Data Flow

1. Input data (demand, carbon intensity, solar, price) loaded
2. Models initialized with system parameters
3. For each time step:
   - Dispatch strategy decides energy sources
   - Battery state updated
   - Metrics accumulated
4. Results visualized and reported

## Dependencies

- pandas: Time-series data handling
- numpy: Numerical computations
- matplotlib: Visualization
- scipy: Optimization utilities