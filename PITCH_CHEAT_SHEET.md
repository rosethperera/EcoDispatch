# EcoDispatch Pitch Cheat Sheet

Use this only for statements that the current repository supports directly.

## 30-Second Version

"I built EcoDispatch, a Python simulation prototype for carbon-aware data center energy optimization. It models how a site could coordinate grid power, on-site solar, battery storage, and flexible workloads, then compares multiple dispatch strategies in a Streamlit dashboard."

## One-Sentence Summary

"EcoDispatch is a scenario-analysis tool for studying carbon-versus-cost tradeoffs in data center energy dispatch."

## What You Can Safely Claim

- It is a Python simulation prototype, not a production dispatch controller.
- It compares five strategies: `baseline`, `carbon_min`, `cost_min`, `balanced`, and `optimized`.
- It includes a Streamlit dashboard for scenario setup and strategy comparison.
- It models battery state of charge, solar generation, grid carbon intensity, electricity price, and flexible demand.
- It can use real weather data by default and optional Electricity Maps carbon and price data when configured.
- It includes prototype hardware paths for Arduino and Raspberry Pi monitoring concepts.
- It currently has 10 unit tests passing via `python -m unittest discover -s tests -q`.

## What You Should Not Claim

- Specific fixed savings like "27% less carbon" or "21% lower cost" as universal project results.
- "40% renewable energy" as a standing project outcome.
- "98% coverage" or "42 passing tests."
- "Production-ready" or "deployed live" unless you separately verify a real deployment.
- Large-scale national impact numbers.

## Technical Version

"The project combines time-series simulation, battery and solar component models, flexible workload shifting, and multiple dispatch strategies, including a rolling-horizon optimized mode, to study tradeoffs between emissions, electricity cost, and battery usage."

## Interview-Friendly Framing

### What problem does it solve?

It gives you a controlled way to explore whether a data center could lower emissions or cost by changing when it draws from the grid, when it uses storage, and when it shifts flexible work.

### Why is it interesting?

Because the grid changes hour by hour. Carbon intensity and electricity price are not constant, so timing decisions matter.

### What is the strongest honest outcome?

The strongest outcome is not one fixed percentage. It is that the repo now exposes strategy differences, scenario presets, and explicit load-served accounting so comparisons are inspectable instead of hand-wavy.

## Resume-Safe Version

"Built EcoDispatch, a Python simulation prototype for carbon-aware data center energy optimization, with battery and solar models, flexible workload scheduling, and a Streamlit dashboard for comparing dispatch strategies under different scenarios."
