"""
Calculation of simulation metrics and KPIs.
"""

import pandas as pd
import numpy as np
from typing import Dict


def calculate_metrics(results: Dict[str, pd.DataFrame],
                     carbon_intensity: pd.Series,
                     electricity_price: pd.Series) -> Dict[str, float]:
    """
    Calculate key performance metrics.

    Args:
        results: Simulation results dictionary
        carbon_intensity: Carbon intensity time series (gCO2/kWh)
        electricity_price: Electricity price time series ($/kWh)

    Returns:
        Dictionary of calculated metrics
    """
    dispatch = results['dispatch']

    # Total energy consumption
    total_energy_kwh = float(dispatch.sum().sum())

    # Grid energy usage
    grid_energy_kwh = float(dispatch['grid'].sum())

    # Solar utilization
    solar_energy_kwh = float(dispatch['solar'].sum())
    total_solar_available = float(results.get('solar_available', pd.Series()).sum())
    solar_utilization = solar_energy_kwh / total_solar_available if total_solar_available > 0 else 0

    # Battery usage
    battery_energy_kwh = float(abs(dispatch['battery']).sum())

    # Peak grid draw
    peak_grid_kw = float(dispatch['grid'].max())

    # Total emissions (gCO2)
    total_emissions_gco2 = float((dispatch['grid'] * carbon_intensity).sum())

    # Total cost ($)
    total_cost = float((dispatch['grid'] * electricity_price).sum())

    # Renewable energy fraction
    battery_discharge_kwh = float(dispatch['battery'].clip(lower=0).sum())
    renewable_energy_kwh = solar_energy_kwh + battery_discharge_kwh
    renewable_fraction = renewable_energy_kwh / total_energy_kwh if total_energy_kwh > 0 else 0

    metrics = {
        'total_energy_kwh': total_energy_kwh,
        'grid_energy_kwh': grid_energy_kwh,
        'solar_energy_kwh': solar_energy_kwh,
        'battery_energy_kwh': battery_energy_kwh,
        'solar_utilization': solar_utilization,
        'peak_grid_kw': peak_grid_kw,
        'total_emissions_gco2': total_emissions_gco2,
        'total_cost_usd': total_cost,
        'renewable_fraction': renewable_fraction
    }

    return metrics
