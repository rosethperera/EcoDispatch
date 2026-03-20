#!/usr/bin/env python3
"""
EcoDispatch Demo Script
========================

This script demonstrates the key features of EcoDispatch:
1. Carbon-aware energy dispatch
2. Workload shifting for flexible loads
3. Multi-strategy comparison
4. Real-time metrics calculation

Perfect for presentations and portfolio showcases!
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import pandas as pd
import numpy as np
from ecodispatch.simulation import EcoDispatch
from ecodispatch.metrics import calculate_metrics
from ecodispatch.visualization import plot_dispatch, plot_battery_soc


OUTPUTS_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def ensure_outputs_dir():
    """Create the outputs directory if it does not exist."""
    os.makedirs(OUTPUTS_DIR, exist_ok=True)

def create_demo_data():
    """Create realistic demo data for San Francisco."""
    print("Creating San Francisco demo data...")

    # 24-hour simulation
    hours = pd.date_range('2023-01-15', periods=24, freq='h')  # Sunny January day

    # Realistic demand: higher during day, lower at night
    base_demand = 1000  # kW
    demand = pd.DataFrame({
        'demand_kw': [
            base_demand * (0.7 + 0.3 * np.sin(np.pi * i / 12))  # Peak at noon
            for i in range(24)
        ]
    }, index=hours)

    # Carbon intensity: higher during day (peak demand), lower at night
    carbon_intensity = pd.DataFrame({
        'carbon_gco2_per_kwh': [
            350 + 150 * np.sin(np.pi * i / 12) + np.random.normal(0, 30)
            for i in range(24)
        ]
    }, index=hours)

    # Solar generation: only during daylight hours
    solar_generation = pd.DataFrame({
        'solar_kw': [
            max(0, 500 * np.sin(np.pi * (i - 6) / 12)) if 6 <= i <= 18 else 0
            for i in range(24)
        ]
    }, index=hours)

    # Electricity price: peak during day
    price = pd.DataFrame({
        'price_usd_per_kwh': [
            0.10 + 0.05 * np.sin(np.pi * i / 12) + np.random.normal(0, 0.01)
            for i in range(24)
        ]
    }, index=hours)

    return {
        'demand': demand,
        'carbon_intensity': carbon_intensity,
        'solar_generation': solar_generation,
        'price': price
    }

def run_strategy_comparison():
    """Run all strategies and compare results."""
    print("\nRunning strategy comparison...")

    data = create_demo_data()
    strategies = ['baseline', 'carbon_min', 'cost_min', 'balanced', 'optimized']
    results = {}

    for strategy in strategies:
        print(f"  Running {strategy} strategy...")
        result = EcoDispatch.simulate(data, strategy=strategy)
        metrics = calculate_metrics(
            result,
            data['carbon_intensity']['carbon_gco2_per_kwh'],
            data['price']['price_usd_per_kwh']
        )
        results[strategy] = {
            'result': result,
            'metrics': metrics
        }

    return results

def print_comparison_table(results):
    """Print a nice comparison table of all strategies."""
    print("\n" + "="*80)
    print("ECODISPATCH STRATEGY COMPARISON")
    print("="*80)
    header = (
        f"{'Strategy':<12}"
        f"{'Emissions (kgCO2)':>20}"
        f"{'Cost ($)':>14}"
        f"{'Renewable (%)':>18}"
        f"{'Peak Grid (kW)':>18}"
    )
    print(header)
    print("-" * 80)

    for strategy, data in results.items():
        m = data['metrics']
        emissions_kg = m['total_emissions_gco2'] / 1000
        cost = m['total_cost_usd']
        renewable_pct = m['renewable_fraction'] * 100
        peak_grid = m['peak_grid_kw']
        print(
            f"{strategy:<12}"
            f"{emissions_kg:>20,.1f}"
            f"{cost:>14,.2f}"
            f"{renewable_pct:>18.1f}"
            f"{peak_grid:>18,.1f}"
        )

    print("="*80)

def demonstrate_workload_shifting():
    """Show how workload shifting reduces emissions."""
    print("\nDemonstrating Workload Shifting...")

    data = create_demo_data()

    # Run baseline (no shifting)
    baseline = EcoDispatch.simulate(data, strategy='baseline')
    baseline_metrics = calculate_metrics(
        baseline,
        data['carbon_intensity']['carbon_gco2_per_kwh'],
        data['price']['price_usd_per_kwh']
    )

    # Run carbon_min (with shifting)
    carbon_min = EcoDispatch.simulate(data, strategy='carbon_min')
    carbon_min_metrics = calculate_metrics(
        carbon_min,
        data['carbon_intensity']['carbon_gco2_per_kwh'],
        data['price']['price_usd_per_kwh']
    )

    emissions_saved = baseline_metrics['total_emissions_gco2'] - carbon_min_metrics['total_emissions_gco2']
    cost_saved = baseline_metrics['total_cost_usd'] - carbon_min_metrics['total_cost_usd']

    print("\nWorkload Shifting Impact:")
    print(f"  Emissions Saved: {emissions_saved/1000:.1f} kgCO2 ({emissions_saved/baseline_metrics['total_emissions_gco2']*100:.1f}%)")
    print(f"  Cost Saved: ${cost_saved:.2f} ({cost_saved/baseline_metrics['total_cost_usd']*100:.1f}%)")
    shifted_load_kwh = float(carbon_min['workload_shifts']['shifted_load_kw'].abs().sum())
    print(f"  Flexible Load Shifted: {shifted_load_kwh:.0f} kWh")

def create_visualizations(results):
    """Generate plots for the best strategy."""
    print("\nCreating visualizations...")
    ensure_outputs_dir()

    # Use carbon_min results (most impressive)
    best_result = results['carbon_min']['result']

    # Create plots
    dispatch_path = os.path.join(OUTPUTS_DIR, 'demo_dispatch.png')
    battery_path = os.path.join(OUTPUTS_DIR, 'demo_battery_soc.png')
    plot_dispatch(best_result, dispatch_path)
    plot_battery_soc(best_result['battery_soc'], battery_path)

    print("  Created outputs/demo_dispatch.png (energy sources over time)")
    print("  Created outputs/demo_battery_soc.png (battery charge level)")

def main():
    """Main demo function."""
    print("EcoDispatch: Carbon-Aware Data Center Energy Optimizer")
    print("="*60)

    # Run comparison
    results = run_strategy_comparison()

    # Show results
    print_comparison_table(results)

    # Demonstrate workload shifting
    demonstrate_workload_shifting()

    # Create visualizations
    create_visualizations(results)

    print("\n" + "="*60)
    print("Demo Complete!")
    print("Check the generated plot files in outputs/: demo_dispatch.png, demo_battery_soc.png")
    print("Run 'streamlit run dashboard.py' for interactive exploration")
    print("Hardware demo available in hardware/ directory")
    print("="*60)

if __name__ == "__main__":
    main()
