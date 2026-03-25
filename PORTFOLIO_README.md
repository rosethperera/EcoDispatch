# EcoDispatch: Carbon-Aware Data Center Energy Optimization Prototype

> A Python simulation prototype for studying carbon-versus-cost tradeoffs in data center energy dispatch.

## Executive Summary

EcoDispatch models how a site could coordinate grid electricity, on-site solar, battery storage, and flexible workloads across hourly timesteps. It is designed as a scenario-analysis platform for engineering exploration, not as a production dispatch controller.

## What The Project Includes

- Time-series simulation of demand, carbon intensity, weather, electricity price, and dispatch.
- Five strategies: `baseline`, `carbon_min`, `cost_min`, `balanced`, and `optimized`.
- Battery and solar component models.
- Flexible workload shifting experiments.
- A Streamlit dashboard for running and comparing strategies.
- Optional real weather and optional Electricity Maps carbon/price inputs.
- Prototype hardware integration concepts via Arduino and Raspberry Pi files.

## What Makes It Worth Showing

- It frames sustainability as a systems problem rather than a slogan.
- It combines modeling, optimization logic, visualization, and testing in one repo.
- It makes tradeoffs inspectable by showing metrics like emissions, cost, peak grid draw, renewable share, load served, and unmet demand.
- It now includes scenario presets to make strategy differences easier to analyze.

## Honest Scope

EcoDispatch should be presented as:

- a prototype
- a simulation platform
- a scenario-analysis tool
- a portfolio project in sustainable infrastructure and energy systems

EcoDispatch should not be presented as:

- a production-ready controller
- a validated commercial deployment
- a source of fixed universal savings percentages

## Safe Resume Summary

Built EcoDispatch, a Python simulation prototype for carbon-aware data center energy optimization, modeling dispatch across grid, solar, battery storage, and flexible workloads with a Streamlit dashboard for scenario analysis.
