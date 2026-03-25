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
    demand_profile = results.get('demand_served')
    grid_import_series = (
        results['grid_import']['grid_kw']
        if 'grid_import' in results
        else dispatch['grid']
    )

    # Total energy consumption
    total_energy_kwh = float(dispatch.sum().sum())

    # Grid energy usage
    grid_energy_kwh = float(grid_import_series.sum())

    # Solar utilization
    solar_energy_kwh = float(dispatch['solar'].sum())
    total_solar_available = float(results.get('solar_available', pd.Series()).sum())
    solar_utilization = solar_energy_kwh / total_solar_available if total_solar_available > 0 else 0

    # Battery usage
    battery_energy_kwh = float(abs(dispatch['battery']).sum())

    # Peak grid draw
    peak_grid_kw = float(grid_import_series.max())

    # Total emissions (gCO2)
    total_emissions_gco2 = float((grid_import_series * carbon_intensity).sum())

    # Total cost ($)
    total_cost = float((grid_import_series * electricity_price).sum())

    # Renewable energy fraction
    # Only count direct solar consumption as renewable here. The simulator does
    # not yet track whether discharged battery energy originally came from solar
    # or from a pre-charged / grid-charged state, so counting all battery
    # discharge as renewable would overstate clean-energy usage.
    renewable_energy_kwh = solar_energy_kwh
    renewable_fraction = renewable_energy_kwh / total_energy_kwh if total_energy_kwh > 0 else 0

    total_demand_kwh = float(demand_profile['demand_kw'].sum()) if demand_profile is not None else total_energy_kwh
    total_served_kwh = total_energy_kwh
    unmet_demand_kwh = max(total_demand_kwh - total_served_kwh, 0.0)
    load_served_fraction = total_served_kwh / total_demand_kwh if total_demand_kwh > 0 else 1.0

    metrics = {
        'total_energy_kwh': total_energy_kwh,
        'total_demand_kwh': total_demand_kwh,
        'total_served_kwh': total_served_kwh,
        'unmet_demand_kwh': unmet_demand_kwh,
        'load_served_fraction': load_served_fraction,
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
