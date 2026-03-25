"""
Energy dispatch optimization algorithms with workload shifting.
"""

import math
import numpy as np
from typing import Dict, List, Tuple
from enum import Enum
from scipy.optimize import minimize


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
                       flexible_load: float = 0,
                       strategy_context: Dict[str, float] = None) -> Dict[str, float]:
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
        strategy_context = strategy_context or {}

        if self.strategy == Strategy.OPTIMIZED:
            return self._optimize_dispatch(available_sources, demand_kw,
                                         carbon_intensity, price, battery_soc, strategy_context)

        if self.strategy == Strategy.BASELINE:
            # Always use grid first, then solar, then battery
            dispatch['grid'] = min(demand_kw, available_sources['grid'])
            remaining = demand_kw - dispatch['grid']
            dispatch['solar'] = min(remaining, available_sources['solar'])
            remaining = remaining - dispatch['solar']
            dispatch['battery'] = min(remaining, available_sources['battery'])

        elif self.strategy == Strategy.CARBON_MIN:
            # Prioritize low-carbon sources
            # Use solar first, then battery more aggressively during dirty hours.
            dispatch['solar'] = min(demand_kw, available_sources['solar'])
            remaining = demand_kw - dispatch['solar']
            high_carbon_threshold = float(strategy_context.get('high_carbon_threshold', carbon_intensity))
            carbon_pressure = np.clip(
                (carbon_intensity - high_carbon_threshold) / max(high_carbon_threshold, 1.0) + 1.0,
                0.35,
                1.0,
            )
            battery_budget = available_sources['battery'] * carbon_pressure
            dispatch['battery'] = min(remaining, battery_budget)
            remaining = remaining - dispatch['battery']
            dispatch['grid'] = min(remaining, available_sources['grid'])

        elif self.strategy == Strategy.COST_MIN:
            # Use battery mainly during expensive hours.
            dispatch['solar'] = min(demand_kw, available_sources['solar'])
            remaining = demand_kw - dispatch['solar']
            high_price_threshold = float(strategy_context.get('high_price_threshold', price))
            if price >= high_price_threshold and battery_soc > 0.2:
                dispatch['battery'] = min(remaining, available_sources['battery'])
                remaining -= dispatch['battery']
            dispatch['grid'] = min(remaining, available_sources['grid'])

        elif self.strategy == Strategy.BALANCED:
            # Balance carbon and cost using a combined score.
            dispatch['solar'] = min(demand_kw, available_sources['solar'])
            remaining = demand_kw - dispatch['solar']
            current_score = float(strategy_context.get('current_score', 0.5))
            if current_score >= 0.65 and battery_soc > 0.2:
                dispatch['battery'] = min(remaining, available_sources['battery'])
                remaining = remaining - dispatch['battery']

            dispatch['grid'] = min(remaining, available_sources['grid'])
            remaining = remaining - dispatch['grid']

            # If still remaining and battery can provide, use it
            if remaining > 0:
                dispatch['battery'] += min(remaining, available_sources['battery'])

        return dispatch

    def decide_charging(self, available_sources: Dict[str, float], dispatch: Dict[str, float],
                        carbon_intensity: float, price: float, battery_soc: float,
                        strategy_context: Dict[str, float] = None) -> Dict[str, float]:
        """
        Decide whether to charge the battery after serving the current hour's load.

        Returns:
            Dict with optional charging requests from solar and grid in kW.
        """
        strategy_context = strategy_context or {}
        remaining_solar = max(0.0, float(available_sources['solar']) - float(dispatch['solar']))
        battery_charge_limit = max(0.0, float(strategy_context.get('battery_charge_limit', 0.0)))
        if battery_charge_limit <= 0:
            return {'solar': 0.0, 'grid': 0.0}

        solar_charge = min(remaining_solar, battery_charge_limit)
        grid_charge = 0.0

        low_carbon_threshold = float(strategy_context.get('low_carbon_threshold', carbon_intensity))
        high_carbon_threshold = float(strategy_context.get('high_carbon_threshold', carbon_intensity))
        low_price_threshold = float(strategy_context.get('low_price_threshold', price))
        high_price_threshold = float(strategy_context.get('high_price_threshold', price))
        current_score = float(strategy_context.get('current_score', 0.5))
        future_max_score = float(strategy_context.get('future_max_score', current_score))
        future_high_carbon = bool(strategy_context.get('future_high_carbon', False))
        future_high_price = bool(strategy_context.get('future_high_price', False))

        remaining_capacity = max(0.0, battery_charge_limit - solar_charge)
        if self.strategy == Strategy.BASELINE:
            return {'solar': 0.0, 'grid': 0.0}

        if remaining_capacity <= 0 or battery_soc >= 0.95:
            return {'solar': solar_charge, 'grid': 0.0}

        if self.strategy == Strategy.CARBON_MIN:
            if carbon_intensity <= low_carbon_threshold and future_high_carbon and battery_soc < 0.9:
                grid_charge = remaining_capacity
        elif self.strategy == Strategy.COST_MIN:
            if price <= low_price_threshold and future_high_price and battery_soc < 0.9:
                grid_charge = remaining_capacity
        elif self.strategy == Strategy.BALANCED:
            if current_score <= 0.35 and future_max_score >= 0.65 and battery_soc < 0.9:
                grid_charge = remaining_capacity * 0.75
        elif self.strategy == Strategy.OPTIMIZED:
            opportunity_gap = max(0.0, future_max_score - current_score)
            if opportunity_gap >= 0.2 and battery_soc < 0.92:
                grid_charge = remaining_capacity * min(1.0, opportunity_gap / 0.4)

        return {
            'solar': solar_charge,
            'grid': max(0.0, min(grid_charge, remaining_capacity))
        }

    def _optimize_dispatch(self, available_sources: Dict[str, float],
                          demand_kw: float, carbon_intensity: float,
                          price: float, battery_soc: float,
                          strategy_context: Dict[str, float] = None) -> Dict[str, float]:
        """
        Use constrained optimization to find the best single-step dispatch.

        The optimizer must still serve the full demand. If the numerical solver
        fails, fall back to a deterministic heuristic that fills the remaining
        load with grid power instead of silently under-serving demand.
        """
        strategy_context = strategy_context or {}
        if demand_kw <= 0:
            return {'grid': 0.0, 'solar': 0.0, 'battery': 0.0}

        grid_limit = demand_kw if not math.isfinite(available_sources['grid']) else min(
            float(available_sources['grid']), demand_kw
        )
        solar_limit = min(float(available_sources['solar']), demand_kw)
        battery_limit = min(float(available_sources['battery']), demand_kw)

        current_score = float(strategy_context.get('current_score', 0.5))
        future_max_score = float(strategy_context.get('future_max_score', current_score))
        reserve_value = max(0.0, future_max_score - current_score)

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
            if grid_kw > grid_limit or solar_kw > solar_limit or battery_kw > battery_limit:
                return 1000000

            # Multi-objective: minimize carbon + cost (normalized)
            carbon_cost = grid_kw * carbon_intensity
            monetary_cost = grid_kw * price * 100  # Scale to match carbon units
            battery_wear = abs(battery_kw) * (6 + max(0.0, 0.4 - battery_soc) * 40 + reserve_value * 60)

            return carbon_cost + monetary_cost + battery_wear

        # Optimize
        bounds = [(0, 1), (0, 1), (0, 1)]
        constraints = [{'type': 'eq', 'fun': lambda x: x[0] + x[1] + x[2] - 1}]  # Sum to 1

        result = minimize(
            objective,
            [0.4, 0.4, 0.2],
            method='SLSQP',
            bounds=bounds,
            constraints=constraints,
        )

        if result.success:
            grid_kw = min(max(result.x[0], 0.0) * demand_kw, grid_limit)
            solar_kw = min(max(result.x[1], 0.0) * demand_kw, solar_limit)
            battery_kw = min(max(result.x[2], 0.0) * demand_kw, battery_limit)
        else:
            # Fallback heuristic: solar first, then battery if it is worth using,
            # and always cover any remaining demand with the grid.
            solar_kw = min(demand_kw, solar_limit)
            remaining = demand_kw - solar_kw

            battery_preferred = (
                (carbon_intensity > float(strategy_context.get('high_carbon_threshold', 325)))
                or (price > float(strategy_context.get('high_price_threshold', 0.14)))
                or (battery_soc > 0.75 and current_score >= 0.55)
            )
            battery_budget = battery_limit
            if battery_preferred and battery_soc > 0.15:
                battery_budget = min(battery_limit, remaining)
            else:
                battery_budget = min(battery_limit, remaining * 0.25)

            battery_kw = max(0.0, battery_budget)
            remaining -= battery_kw
            grid_kw = min(max(remaining, 0.0), grid_limit)

        served_kw = grid_kw + solar_kw + battery_kw
        if served_kw < demand_kw:
            grid_kw += min(demand_kw - served_kw, grid_limit - grid_kw)

        return {
            'grid': grid_kw,
            'solar': solar_kw,
            'battery': battery_kw
        }
