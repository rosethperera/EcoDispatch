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
from ecodispatch.data_integration import WeatherAPI, load_real_data, lookup_location_name
from ecodispatch.metrics import calculate_metrics
from ecodispatch.models import SolarPV


# ============================================================================
# FORMATTING UTILITIES
# ============================================================================

def format_number(value, unit=""):
    """Format numbers with commas for readability."""
    if isinstance(value, float):
        if value >= 1000:
            return f"{value:,.1f} {unit}"
        return f"{value:.1f} {unit}"


def build_solar_generation(weather, solar_capacity, latitude, longitude, multiplier=1.0):
    """Build an hourly solar profile from weather and scenario multiplier."""
    solar_model = SolarPV(capacity_kw=solar_capacity, latitude=latitude, longitude=longitude)
    solar_values = []
    for ts, row in weather.iterrows():
        solar_values.append(
            float(
                solar_model.generate(
                    ts,
                    float(row.get("cloud_cover", 0.0)),
                    float(row.get("temperature_c", 25.0)),
                    float(row.get("wind_speed_ms", 1.0)),
                )
            ) * multiplier
        )
    return pd.DataFrame({"solar_kw": solar_values}, index=weather.index)


def apply_scenario_profile(data, scenario, solar_capacity, latitude, longitude):
    """Modify the input data so different strategies separate more clearly."""
    if scenario == "realistic":
        return data

    data = {
        key: value.copy() if hasattr(value, "copy") else value
        for key, value in data.items()
    }

    carbon = data["carbon_intensity"]["carbon_gco2_per_kwh"].astype(float)
    price = data["price"]["price_usd_per_kwh"].astype(float)
    demand = data["demand"]["demand_kw"].astype(float)
    weather = data["weather"]

    if scenario == "stress_test":
        centered_carbon = carbon - carbon.mean()
        centered_price = price - price.mean()
        data["carbon_intensity"]["carbon_gco2_per_kwh"] = np.clip(carbon.mean() + centered_carbon * 1.8, 120, 900)
        data["price"]["price_usd_per_kwh"] = np.clip(price.mean() + centered_price * 2.2, 0.03, 0.60)
        data["demand"]["demand_kw"] = np.maximum(demand * 1.08, 450)
        data["solar_generation"] = build_solar_generation(weather, solar_capacity, latitude, longitude, multiplier=1.4)
    elif scenario == "solar_rich":
        data["solar_generation"] = build_solar_generation(weather, solar_capacity, latitude, longitude, multiplier=2.0)
        data["demand"]["demand_kw"] = np.maximum(demand * 0.95, 450)
    elif scenario == "volatile_market":
        centered_carbon = carbon - carbon.mean()
        centered_price = price - price.mean()
        data["carbon_intensity"]["carbon_gco2_per_kwh"] = np.clip(carbon.mean() + centered_carbon * 1.5, 150, 850)
        data["price"]["price_usd_per_kwh"] = np.clip(price.mean() + centered_price * 2.8, 0.03, 0.75)

    return data
    return f"{value:,} {unit}"


