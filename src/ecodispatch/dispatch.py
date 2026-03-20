"""
Energy dispatch optimization algorithms with workload shifting.
"""

import numpy as np
from typing import Dict, List, Tuple
from enum import Enum
from scipy.optimize import minimize_scalar, minimize


class Strategy(Enum):
    BASELINE = "baseline"
    CARBON_MIN = "carbon_min"
    COST_MIN = "cost_min"
    BALANCED = "balanced"
    OPTIMIZED = "optimized"


class WorkloadScheduler:
    """
    Handles flexible workload shifting decisions.
    """

    def __init__(self, max_shift_hours: int = 4):
        """
        Initialize workload scheduler.

        Args:
            max_shift_hours: Maximum hours a workload can be shifted
        """
        self.max_shift_hours = max_shift_hours

    def find_optimal_shift(self, current_hour: int, carbon_profile: np.ndarray,
                          demand_profile: np.ndarray, flexible_load: float) -> Tuple[int, float]:
        """
        Find optimal hour to shift flexible load to minimize carbon emissions.

        Args:
            current_hour: Current hour index
            carbon_profile: Carbon intensity for all hours (gCO2/kWh)
            demand_profile: Base demand for all hours (kW)
            flexible_load: Amount of flexible load to shift (kW)

        Returns:
            Tuple of (optimal_hour, carbon_savings)
        """
        n_hours = len(carbon_profile)
        best_hour = current_hour
        max_savings = 0

        # Search within shift window
        start_hour = current_hour + 1
        end_hour = min(n_hours, current_hour + self.max_shift_hours + 1)

        for hour in range(start_hour, end_hour):
            if hour == current_hour:
                continue

            # Calculate carbon impact of shifting
            current_carbon = carbon_profile[current_hour] * flexible_load
            new_carbon = carbon_profile[hour] * flexible_load

            savings = current_carbon - new_carbon
            if savings > max_savings:
                max_savings = savings
                best_hour = hour

        return best_hour, max_savings


