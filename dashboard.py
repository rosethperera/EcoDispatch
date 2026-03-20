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


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_number(value, unit=""):
    """Format numbers with commas for readability."""
    if isinstance(value, float):
        if value >= 1000:
            return f"{value:,.1f} {unit}"
        return f"{value:.1f} {unit}"
    return f"{value:,} {unit}"


def get_strategy_description(strategy):
    """Get a friendly description of each strategy."""
    descriptions = {
        'baseline': 'Always uses grid power first, minimal optimization',
        'carbon_min': 'Prioritizes clean energy, shifts flexible workloads to low-carbon hours',
        'cost_min': 'Minimizes electricity costs using solar first, then grid',
        'balanced': 'Balances carbon emissions and cost reduction',
        'optimized': 'Multi-objective optimization using advanced algorithms'
    }
    return descriptions.get(strategy, strategy)


def get_strategy_color(strategy):
    """Get a color for each strategy."""
    colors = {
        'baseline': '#808080',
        'carbon_min': '#2ecc71',
        'cost_min': '#3498db',
        'balanced': '#f39c12',
        'optimized': '#9b59b6'
    }
    return colors.get(strategy, '#95a5a6')


# ============================================================================
# MAIN APP
# ============================================================================

def main():
    """Main Streamlit application."""
    st.set_page_config(
        page_title="EcoDispatch - Carbon-Aware Data Center Energy Optimizer",
        page_icon="⚡", 
        layout="wide"
    )

    st.title("⚡ EcoDispatch: Carbon-Aware Data Center Energy Optimizer")
    st.markdown(
        "*Optimizing renewable energy utilization and workload scheduling to minimize carbon footprint*"
    )

    # Initialize session state for strategy comparison
    if 'comparison_results' not in st.session_state:
        st.session_state.comparison_results = None

    # Sidebar configuration
    st.sidebar.header("🎛️ Configuration")

    # Location settings
    st.sidebar.subheader("📍 Location")
    latitude = st.sidebar.number_input(
        "Latitude", 
        value=37.7749, 
        format="%.4f",
        help="San Francisco = 37.77°N"
    )
    longitude = st.sidebar.number_input(
        "Longitude", 
        value=-122.4194, 
        format="%.4f",
        help="San Francisco = -122.42°W"
    )

    # System parameters
    st.sidebar.subheader("⚙️ System Parameters")
    battery_capacity = st.sidebar.slider(
        "🔋 Battery Capacity (kWh)", 
        500, 2000, 1000,
        help="Total energy storage available"
    )
    solar_capacity = st.sidebar.slider(
        "☀️ Solar Capacity (kW)", 
        200, 1000, 500,
        help="Peak solar generation capacity"
    )
    flexible_load_fraction = st.sidebar.slider(
        "🔄 Flexible Load Fraction", 
        0.0, 0.5, 0.3,
        help="Percentage of workload that can be shifted"
    )

    # Simulation settings
    st.sidebar.subheader("⚙️ Simulation")
    days = st.sidebar.slider(
        "📅 Simulation Days", 
        1, 7, 1,
        help="Number of days to simulate"
    )
    strategy = st.sidebar.selectbox(
        "🎯 Dispatch Strategy",
        ["baseline", "carbon_min", "cost_min", "balanced", "optimized"],
        format_func=lambda x: f"{x.upper()} - {get_strategy_description(x)}"
    )

    col1, col2 = st.sidebar.columns(2)
    with col1:
        run_button = st.button("▶️ Run Simulation", use_container_width=True)
    with col2:
        compare_button = st.button("🔬 Compare All Strategies", use_container_width=True)

    if run_button:
        run_simulation(latitude, longitude, battery_capacity, solar_capacity,
                      flexible_load_fraction, days, strategy)

    if compare_button:
        compare_all_strategies(latitude, longitude, battery_capacity, solar_capacity,
                             flexible_load_fraction, days)


# ============================================================================
# SIMULATION FUNCTIONS
# ============================================================================

