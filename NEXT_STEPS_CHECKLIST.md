# Next Steps Checklist

This checklist assumes you want to present EcoDispatch honestly as a prototype.

## Immediate

- Keep the README and website wording aligned with the current code.
- Use screenshots from the current dashboard rather than old percentage claims.
- Run tests before sharing:

```bash
python -m unittest discover -s tests -q
```

## Portfolio

- Use `PORTFOLIO_README.md` as the source copy.
- Use `PORTFOLIO_INTEGRATION_GUIDE.md` for safe wording.
- Avoid unsupported metrics, deployment claims, and coverage claims.

## Demo

- Run `python demo.py` for a quick strategy comparison.
- Run `streamlit run dashboard.py` for the full dashboard.
- Prefer showing scenario presets and strategy explanations over hard-coded impact numbers.

## Deployment

- Only claim a live deployment if you have verified one.
- If you deploy the dashboard, say it is a public demo of a prototype simulator.

## Safe Share Text

"I built EcoDispatch, a Python simulation prototype for carbon-aware data center energy optimization. It compares multiple dispatch strategies for using grid power, solar, batteries, and flexible workloads under different scenarios."