class DispatchStrategy:
    """
    Energy dispatch decision making with optimization.
    """

    def __init__(self, strategy: Strategy, workload_scheduler: WorkloadScheduler = None):
        """
        Initialize dispatch strategy.

        Args:
            strategy: Optimization strategy
            workload_scheduler: Optional workload scheduler for flexible loads
        """
        self.strategy = strategy
        self.workload_scheduler = workload_scheduler or WorkloadScheduler()

    def decide_dispatch(self, available_sources: Dict[str, float],
                       demand_kw: float, carbon_intensity: float,
                       price: float, battery_soc: float,
                       flexible_load: float = 0) -> Dict[str, float]:
        """
        Decide how to dispatch energy sources.

        Args:
            available_sources: Dict of available power by source (grid, solar, battery)
            demand_kw: Required demand in kW
            carbon_intensity: Grid carbon intensity (gCO2/kWh)
            price: Electricity price ($/kWh)
            battery_soc: Battery state of charge (0-1)
            flexible_load: Amount of flexible load that could be shifted

        Returns:
            Dict of dispatched power by source
        """
        # Ensure parameters are scalars
        demand_kw = float(demand_kw)
        carbon_intensity = float(carbon_intensity)
        price = float(price)
        battery_soc = float(battery_soc)
        flexible_load = float(flexible_load)
        available_sources = {k: float(v) for k, v in available_sources.items()}

        dispatch = {'grid': 0.0, 'solar': 0.0, 'battery': 0.0}

        if self.strategy == Strategy.OPTIMIZED:
            return self._optimize_dispatch(available_sources, demand_kw,
                                         carbon_intensity, price, battery_soc)

        if self.strategy == Strategy.BASELINE:
            # Always use grid first, then solar, then battery
            dispatch['grid'] = min(demand_kw, available_sources['grid'])
            remaining = demand_kw - dispatch['grid']
            dispatch['solar'] = min(remaining, available_sources['solar'])
            remaining = remaining - dispatch['solar']
            dispatch['battery'] = min(remaining, available_sources['battery'])

        elif self.strategy == Strategy.CARBON_MIN:
            # Prioritize low-carbon sources
            # Use solar first, then battery, then grid
            dispatch['solar'] = min(demand_kw, available_sources['solar'])
            remaining = demand_kw - dispatch['solar']
            dispatch['battery'] = min(remaining, available_sources['battery'])
            remaining = remaining - dispatch['battery']
            dispatch['grid'] = min(remaining, available_sources['grid'])

        elif self.strategy == Strategy.COST_MIN:
            # Prioritize cheap sources (assuming solar is free, battery has wear cost)
            # Simplified: solar first, then grid, then battery
            dispatch['solar'] = min(demand_kw, available_sources['solar'])
            remaining = demand_kw - dispatch['solar']
            dispatch['grid'] = min(remaining, available_sources['grid'])
            remaining = remaining - dispatch['grid']
            dispatch['battery'] = min(remaining, available_sources['battery'])

        elif self.strategy == Strategy.BALANCED:
            # Balance carbon and cost
            # Use solar, then mix grid/battery based on carbon and SOC
            dispatch['solar'] = min(demand_kw, available_sources['solar'])
            remaining = demand_kw - dispatch['solar']

            # If carbon intensity is high and battery has charge, prefer battery
            if carbon_intensity > 400 and battery_soc > 0.2:  # High carbon threshold
                dispatch['battery'] = min(remaining, available_sources['battery'])
                remaining = remaining - dispatch['battery']

            dispatch['grid'] = min(remaining, available_sources['grid'])
            remaining = remaining - dispatch['grid']

            # If still remaining and battery can provide, use it
            if remaining > 0:
                dispatch['battery'] += min(remaining, available_sources['battery'])

        return dispatch

    def _optimize_dispatch(self, available_sources: Dict[str, float],
                          demand_kw: float, carbon_intensity: float,
                          price: float, battery_soc: float) -> Dict[str, float]:
        """
        Use optimization to find best dispatch for single time step.
        """
        def objective(x):
            # x = [grid_fraction, solar_fraction, battery_fraction]
            grid_kw = x[0] * demand_kw
            solar_kw = x[1] * demand_kw
            battery_kw = x[2] * demand_kw

            # Constraints
            total = grid_kw + solar_kw + battery_kw
            if abs(total - demand_kw) > 1:  # Allow small tolerance
                return 1000000  # Large penalty

            # Limit by available sources
            if grid_kw > available_sources['grid'] or solar_kw > available_sources['solar'] or \
               battery_kw > available_sources['battery']:
                return 1000000

            # Multi-objective: minimize carbon + cost (normalized)
            carbon_cost = grid_kw * carbon_intensity
            monetary_cost = grid_kw * price * 100  # Scale to match carbon units
            battery_wear = abs(battery_kw) * 10  # Penalty for battery usage

            return carbon_cost + monetary_cost + battery_wear

        # Optimize
        bounds = [(0, 1), (0, 1), (0, 1)]
        constraints = [{'type': 'eq', 'fun': lambda x: x[0] + x[1] + x[2] - 1}]  # Sum to 1

        result = minimize(objective, [0.5, 0.3, 0.2], bounds=bounds, constraints=constraints)

        if result.success:
            grid_kw = result.x[0] * demand_kw
            solar_kw = result.x[1] * demand_kw
            battery_kw = result.x[2] * demand_kw
        else:
            # Fallback to balanced strategy
            grid_kw = min(demand_kw * 0.6, available_sources['grid'])
            solar_kw = min(demand_kw * 0.3, available_sources['solar'])
            battery_kw = min(demand_kw * 0.1, available_sources['battery'])

        return {
            'grid': grid_kw,
            'solar': solar_kw,
            'battery': battery_kw
        }
