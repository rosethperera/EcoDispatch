"""
Visualization and plotting functions.
"""

import matplotlib.pyplot as plt
import pandas as pd
from typing import Dict


def plot_dispatch(results: Dict[str, pd.DataFrame], save_path: str = None):
    """
    Plot energy dispatch over time.

    Args:
        results: Simulation results
        save_path: Optional path to save plot
    """
    dispatch = results['dispatch']

    fig, ax = plt.subplots(figsize=(12, 6))

    dispatch.plot.area(ax=ax, stacked=True,
                      color=['red', 'orange', 'green'],
                      alpha=0.7)

    ax.set_xlabel('Time')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Energy Dispatch Over Time')
    ax.legend(['Grid', 'Solar', 'Battery'])

    if save_path:
        plt.savefig(save_path)
    else:
        plt.savefig('dispatch_plot.png')
    plt.close()  # Close instead of show for headless operation


def plot_battery_soc(battery_soc: pd.Series, save_path: str = None):
    """
    Plot battery state of charge over time.

    Args:
        battery_soc: Battery SOC time series
        save_path: Optional path to save plot
    """
    fig, ax = plt.subplots(figsize=(12, 4))

    ax.plot(battery_soc.index, battery_soc.values * 100, 'b-')
    ax.set_xlabel('Time')
    ax.set_ylabel('State of Charge (%)')
    ax.set_title('Battery State of Charge')
    ax.grid(True)

    if save_path:
        plt.savefig(save_path)
    else:
        plt.savefig('battery_soc_plot.png')
    plt.close()


def plot_emissions_comparison(strategies_results: Dict[str, Dict],
                             save_path: str = None):
    """
    Plot emissions comparison across strategies.

    Args:
        strategies_results: Dict of strategy names to results
        save_path: Optional path to save plot
    """
    strategies = list(strategies_results.keys())
    emissions = [results['metrics']['total_emissions_gco2']
                for results in strategies_results.values()]

    fig, ax = plt.subplots(figsize=(8, 6))

    bars = ax.bar(strategies, emissions, color='skyblue')
    ax.set_xlabel('Strategy')
    ax.set_ylabel('Total Emissions (gCO2)')
    ax.set_title('Carbon Emissions by Dispatch Strategy')

    # Add value labels on bars
    for bar, emission in zip(bars, emissions):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
               '.1f', ha='center', va='bottom')

    if save_path:
        plt.savefig(save_path)
    else:
        plt.savefig('emissions_comparison.png')
    plt.close()