"""
Streamlit web dashboard for EcoDispatch visualization and interaction.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ecodispatch import EcoDispatch
from ecodispatch.data_integration import load_real_data
from ecodispatch.metrics import calculate_metrics


def main():
    """
    Main Streamlit application.
    """
    st.set_page_config(page_title="EcoDispatch - Carbon-Aware Data Center Energy Optimizer",
                      page_icon="⚡", layout="wide")

    st.title("⚡ EcoDispatch: Carbon-Aware Data Center Energy Optimizer")
    st.markdown("*Optimizing renewable energy utilization and workload scheduling to minimize carbon footprint*")

    # Sidebar configuration
    st.sidebar.header("Configuration")

    # Location settings
    st.sidebar.subheader("Location")
    latitude = st.sidebar.number_input("Latitude", value=37.7749, format="%.4f")
    longitude = st.sidebar.number_input("Longitude", value=-122.4194, format="%.4f")

    # System parameters
    st.sidebar.subheader("System Parameters")
    battery_capacity = st.sidebar.slider("Battery Capacity (kWh)", 500, 2000, 1000)
    solar_capacity = st.sidebar.slider("Solar Capacity (kW)", 200, 1000, 500)
    flexible_load_fraction = st.sidebar.slider("Flexible Load Fraction", 0.0, 0.5, 0.3)

    # Simulation settings
    st.sidebar.subheader("Simulation")
    days = st.sidebar.slider("Simulation Days", 1, 7, 1)
    strategy = st.sidebar.selectbox("Dispatch Strategy",
                                   ["baseline", "carbon_min", "cost_min", "balanced", "optimized"])

    if st.sidebar.button("Run Simulation"):
        run_simulation(latitude, longitude, battery_capacity, solar_capacity,
                      flexible_load_fraction, days, strategy)


def run_simulation(latitude, longitude, battery_capacity, solar_capacity,
                  flexible_load_fraction, days, strategy):
    """
    Run the simulation and display results.
    """
    with st.spinner("Loading data and running simulation..."):
        # Load data
        data = load_real_data(latitude, longitude, days)

        # Update demand with flexible load fraction
        data['demand']['flexible_fraction'] = flexible_load_fraction

        # Run simulation
        results = EcoDispatch.simulate(data, strategy=strategy)

        # Calculate metrics
        carbon_intensity = data['carbon_intensity']['carbon_gco2_per_kwh']
        electricity_price = data['price']['price_usd_per_kwh']
        metrics = calculate_metrics(results, carbon_intensity, electricity_price)

    # Display results
    display_results(results, metrics, data, strategy)


def display_results(results, metrics, data, strategy):
    """
    Display simulation results in the dashboard.
    """
    st.header(f"Simulation Results - {strategy.upper()} Strategy")

    # Key metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Emissions", f"{metrics['total_emissions_gco2']/1000:.1f} kgCO2",
                 help="Total carbon emissions over simulation period")

    with col2:
        st.metric("Total Cost", f"${metrics['total_cost_usd']:.2f}",
                 help="Total electricity cost")

    with col3:
        st.metric("Peak Grid Draw", f"{metrics['peak_grid_kw']:.0f} kW",
                 help="Maximum power drawn from grid")

    with col4:
        st.metric("Renewable Fraction", f"{metrics['renewable_fraction']*100:.1f}%",
                 help="Fraction of energy from renewable sources")

    # Charts
    st.header("Energy Dispatch")

    # Dispatch over time
    fig, ax = plt.subplots(figsize=(12, 6))
    dispatch = results['dispatch']
    dispatch.plot.area(ax=ax, stacked=True,
                      color=['#FF6B6B', '#FFD93D', '#6BCF7F'],
                      alpha=0.8)
    ax.set_xlabel('Time')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Energy Dispatch Over Time')
    ax.legend(['Grid', 'Solar', 'Battery'])
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    # Battery SOC
    st.header("Battery State")
    fig, ax = plt.subplots(figsize=(12, 4))
    battery_soc = results['battery_soc']
    ax.plot(battery_soc.index, battery_soc['soc'] * 100, 'b-', linewidth=2)
    ax.set_xlabel('Time')
    ax.set_ylabel('State of Charge (%)')
    ax.set_title('Battery State of Charge')
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 100)
    st.pyplot(fig)

    # Carbon intensity and emissions
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Carbon Intensity")
        fig, ax = plt.subplots(figsize=(8, 4))
        carbon_data = data['carbon_intensity']
        ax.plot(carbon_data.index, carbon_data['carbon_gco2_per_kwh'], 'r-', linewidth=2)
        ax.set_xlabel('Time')
        ax.set_ylabel('Carbon Intensity (gCO2/kWh)')
        ax.set_title('Grid Carbon Intensity')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

    with col2:
        st.subheader("Emissions Over Time")
        fig, ax = plt.subplots(figsize=(8, 4))
        emissions = results['emissions']
        ax.plot(emissions.index, emissions['emissions_gco2'], 'darkred', linewidth=2)
        ax.set_xlabel('Time')
        ax.set_ylabel('Emissions (gCO2)')
        ax.set_title('Carbon Emissions Rate')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

    # Workload shifts (if available)
    if 'workload_shifts' in results:
        st.header("Workload Management")
        fig, ax = plt.subplots(figsize=(12, 4))
        shifts = results['workload_shifts']
        ax.bar(shifts.index, shifts['shifted_load_kw'], color='purple', alpha=0.7)
        ax.set_xlabel('Time')
        ax.set_ylabel('Shifted Load (kW)')
        ax.set_title('Flexible Workload Shifts')
        ax.grid(True, alpha=0.3)
        st.pyplot(fig)

    # Weather data
    if 'weather' in data:
        st.header("Weather Conditions")
        weather = data['weather']

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Avg Temperature", f"{weather['temperature_c'].mean():.1f}°C")

        with col2:
            st.metric("Avg Cloud Cover", f"{weather['cloud_cover'].mean()*100:.1f}%")

        with col3:
            st.metric("Avg Wind Speed", f"{weather['wind_speed_ms'].mean():.1f} m/s")

    # Raw data
    with st.expander("View Raw Data"):
        tab1, tab2, tab3, tab4 = st.tabs(["Dispatch", "Battery", "Emissions", "Costs"])

        with tab1:
            st.dataframe(results['dispatch'])

        with tab2:
            st.dataframe(results['battery_soc'])

        with tab3:
            st.dataframe(results['emissions'])

        with tab4:
            st.dataframe(results['costs'])


if __name__ == "__main__":
    main()