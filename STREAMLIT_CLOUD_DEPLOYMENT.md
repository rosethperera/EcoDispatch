# Streamlit Cloud Deployment Notes

This file covers deployment mechanics only. Deployment does not change the fact that EcoDispatch is a prototype simulator.

## Before Deploying

- Verify the app runs locally:

```bash
streamlit run dashboard.py
```

- Verify tests pass:

```bash
python -m unittest discover -s tests -q
```

## Safe Deployment Wording

If you deploy the app, describe it like this:

"A public demo of the EcoDispatch prototype dashboard."

Not like this:

- "production-ready platform"
- "validated commercial deployment"
- fixed impact percentages unless you label them as scenario-specific

## Safe Announcement Template

"I published a public demo of EcoDispatch, a Python simulation prototype for carbon-aware data center energy optimization. The dashboard compares multiple dispatch strategies and scenario presets so users can inspect carbon-versus-cost tradeoffs."