def run_simulation(latitude, longitude, battery_capacity, solar_capacity,
                  flexible_load_fraction, days, strategy):
    """Run single strategy simulation and display results."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("📊 Loading data...")
        progress_bar.progress(20)

        data = load_real_data(latitude, longitude, days)

        progress_bar.progress(40)
        status_text.text("🔄 Running simulation...")

        data['demand']['flexible_fraction'] = flexible_load_fraction
        data['config'] = {
            'latitude': latitude,
            'longitude': longitude,
            'battery_capacity_kwh': battery_capacity,
            'battery_max_power_kw': min(200.0, battery_capacity * 0.25),
            'solar_capacity_kw': solar_capacity,
            'flexible_load_fraction': flexible_load_fraction
        }
        results = EcoDispatch.simulate(data, strategy=strategy)

        progress_bar.progress(70)
        status_text.text("📈 Calculating metrics...")

        carbon_intensity = data['carbon_intensity']['carbon_gco2_per_kwh']
        electricity_price = data['price']['price_usd_per_kwh']
        metrics = calculate_metrics(results, carbon_intensity, electricity_price)

        progress_bar.progress(100)
        status_text.text("✅ Complete!")

        # Clear progress
        progress_bar.empty()
        status_text.empty()

        # Display results
        display_results(results, metrics, data, strategy)

    except Exception as e:
        st.error(f"❌ Simulation failed: {str(e)}")
        st.info("Try adjusting parameters or check console for details.")


def compare_all_strategies(latitude, longitude, battery_capacity, solar_capacity,
                          flexible_load_fraction, days):
    """Compare all 5 strategies side-by-side."""
    strategies = ["baseline", "carbon_min", "cost_min", "balanced", "optimized"]
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("📊 Loading data...")
        progress_bar.progress(10)

        data = load_real_data(latitude, longitude, days)
        data['demand']['flexible_fraction'] = flexible_load_fraction
        data['config'] = {
            'latitude': latitude,
            'longitude': longitude,
            'battery_capacity_kwh': battery_capacity,
            'battery_max_power_kw': min(200.0, battery_capacity * 0.25),
            'solar_capacity_kw': solar_capacity,
            'flexible_load_fraction': flexible_load_fraction
        }

        comparison_data = []

        for i, strategy in enumerate(strategies):
            status_text.text(f"🔄 Running {strategy.upper()} strategy...")
            progress_bar.progress(10 + (i * 18))

            results = EcoDispatch.simulate(data, strategy=strategy)

            carbon_intensity = data['carbon_intensity']['carbon_gco2_per_kwh']
            electricity_price = data['price']['price_usd_per_kwh']
            metrics = calculate_metrics(results, carbon_intensity, electricity_price)

            comparison_data.append({
                'Strategy': strategy.upper(),
                'Emissions (kgCO2)': float(metrics['total_emissions_gco2'] / 1000),
                'Cost ($)': float(metrics['total_cost_usd']),
                'Peak Grid (kW)': float(metrics['peak_grid_kw']),
                'Renewable (%)': float(metrics['renewable_fraction'] * 100)
            })

        progress_bar.progress(100)
        status_text.text("✅ Complete!")
        progress_bar.empty()
        status_text.empty()

        # Display comparison
        display_comparison(comparison_data)

    except Exception as e:
        st.error(f"❌ Comparison failed: {str(e)}")


# ============================================================================
# DISPLAY FUNCTIONS
# ============================================================================

def display_results(results, metrics, data, strategy):
    """Display simulation results."""
    strategy_color = get_strategy_color(strategy)

    # Strategy header with color
    st.markdown(f"<h2 style='color: {strategy_color}'>📊 Results - {strategy.upper()} Strategy</h2>", 
                unsafe_allow_html=True)
    st.markdown(f"*{get_strategy_description(strategy)}*")
    st.divider()

    # Key metrics with better formatting
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        emissions_kg = metrics['total_emissions_gco2'] / 1000
        st.metric(
            "🌍 Total Emissions",
            f"{emissions_kg:,.0f} kgCO2",
            help="Total carbon emissions over the simulation period"
        )

    with col2:
        cost = metrics['total_cost_usd']
        st.metric(
            "💰 Total Cost",
            f"${cost:,.2f}",
            help="Total electricity cost for the period"
        )

    with col3:
        peak_grid = metrics['peak_grid_kw']
        st.metric(
            "⚡ Peak Grid Draw",
            f"{peak_grid:,.0f} kW",
            help="Maximum power drawn from the grid"
        )

    with col4:
        renewable = metrics['renewable_fraction'] * 100
        st.metric(
            "♻️ Renewable Energy",
            f"{renewable:.1f}%",
            help="Percentage of energy from renewable sources"
        )

    st.divider()

    # Energy Dispatch Chart
    st.subheader("📈 Energy Dispatch Over Time")
    display_dispatch_chart(results)

    # Two-column layout for battery and carbon
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🔋 Battery State of Charge")
        display_battery_chart(results)

    with col2:
        st.subheader("🌐 Grid Carbon Intensity")
        display_carbon_intensity_chart(data)

    # Emissions rate
    st.subheader("📊 Emissions Rate Over Time")
    display_emissions_chart(results)

    # Workload shifts
    if 'workload_shifts' in results and results['workload_shifts']['shifted_load_kw'].abs().max() > 0:
        st.subheader("🔄 Flexible Workload Shifts")
        display_workload_chart(results)

    # Weather data
    if 'weather' in data:
        st.subheader("🌤️ Weather Conditions")
        display_weather_section(data)

    # Raw data expander
    st.divider()
    with st.expander("📋 View Raw Data"):
        tab1, tab2, tab3, tab4 = st.tabs(["Dispatch", "Battery", "Emissions", "Costs"])

        with tab1:
            st.dataframe(results['dispatch'], use_container_width=True)

        with tab2:
            st.dataframe(results['battery_soc'], use_container_width=True)

        with tab3:
            st.dataframe(results['emissions'], use_container_width=True)

        with tab4:
            st.dataframe(results['costs'], use_container_width=True)


def display_dispatch_chart(results):
    """Display energy dispatch stack chart with proper colors."""
    try:
        dispatch = results['dispatch'].copy()

        # Ensure columns are in correct order
        column_order = [col for col in ['grid', 'solar', 'battery'] if col in dispatch.columns]
        dispatch = dispatch[column_order]

        fig, ax = plt.subplots(figsize=(14, 6))

        # Distinct colors: dark gray for grid, bright yellow for solar, bright blue for battery
        color_map = {
            'grid': '#404040',      # Dark gray
            'solar': '#FFD700',     # Bright yellow
            'battery': '#0099FF'    # Bright blue
        }
        colors = [color_map.get(col, '#95a5a6') for col in dispatch.columns]

        dispatch.plot.area(
            ax=ax,
            stacked=True,
            color=colors,
            alpha=0.8,
            linewidth=2
        )

        ax.set_xlabel('Time', fontsize=12, fontweight='bold')
        ax.set_ylabel('Power (kW)', fontsize=12, fontweight='bold')
        ax.set_title('Energy Dispatch Over Time - Which Source Powers Your Data Center', 
                    fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(
            ['Grid Power', 'Solar Power', 'Battery Power'],
            loc='upper left',
            fontsize=10,
            framealpha=0.95
        )

        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Could not display dispatch chart: {e}")


def display_battery_chart(results):
    """Display battery state of charge."""
    try:
        fig, ax = plt.subplots(figsize=(12, 4))
        battery_soc = results['battery_soc']

        if 'soc' in battery_soc.columns:
            soc_values = battery_soc['soc'] * 100
        else:
            soc_values = battery_soc.iloc[:, 0] * 100

        ax.plot(battery_soc.index, soc_values, 'b-', linewidth=3, label='Battery SOC')
        ax.fill_between(battery_soc.index, soc_values, alpha=0.3)
        ax.set_xlabel('Time', fontsize=11, fontweight='bold')
        ax.set_ylabel('State of Charge (%)', fontsize=11, fontweight='bold')
        ax.set_title('Battery State of Charge Over Time', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_ylim(0, 105)
        ax.legend(fontsize=10)

        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Could not display battery chart: {e}")


def display_carbon_intensity_chart(data):
    """Display grid carbon intensity."""
    try:
        fig, ax = plt.subplots(figsize=(12, 4))
        carbon_data = data['carbon_intensity']

        ax.plot(carbon_data.index, carbon_data['carbon_gco2_per_kwh'], 
               color='#e74c3c', linewidth=2.5)
        ax.fill_between(carbon_data.index, carbon_data['carbon_gco2_per_kwh'], alpha=0.2, color='#e74c3c')
        ax.set_xlabel('Time', fontsize=11, fontweight='bold')
        ax.set_ylabel('Carbon Intensity (gCO2/kWh)', fontsize=11, fontweight='bold')
        ax.set_title('Grid Carbon Intensity Over Time', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Could not display carbon chart: {e}")


def display_emissions_chart(results):
    """Display emissions rate."""
    try:
        fig, ax = plt.subplots(figsize=(14, 4))
        emissions = results['emissions']

        ax.plot(emissions.index, emissions['emissions_gco2'], 
               color='#c0392b', linewidth=2.5, label='Emissions Rate')
        ax.fill_between(emissions.index, emissions['emissions_gco2'], alpha=0.2, color='#c0392b')
        ax.set_xlabel('Time', fontsize=11, fontweight='bold')
        ax.set_ylabel('Emissions (gCO2/h)', fontsize=11, fontweight='bold')
        ax.set_title('Carbon Emissions Rate Over Time', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.legend(fontsize=10)

        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Could not display emissions chart: {e}")


def display_workload_chart(results):
    """Display workload shifts."""
    try:
        fig, ax = plt.subplots(figsize=(14, 4))
        shifts = results['workload_shifts']

        colors = ['#2ecc71' if x > 0 else '#e74c3c' for x in shifts['shifted_load_kw']]
        ax.bar(shifts.index, shifts['shifted_load_kw'], color=colors, alpha=0.7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
        ax.set_xlabel('Time', fontsize=11, fontweight='bold')
        ax.set_ylabel('Shifted Load (kW)', fontsize=11, fontweight='bold')
        ax.set_title('Flexible Workload Shifts (Green=Reduce, Red=Increase)', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')

        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Could not display workload chart: {e}")


def display_weather_section(data):
    """Display weather metrics."""
    try:
        weather = data['weather']

        col1, col2, col3 = st.columns(3)

        with col1:
            temp = weather['temperature_c'].mean()
            st.metric(
                "🌡️ Avg Temperature",
                f"{temp:.1f}°C",
                help=f"Range: {weather['temperature_c'].min():.1f}°C to {weather['temperature_c'].max():.1f}°C"
            )

        with col2:
            cloud = weather['cloud_cover'].mean() * 100
            st.metric(
                "☁️ Avg Cloud Cover",
                f"{cloud:.1f}%",
                help=f"Higher = Less solar generation"
            )

        with col3:
            wind = weather['wind_speed_ms'].mean()
            st.metric(
                "💨 Avg Wind Speed",
                f"{wind:.1f} m/s",
                help="May affect solar and cooling"
            )
    except Exception as e:
        st.warning(f"Could not display weather: {e}")


def display_comparison(comparison_data):
    """Display strategy comparison."""
    st.divider()
    st.header("🔬 Strategy Comparison")

    df = pd.DataFrame(comparison_data)
    numeric_columns = ['Emissions (kgCO2)', 'Cost ($)', 'Peak Grid (kW)', 'Renewable (%)']
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors='coerce')
    df_sorted = df.sort_values('Emissions (kgCO2)')

    # Summary table
    st.subheader("📊 Performance Comparison Table")
    st.dataframe(
        df_sorted.style.format({
            'Emissions (kgCO2)': '{:,.0f}',
            'Cost ($)': '${:,.2f}',
            'Peak Grid (kW)': '{:,.0f}',
            'Renewable (%)': '{:.1f}%'
        }).background_gradient(subset=['Emissions (kgCO2)'], cmap='RdYlGn_r').background_gradient(
            subset=['Cost ($)'], cmap='RdYlGn_r'
        ).background_gradient(subset=['Renewable (%)'], cmap='RdYlGn'),
        use_container_width=True
    )

    # Comparison charts
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🌍 Total Emissions Comparison")
        fig, ax = plt.subplots(figsize=(8, 5))
        colors_list = [get_strategy_color(s.lower()) for s in df_sorted['Strategy']]
        bars = ax.bar(df_sorted['Strategy'], df_sorted['Emissions (kgCO2)'], color=colors_list, alpha=0.8)
        ax.set_ylabel('Emissions (kgCO2)', fontsize=11, fontweight='bold')
        ax.set_title('Total Carbon Emissions by Strategy', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

        st.pyplot(fig)

    with col2:
        st.subheader("💰 Total Cost Comparison")
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(df_sorted['Strategy'], df_sorted['Cost ($)'], color=colors_list, alpha=0.8)
        ax.set_ylabel('Cost ($)', fontsize=11, fontweight='bold')
        ax.set_title('Total Electricity Cost by Strategy', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')

        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'${height:,.2f}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

        st.pyplot(fig)

    # Renewable energy comparison
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("♻️ Renewable Energy Percentage")
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(df_sorted['Strategy'], df_sorted['Renewable (%)'], color=colors_list, alpha=0.8)
        ax.set_ylabel('Renewable Energy (%)', fontsize=11, fontweight='bold')
        ax.set_title('Renewable Energy Utilization by Strategy', fontsize=12, fontweight='bold')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:.1f}%',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

        st.pyplot(fig)

    with col2:
        st.subheader("⚡ Peak Grid Draw Comparison")
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.bar(df_sorted['Strategy'], df_sorted['Peak Grid (kW)'], color=colors_list, alpha=0.8)
        ax.set_ylabel('Peak Power (kW)', fontsize=11, fontweight='bold')
        ax.set_title('Maximum Grid Power Draw by Strategy', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3, axis='y', linestyle='--')

        for bar in bars:
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{height:,.0f}',
                   ha='center', va='bottom', fontsize=9, fontweight='bold')

        st.pyplot(fig)

    # Insights
    st.divider()
    st.subheader("💡 Key Insights")

    best_emissions = df_sorted.iloc[0]
    best_cost = df.loc[df['Cost ($)'].idxmin()]
    best_renewable = df.loc[df['Renewable (%)'].idxmax()]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.success(f"🏆 **Best for Emissions**: {best_emissions['Strategy']}\n"
                  f"{best_emissions['Emissions (kgCO2)']:,.0f} kgCO2")

    with col2:
        st.info(f"💵 **Best for Cost**: {best_cost['Strategy']}\n"
               f"${best_cost['Cost ($)']:,.2f}")

    with col3:
        st.success(f"♻️ **Best for Renewables**: {best_renewable['Strategy']}\n"
                  f"{best_renewable['Renewable (%)']:.1f}% renewable")


if __name__ == "__main__":
    main()
