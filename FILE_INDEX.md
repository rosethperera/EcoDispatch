# File Index

This index uses evidence-based descriptions only.

## Start Here

1. `README.md` for the technical project overview.
2. `dashboard.py` for the Streamlit interface.
3. `src/ecodispatch/` for the core simulation package.
4. `tests/` for automated checks.

## Portfolio Docs

- `PORTFOLIO_README.md`: portfolio-safe project summary
- `PORTFOLIO_INTEGRATION_GUIDE.md`: safe wording for website integration
- `PORTFOLIO_CHECKLIST.md`: truthfulness checklist
- `PORTFOLIO_PACKAGE_SUMMARY.md`: short portfolio package summary
- `PITCH_CHEAT_SHEET.md`: safe talking points
- `PRESENTATION_GUIDE.md`: safe demo framing

## Core App Files

- `dashboard.py`: Streamlit dashboard
- `demo.py`: demo script that runs strategy comparisons
- `main.py`: sample entry point
- `src/ecodispatch/models.py`: battery, solar, and demand models
- `src/ecodispatch/dispatch.py`: strategy logic
- `src/ecodispatch/simulation.py`: simulation engine
- `src/ecodispatch/metrics.py`: KPI calculations
- `src/ecodispatch/data_integration.py`: real/synthetic data loading

## Tests

- `tests/test_models.py`: simulation and model tests
- `tests/test_data_integration.py`: data-integration tests

Current verified command:

```bash
python -m unittest discover -s tests -q
```

## Notes

- Do not cite fixed savings percentages unless you verify them from a specific run and label them as scenario-specific.
- Do not cite old coverage or test-count claims that are no longer true.
