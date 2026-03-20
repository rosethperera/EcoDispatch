"""
Core simulation engine for EcoDispatch.

Handles time-series simulation of data center energy systems.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .models import Battery, SolarPV, DemandProfile
from .dispatch import DispatchStrategy, Strategy
from .metrics import calculate_metrics


class EcoDispatch:
    """
    Main simulation class for carbon-aware data center energy dispatch.
    """

    def __init__(self, battery: Battery, solar: SolarPV, demand: DemandProfile):
        """
        Initialize the EcoDispatch simulator.

        Args:
            battery: Battery storage model
            solar: Solar PV generation model
            demand: Data center demand profile
        """
        self.battery = battery
        self.solar = solar
        self.demand = demand

    @classmethod
    def simulate(cls, data: Dict[str, pd.DataFrame],
                 strategy: str = 'baseline') -> Dict[str, pd.DataFrame]:
        """
        Run a complete simulation.

        Args:
            data: Dictionary containing input dataframes
            strategy: Dispatch strategy ('baseline', 'carbon_min', 'cost_min', 'balanced', 'optimized')

        Returns:
            Dictionary of simulation results
        """
        config = data.get('config', {})
        demand_df = data['demand']
        avg_demand_kw = float(demand_df['demand_kw'].mean()) if 'demand_kw' in demand_df else 1000.0

        battery_capacity_kwh = float(config.get('battery_capacity_kwh', 1000))
        battery_max_power_kw = float(
            config.get('battery_max_power_kw', min(200.0, battery_capacity_kwh * 0.25))
        )
        solar_capacity_kw = float(config.get('solar_capacity_kw', 500))
        flexible_fraction = float(
            config.get(
                'flexible_load_fraction',
                demand_df['flexible_fraction'].iloc[0] if 'flexible_fraction' in demand_df else 0.3
            )
        )
        latitude = float(config.get('latitude', 37.7749))
        longitude = float(config.get('longitude', -122.4194))

        # Initialize models with user-selected parameters when available.
        battery = Battery(
            capacity_kwh=battery_capacity_kwh,
            max_power_kw=battery_max_power_kw,
            efficiency=0.95,
            degradation_rate=0.0001,
            temperature_c=25
        )
        solar = SolarPV(capacity_kw=solar_capacity_kw, latitude=latitude, longitude=longitude)
        demand = DemandProfile(base_load_kw=avg_demand_kw, flexible_fraction=flexible_fraction)

        simulator = cls(battery, solar, demand)

        # Run simulation
        results = simulator._run_simulation(data, strategy)

        return results

    def _run_simulation(self, data: Dict[str, pd.DataFrame],
                       strategy: str) -> Dict[str, pd.DataFrame]:
        """
        Internal simulation method.
        """
        timestamps = data['demand'].index
        n_steps = len(timestamps)

        # Initialize results dataframes
        dispatch_df = pd.DataFrame(index=timestamps, columns=['grid', 'solar', 'battery'])
        battery_soc_df = pd.DataFrame(index=timestamps, columns=['soc'])
        emissions_df = pd.DataFrame(index=timestamps, columns=['emissions_gco2'])
        costs_df = pd.DataFrame(index=timestamps, columns=['cost_usd'])
        workload_shift_df = pd.DataFrame(index=timestamps, columns=['shifted_load_kw'])
        solar_available_df = pd.DataFrame(index=timestamps, columns=['solar_kw'])

        # Initialize dispatch strategy with workload scheduler
        from .dispatch import WorkloadScheduler
        workload_scheduler = WorkloadScheduler(max_shift_hours=4)
        dispatch_strategy = DispatchStrategy(Strategy(strategy), workload_scheduler)

        # Pre-calculate carbon profile for workload shifting
        carbon_profile = data['carbon_intensity']['carbon_gco2_per_kwh'].values
        demand_profile = data['demand']['demand_kw'].values
        flexible_fraction_series = (
            data['demand']['flexible_fraction']
            if 'flexible_fraction' in data['demand']
            else pd.Series(self.demand.flexible_fraction, index=timestamps)
        )

        # Track shifted workloads (simplified - in practice would need more sophisticated scheduling)
        shifted_loads = np.zeros(n_steps)

        # Simulation loop
        for i, ts in enumerate(timestamps):
            # Use the loaded demand profile instead of a canned daily shape.
            base_demand = float(demand_profile[i])
            flexible_fraction = float(flexible_fraction_series.iloc[i])
            flexible_fraction = min(max(flexible_fraction, 0.0), 1.0)
            demand_breakdown = {
                'critical': base_demand * (1 - flexible_fraction),
                'flexible': base_demand * flexible_fraction,
                'total': base_demand
            }

            # Apply workload shifting for carbon_min strategy
            flexible_load = demand_breakdown['flexible']
            current_demand = base_demand

            if strategy == 'carbon_min' and flexible_load > 0:
                # Find optimal shift (simplified - only shift if current hour has high carbon)
                current_carbon = carbon_profile[i]
                if current_carbon > np.mean(carbon_profile) * 1.2:  # Above average carbon
                    optimal_hour, savings = workload_scheduler.find_optimal_shift(
                        i, carbon_profile, demand_profile, flexible_load * 0.5
                    )
                    if savings > 0 and abs(optimal_hour - i) <= 4:  # Within shift window
                        shift_amount = min(flexible_load * 0.5, base_demand * 0.2)
                        shifted_loads[i] -= shift_amount
                        shifted_loads[optimal_hour] += shift_amount
                        workload_shift_df.loc[ts, 'shifted_load_kw'] = -shift_amount

            # Add any shifted load from previous decisions
            current_demand += shifted_loads[i]
            if shifted_loads[i] > 0:
                workload_shift_df.loc[ts, 'shifted_load_kw'] = shifted_loads[i]

            # Get carbon intensity and price
            carbon_intensity = data['carbon_intensity']['carbon_gco2_per_kwh'].iloc[i]
            price = data['price']['price_usd_per_kwh'].iloc[i]

            # Calculate solar generation with weather data (use defaults if not available)
            cloud_cover = data['weather']['cloud_cover'].iloc[i] if 'weather' in data and 'cloud_cover' in data['weather'].columns else 0.0
            temperature = data['weather']['temperature_c'].iloc[i] if 'weather' in data and 'temperature_c' in data['weather'].columns else 25
            wind_speed = data['weather']['wind_speed_ms'].iloc[i] if 'weather' in data and 'wind_speed_ms' in data['weather'].columns else 1.0

            if 'solar_generation' in data and 'solar_kw' in data['solar_generation'].columns:
                solar_generation = float(data['solar_generation']['solar_kw'].iloc[i])
            else:
                solar_generation = float(self.solar.generate(ts, cloud_cover, temperature, wind_speed))

            # Available sources
            available_sources = {
                'grid': float('inf'),  # Assume unlimited grid
                'solar': solar_generation,
                'battery': min(self.battery.max_power, self.battery.capacity * self.battery.soc)
            }

            # Decide dispatch
            dispatch = dispatch_strategy.decide_dispatch(
                available_sources, current_demand, carbon_intensity, price, self.battery.soc, flexible_load
            )

            # Update battery state
            net_battery_power = dispatch['battery']  # Positive = discharge, negative = charge
            if net_battery_power > 0:
                # Discharge
                actual_discharge = self.battery.discharge(net_battery_power, 1.0)
                dispatch['battery'] = actual_discharge
            elif net_battery_power < 0:
                # Charge
                actual_charge = self.battery.charge(-net_battery_power, 1.0)
                dispatch['battery'] = -actual_charge  # Negative for charging

            # Apply battery degradation
            self.battery.apply_degradation()

            # Store results
            dispatch_df.loc[ts] = dispatch
            battery_soc_df.loc[ts, 'soc'] = self.battery.soc
            emissions_df.loc[ts, 'emissions_gco2'] = dispatch['grid'] * carbon_intensity
            costs_df.loc[ts, 'cost_usd'] = dispatch['grid'] * price
            solar_available_df.loc[ts, 'solar_kw'] = solar_generation

        results = {
            'dispatch': dispatch_df.astype(float),
            'battery_soc': battery_soc_df.astype(float),
            'emissions': emissions_df.astype(float),
            'costs': costs_df.astype(float),
            'workload_shifts': workload_shift_df.astype(float).fillna(0.0),
            'solar_available': solar_available_df['solar_kw'].astype(float)
        }

        return results

    @staticmethod
    def visualize(results: Dict[str, pd.DataFrame]):
        """
        Generate visualization dashboard.

        Args:
            results: Simulation results dictionary
        """
        # Placeholder for visualization
        pass
