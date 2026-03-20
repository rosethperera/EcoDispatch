"""
Visualization and plotting functions with publication-quality plots.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from typing import Dict


def plot_dispatch(results: Dict[str, pd.DataFrame], save_path: str = None):
    """
    Plot energy dispatch over time with distinct colors.

    Args:
        results: Simulation results dictionary
        save_path: Optional path to save plot
    """
    dispatch = results['dispatch'].copy()

    # Ensure columns are in correct order
    column_order = [col for col in ['grid', 'solar', 'battery'] if col in dispatch.columns]
    dispatch = dispatch[column_order]

    fig, ax = plt.subplots(figsize=(14, 6))

    # Distinct colors: dark gray (grid), bright yellow (solar), bright blue (battery)
    color_map = {
        'grid': '#404040',      # Dark gray
        'solar': '#FFD700',     # Bright yellow
        'battery': '#0099FF'    # Bright blue
    }
    colors = [color_map.get(col, '#95a5a6') for col in dispatch.columns]

    dispatch.plot.area(ax=ax, stacked=True,
                      color=colors,
                      alpha=0.8,
                      linewidth=2)

    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('Power (kW)', fontsize=12, fontweight='bold')
    ax.set_title('Energy Dispatch Over Time - Which Source Powers Your Data Center',
                fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Proper legend mapping
    labels = {'grid': 'Grid Power', 'solar': 'Solar Power', 'battery': 'Battery Power'}
    ax.legend([labels.get(col, col) for col in dispatch.columns],
             loc='upper left', fontsize=11, framealpha=0.95)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.savefig('dispatch_plot.png', dpi=150, bbox_inches='tight')
    plt.close()


def plot_battery_soc(battery_soc: pd.Series, save_path: str = None):
    """
    Plot battery state of charge over time.

    Args:
        battery_soc: Battery SOC time series or dataframe
        save_path: Optional path to save plot
    """
    fig, ax = plt.subplots(figsize=(14, 5))

    # Handle both Series and DataFrame formats
    if isinstance(battery_soc, pd.DataFrame):
        if 'soc' in battery_soc.columns:
            soc_values = battery_soc['soc'] * 100
        else:
            soc_values = battery_soc.iloc[:, 0] * 100
    else:
        soc_values = battery_soc * 100

    ax.plot(soc_values.index, soc_values.values, color='#0099FF', linewidth=3, label='Battery SOC')
    ax.fill_between(soc_values.index, soc_values.values, alpha=0.2, color='#0099FF')

    ax.set_xlabel('Time', fontsize=12, fontweight='bold')
    ax.set_ylabel('State of Charge (%)', fontsize=12, fontweight='bold')
    ax.set_title('Battery State of Charge Over Time', fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.set_ylim(0, 105)
    ax.legend(fontsize=11)

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.savefig('battery_soc_plot.png', dpi=150, bbox_inches='tight')
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
    emissions = [results['metrics']['total_emissions_gco2'] / 1000
                for results in strategies_results.values()]

    fig, ax = plt.subplots(figsize=(10, 6))

    colors = ['#808080', '#2ecc71', '#3498db', '#f39c12', '#9b59b6']
    bars = ax.bar(strategies, emissions, color=colors[:len(strategies)], alpha=0.8)

    ax.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total Emissions (kgCO2)', fontsize=12, fontweight='bold')
    ax.set_title('Carbon Emissions Comparison by Strategy', fontsize=14, fontweight='bold', pad=20)
    ax.grid(True, alpha=0.3, axis='y', linestyle='--')

    # Add value labels on bars
    for bar, emission in zip(bars, emissions):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{emission:.0f}',
               ha='center', va='bottom', fontsize=10, fontweight='bold')

    plt.xticks(rotation=45)
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.savefig('emissions_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