def get_strategy_description(strategy):
    """Get a friendly description of each strategy."""
    descriptions = {
        'baseline': 'Always uses grid power first, minimal optimization',
        'carbon_min': 'Uses solar then battery before grid and shifts some flexible load out of dirty hours',
        'cost_min': 'Minimizes electricity costs using solar first, then grid',
        'balanced': 'Uses solar first, then prefers battery only during high-carbon hours',
        'optimized': 'Single-step constrained optimizer that trades off grid carbon, grid price, and battery wear'
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


def get_strategy_details():
    """Return honest strategy notes for the dashboard."""
    return {
        "baseline": {
            "what_it_does": "Grid-first dispatch. The model serves demand from the grid before considering solar or battery, so this works as a control case rather than an optimization strategy.",
            "what_happens": "When you run it, nearly all demand is met by the grid. Emissions and cost follow the hourly grid carbon and price signals, and renewable use stays close to zero unless the grid cannot fully cover load.",
            "prototype_logic": [
                "Take the hour's demand as-is.",
                "Use as much grid power as needed.",
                "Only use solar or battery if demand remains after grid dispatch."
            ],
            "proper_implementation": [
                "Keep it as the non-optimized benchmark for comparison.",
                "Use measured load, tariffs, and generator limits to define the real baseline.",
                "Track reliability events, demand charges, and contractual power constraints."
            ]
        },
        "carbon_min": {
            "what_it_does": "Carbon-first dispatch. It uses available solar, then battery discharge, then grid power. It also shifts part of flexible demand up to 4 hours later when the current hour is much dirtier than average.",
            "what_happens": "When you run it, the system trims grid usage during dirty hours and may move some flexible work into cleaner hours. It usually lowers emissions, but the renewable percentage depends heavily on how much solar and battery energy is actually available.",
            "prototype_logic": [
                "Check whether the current hour's grid carbon is well above the average profile.",
                "If yes, move up to part of the flexible load to a cleaner hour within the next 4 hours.",
                "Serve the adjusted demand using solar first, then battery, then grid."
            ],
            "proper_implementation": [
                "Forecast carbon intensity and demand over the full optimization horizon.",
                "Classify workloads by deadline, migration cost, and SLA risk before shifting them.",
                "Solve a horizon-wide scheduling problem instead of making isolated hour-by-hour moves."
            ]
        },
        "cost_min": {
            "what_it_does": "Cost-first dispatch. It uses solar first, discharges the battery during expensive hours, and grid-charges the battery during cheap hours if a more expensive period is coming.",
            "what_happens": "When you run it, the system tries to arbitrage electricity prices: charge low, discharge high. It can cut cost even when carbon benefits are small.",
            "prototype_logic": [
                "Take the hour's demand with no workload shifting.",
                "Use available solar first because it is treated as zero marginal cost.",
                "Use grid next, then battery only if there is still unmet demand."
            ],
            "proper_implementation": [
                "Include time-of-use rates, demand charges, export rules, and battery degradation economics.",
                "Optimize battery charging and discharging across the whole day, not just within one hour.",
                "Model marginal cost of deferred workloads and generator startup costs if applicable."
            ]
        },
        "balanced": {
            "what_it_does": "Visible weighted tradeoff between carbon and cost. It computes a combined score from the current carbon and price signals, then uses or charges the battery based on the chosen balance.",
            "what_happens": "When you run it, changing the carbon-weight slider will move BALANCED closer to carbon-first or cost-first behavior. It is meant to be the most interpretable tradeoff strategy.",
            "prototype_logic": [
                "Serve as much load as possible with solar.",
                "If grid carbon is above the threshold and battery state of charge is healthy, discharge the battery.",
                "Use grid for the remaining demand."
            ],
            "proper_implementation": [
                "Replace the single hard-coded threshold with tuned weights or learned policy parameters.",
                "Calibrate using historical price and carbon data from the actual site.",
                "Add explicit reserve margins so battery energy is preserved for backup and peak events."
            ]
        },
        "optimized": {
            "what_it_does": "Rolling-horizon optimization. It chooses the current hour's grid, solar, and battery mix with constrained optimization while also looking ahead to future carbon and price spikes when deciding whether to save or charge the battery.",
            "what_happens": "When you run it, the solver uses the present hour plus a short future window, so it can preserve battery energy for better future opportunities instead of reacting myopically to just one hour.",
            "prototype_logic": [
                "Build one objective function for the current hour: grid carbon plus grid cost plus battery wear.",
                "Use constrained optimization to split the hour's demand across grid, solar, and battery within available limits.",
                "If the solver fails, fall back to a deterministic heuristic that still covers the full load."
            ],
            "proper_implementation": [
                "Upgrade from single-hour optimization to multi-period optimization with forecasts and battery charge planning.",
                "Track where battery energy came from so renewable accounting is physically correct.",
                "Use explicit reliability constraints, demand-charge penalties, and fallback policies for bad forecasts."
            ]
        },
    }


def display_strategy_guide(selected_strategy):
    """Explain what each strategy is doing and how it would be built properly."""
    st.divider()
    st.header("How The Strategies Work")
    st.caption(
        "This section describes the prototype logic that is running right now and the extra pieces needed for a production-ready implementation."
    )

    details = get_strategy_details()
    strategy_order = ["baseline", "carbon_min", "cost_min", "balanced", "optimized"]

    for strategy in strategy_order:
        detail = details[strategy]
        title = f"{strategy.upper()} {'(selected)' if strategy == selected_strategy else ''}".strip()
        with st.expander(title, expanded=(strategy == selected_strategy)):
            st.markdown(f"**Current prototype behavior:** {detail['what_it_does']}")
            st.markdown(f"**What happens when you run it:** {detail['what_happens']}")
            st.markdown("**Current implementation steps**")
            for step in detail["prototype_logic"]:
                st.markdown(f"- {step}")
            st.markdown("**What a proper real-world version would add**")
            for step in detail["proper_implementation"]:
                st.markdown(f"- {step}")


def display_simulation_process(data, strategy):
    """Explain how the dashboard run is executed."""
    st.divider()
    st.header("How This Run Is Executed")

    weather_source = "real weather inputs when available, with synthetic fallback"
    carbon_source = "Electricity Maps carbon data when configured, otherwise synthetic hourly carbon profile"
    price_source = "Electricity Maps price data when configured, otherwise synthetic hourly price profile"

    demand_rows = len(data["demand"])
    start_time = data["demand"].index.min()
    end_time = data["demand"].index.max()
    config = data.get("config", {})
    scenario_profile = config.get("scenario_profile", "realistic")
    carbon_weight = float(config.get("balanced_carbon_weight", 0.5))
    cost_weight = float(config.get("balanced_cost_weight", 0.5))

    st.markdown(
        f"The dashboard runs `{strategy}` over `{demand_rows}` hourly steps from `{start_time}` to `{end_time}`. "
        "For each hour, it builds demand, reads carbon intensity, price, weather, and solar availability, then asks the selected strategy how to split the load across grid, solar, and battery."
    )
    st.markdown(
        f"Scenario profile: `{scenario_profile}`. Balanced tradeoff weights: carbon `{carbon_weight:.2f}`, cost `{cost_weight:.2f}`."
    )

    st.markdown("**Inputs used in this run**")
    st.markdown(f"- Demand: hourly data center load profile generated for the selected horizon")
    st.markdown(f"- Carbon intensity: {carbon_source}")
    st.markdown(f"- Electricity price: {price_source}")
    st.markdown(f"- Weather and solar: {weather_source}")
    st.markdown("- Battery model: finite capacity, finite power, state of charge, and simple degradation")

    st.markdown("**What the simulator does each hour**")
    st.markdown("- Starts with the current demand and optional flexible-load shift adjustments")
    st.markdown("- Estimates solar generation from weather or uses supplied solar generation data")
    st.markdown("- Computes battery discharge limit from current state of charge and max power")
    st.markdown("- Runs the selected dispatch logic to choose grid, solar, and battery output")
    st.markdown("- Updates battery state of charge, then records dispatch, cost, emissions, and shifts")

    st.info(
        "Important limitation: this is still a prototype simulator. The optimized mode is now load-feasible, but it is still a single-hour optimizer, not a full day-ahead control system."
    )


@st.cache_data(show_spinner=False)
def get_location_label(latitude, longitude):
    """Return a readable place name for the selected coordinates."""
    return lookup_location_name(float(latitude), float(longitude))


@st.cache_data(show_spinner=False)
def get_current_weather_preview(latitude, longitude):
    """Return current weather for the selected coordinates."""
    return WeatherAPI().get_current_weather(float(latitude), float(longitude))


def c_to_f(temp_c):
    """Convert Celsius to Fahrenheit."""
    return (temp_c * 9 / 5) + 32


def ms_to_mph(speed_ms):
    """Convert meters per second to miles per hour."""
    return speed_ms * 2.23694


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
    st.sidebar.caption(f"Nearest place: {get_location_label(latitude, longitude)}")
    st.sidebar.caption(
        f"Coordinate signs: "
        f"{abs(latitude):.4f}° {'N' if latitude >= 0 else 'S'}, "
        f"{abs(longitude):.4f}° {'E' if longitude >= 0 else 'W'}"
    )
    if longitude > 0:
        st.sidebar.warning(
            "Positive longitude means east of Greenwich. "
            "For U.S. cities like Madison or San Francisco, longitude should usually be negative."
        )

    current_weather = get_current_weather_preview(latitude, longitude)
    st.sidebar.caption("Current weather preview")
    st.sidebar.markdown(
        f"Temperature: {current_weather['temperature_c']:.1f} °C | {c_to_f(current_weather['temperature_c']):.1f} °F\n\n"
        f"Wind: {current_weather['wind_speed_ms']:.1f} m/s | {ms_to_mph(current_weather['wind_speed_ms']):.1f} mph\n\n"
        f"Cloud cover: {current_weather['cloud_cover'] * 100:.0f}%"
    )

    carbon_provider = os.getenv("ECODISPATCH_CARBON_PROVIDER")
    price_provider = os.getenv("ECODISPATCH_PRICE_PROVIDER")
    has_emaps_token = bool(os.getenv("ELECTRICITYMAPS_API_TOKEN"))
    carbon_provider = (carbon_provider.lower() if carbon_provider else ("electricitymaps" if has_emaps_token else "synthetic"))
    price_provider = (price_provider.lower() if price_provider else ("electricitymaps" if has_emaps_token else "synthetic"))

    weather_status = "Real weather via Open-Meteo"
    carbon_status = "Real carbon via Electricity Maps" if carbon_provider == "electricitymaps" and has_emaps_token else "Synthetic carbon fallback"
    price_status = "Real price via Electricity Maps" if price_provider == "electricitymaps" and has_emaps_token else "Synthetic price fallback"

    st.sidebar.caption(
        f"Data sources: {weather_status} | {carbon_status} | {price_status}"
    )
    carbon_detail = (
        "- Carbon: live via Electricity Maps"
        if carbon_provider == "electricitymaps" and has_emaps_token
        else "- Carbon: real only with a live Electricity Maps token"
    )
    price_detail = (
        "- Price: live via Electricity Maps"
        if price_provider == "electricitymaps" and has_emaps_token
        else "- Price: real only with a live Electricity Maps token"
    )

    st.sidebar.info(
        "Data realism:\n"
        "- Weather: real for the selected latitude/longitude\n"
        "- Solar output: modeled from real location + weather\n"
        f"{carbon_detail}\n"
        f"{price_detail}\n"
        "- Demand: still simulated"
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
    scenario = st.sidebar.selectbox(
        "Scenario Profile",
        ["realistic", "stress_test", "solar_rich", "volatile_market"],
        format_func=lambda x: {
            "realistic": "Realistic",
            "stress_test": "Stress Test",
            "solar_rich": "Solar Rich",
            "volatile_market": "Volatile Market",
        }[x],
        help="Use stress-test scenarios to amplify price, carbon, or solar conditions."
    )
    st.sidebar.subheader("Balanced Strategy Weights")
    balanced_carbon_weight = st.sidebar.slider(
        "Carbon Weight",
        0.0, 1.0, 0.5,
        help="Higher values make BALANCED prioritize lower-carbon hours more strongly."
    )
    balanced_cost_weight = 1.0 - balanced_carbon_weight
    st.sidebar.caption(
        f"Balanced weights: carbon {balanced_carbon_weight:.2f} | cost {balanced_cost_weight:.2f}"
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
        run_simulation(
            latitude,
            longitude,
            battery_capacity,
            solar_capacity,
            flexible_load_fraction,
            days,
            strategy,
            scenario,
            balanced_carbon_weight,
            balanced_cost_weight,
        )

    if compare_button:
        compare_all_strategies(
            latitude,
            longitude,
            battery_capacity,
            solar_capacity,
            flexible_load_fraction,
            days,
            scenario,
            balanced_carbon_weight,
            balanced_cost_weight,
        )


# ============================================================================
# SIMULATION FUNCTIONS
# ============================================================================

def run_simulation(latitude, longitude, battery_capacity, solar_capacity,
                  flexible_load_fraction, days, strategy, scenario,
                  balanced_carbon_weight, balanced_cost_weight):
    """Run single strategy simulation and display results."""
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("📊 Loading data...")
        progress_bar.progress(20)

        data = load_real_data(latitude, longitude, days)
        data = apply_scenario_profile(data, scenario, solar_capacity, latitude, longitude)

        progress_bar.progress(40)
        status_text.text("🔄 Running simulation...")

        data['demand']['flexible_fraction'] = flexible_load_fraction
        data['config'] = {
            'latitude': latitude,
            'longitude': longitude,
            'battery_capacity_kwh': battery_capacity,
            'battery_max_power_kw': min(200.0, battery_capacity * 0.25),
            'solar_capacity_kw': solar_capacity,
            'flexible_load_fraction': flexible_load_fraction,
            'balanced_carbon_weight': balanced_carbon_weight,
            'balanced_cost_weight': balanced_cost_weight,
            'scenario_profile': scenario,
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
                          flexible_load_fraction, days, scenario,
                          balanced_carbon_weight, balanced_cost_weight):
    """Compare all 5 strategies side-by-side."""
    strategies = ["baseline", "carbon_min", "cost_min", "balanced", "optimized"]
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        status_text.text("📊 Loading data...")
        progress_bar.progress(10)

        data = load_real_data(latitude, longitude, days)
        data = apply_scenario_profile(data, scenario, solar_capacity, latitude, longitude)
        data['demand']['flexible_fraction'] = flexible_load_fraction
        data['config'] = {
            'latitude': latitude,
            'longitude': longitude,
            'battery_capacity_kwh': battery_capacity,
            'battery_max_power_kw': min(200.0, battery_capacity * 0.25),
            'solar_capacity_kw': solar_capacity,
            'flexible_load_fraction': flexible_load_fraction,
            'balanced_carbon_weight': balanced_carbon_weight,
            'balanced_cost_weight': balanced_cost_weight,
            'scenario_profile': scenario,
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
                'Renewable (%)': float(metrics['renewable_fraction'] * 100),
                'Load Served (%)': float(metrics['load_served_fraction'] * 100),
                'Unmet Demand (kWh)': float(metrics['unmet_demand_kwh'])
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
            help="Percentage of served energy met directly by on-site solar. Battery discharge is not counted as renewable unless its charge source is tracked."
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        served_pct = metrics['load_served_fraction'] * 100
        st.metric(
            "Load Served",
            f"{served_pct:.1f}%",
            help="How much of the modeled demand was served by this strategy"
        )

    with col2:
        unmet = metrics['unmet_demand_kwh']
        st.metric(
            "Unmet Demand",
            f"{unmet:,.1f} kWh",
            help="Modeled demand that was not served during the run"
        )

    with col3:
        served = metrics['total_served_kwh']
        demand = metrics['total_demand_kwh']
        st.metric(
            "Served / Demand",
            f"{served:,.0f} / {demand:,.0f} kWh",
            help="Total energy served compared with total modeled demand"
        )

    display_simulation_process(data, strategy)
    display_strategy_guide(strategy)

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
        display_weather_section_v2(data)

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


def display_weather_section_v2(data):
    """Display weather metrics with metric and imperial units."""
    try:
        weather = data['weather']

        col1, col2, col3 = st.columns(3)

        with col1:
            temp = float(weather['temperature_c'].mean())
            temp_min = float(weather['temperature_c'].min())
            temp_max = float(weather['temperature_c'].max())
            st.metric(
                "Avg Temperature",
                f"{temp:.1f} C / {c_to_f(temp):.1f} F",
                help=(
                    f"Range: {temp_min:.1f} C to {temp_max:.1f} C | "
                    f"{c_to_f(temp_min):.1f} F to {c_to_f(temp_max):.1f} F"
                )
            )

        with col2:
            cloud = float(weather['cloud_cover'].mean() * 100)
            st.metric(
                "Avg Cloud Cover",
                f"{cloud:.1f}%",
                help="Higher cloud cover usually means less solar generation"
            )

        with col3:
            wind = float(weather['wind_speed_ms'].mean())
            wind_min = float(weather['wind_speed_ms'].min())
            wind_max = float(weather['wind_speed_ms'].max())
            st.metric(
                "Avg Wind Speed",
                f"{wind:.1f} m/s / {ms_to_mph(wind):.1f} mph",
                help=(
                    f"Range: {wind_min:.1f} to {wind_max:.1f} m/s | "
                    f"{ms_to_mph(wind_min):.1f} to {ms_to_mph(wind_max):.1f} mph"
                )
            )

        st.caption(
            "Weather units: temperature is shown in Celsius and Fahrenheit; wind speed is shown in meters per second and miles per hour."
        )
    except Exception as e:
        st.warning(f"Could not display weather: {e}")


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
    numeric_columns = [
        'Emissions (kgCO2)',
        'Cost ($)',
        'Peak Grid (kW)',
        'Renewable (%)',
        'Load Served (%)',
        'Unmet Demand (kWh)'
    ]
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
            'Renewable (%)': '{:.1f}%',
            'Load Served (%)': '{:.1f}%',
            'Unmet Demand (kWh)': '{:,.1f}'
        }).background_gradient(subset=['Emissions (kgCO2)'], cmap='RdYlGn_r').background_gradient(
            subset=['Cost ($)'], cmap='RdYlGn_r'
        ).background_gradient(subset=['Renewable (%)'], cmap='RdYlGn').background_gradient(
            subset=['Load Served (%)'], cmap='RdYlGn'
        ).background_gradient(subset=['Unmet Demand (kWh)'], cmap='RdYlGn_r'),
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

    feasible_df = df[df['Load Served (%)'] >= 99.9]
    ranking_df = feasible_df if not feasible_df.empty else df
    ranking_sorted = ranking_df.sort_values('Emissions (kgCO2)')

    best_emissions = ranking_sorted.iloc[0]
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
