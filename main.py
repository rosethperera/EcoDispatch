"""
Main entry point for EcoDispatch simulation.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from typing import Dict
from ecodispatch import EcoDispatch
from ecodispatch.visualization import plot_dispatch, plot_battery_soc


def load_sample_data() -> Dict[str, pd.DataFrame]:
    """
    Load sample simulation data.

    Returns:
        Dictionary of input dataframes
    """
    # Create sample 24-hour data
    hours = pd.date_range('2023-01-01', periods=24, freq='H')

    # Sample demand profile
    demand = pd.DataFrame({
        'demand_kw': [800 + 200 * np.sin(2 * np.pi * i / 24) + np.random.normal(0, 50)
                     for i in range(24)]
    }, index=hours)

    # Sample carbon intensity (gCO2/kWh)
    carbon_intensity = pd.DataFrame({
        'carbon_gco2_per_kwh': [300 + 100 * np.sin(2 * np.pi * i / 24) + np.random.normal(0, 20)
                               for i in range(24)]
    }, index=hours)

    # Sample solar generation
    solar_generation = pd.DataFrame({
        'solar_kw': [max(0, 400 * np.sin(np.pi * i / 12)) if 6 <= i <= 18 else 0
                    for i in range(24)]
    }, index=hours)

    # Sample electricity price ($/kWh)
    price = pd.DataFrame({
        'price_usd_per_kwh': [0.12 + 0.03 * np.sin(2 * np.pi * i / 24) + np.random.normal(0, 0.01)
                             for i in range(24)]
    }, index=hours)

    return {
        'demand': demand,
        'carbon_intensity': carbon_intensity,
        'solar_generation': solar_generation,
        'price': price
    }


def main():
    """
    Run EcoDispatch simulation with sample data.
    """
    print("EcoDispatch: Carbon-Aware Data Center Energy Optimizer")
    print("=" * 60)

    # Load data
    data = load_sample_data()
    print("Loaded sample data for 24-hour simulation")

    # Run simulation with different strategies
    strategies = ['baseline', 'carbon_min', 'cost_min', 'balanced']
    results = {}

    for strategy in strategies:
        print(f"\nRunning simulation with {strategy} strategy...")
        result = EcoDispatch.simulate(data, strategy=strategy)
        results[strategy] = result

        # Calculate metrics (placeholder - would need actual implementation)
        print(f"Strategy: {strategy}")
        print(".2f")
        print(".2f")

    # Generate plots
    print("\nGenerating visualizations...")
    plot_dispatch(results['carbon_min'])
    plot_battery_soc(results['carbon_min']['battery_soc'])

    print("\nSimulation complete!")


if __name__ == "__main__":
    main()