"""
Mathematical models for energy system components.
"""

import numpy as np
from typing import Optional, Dict


class Battery:
    """
    Battery storage model with capacity, efficiency, power constraints, and degradation.
    """

    def __init__(self, capacity_kwh: float, max_power_kw: float,
                 efficiency: float = 0.95, initial_soc: float = 0.5,
                 degradation_rate: float = 0.0001, temperature_c: float = 25):
        """
        Initialize battery model.

        Args:
            capacity_kwh: Battery capacity in kWh
            max_power_kw: Maximum charge/discharge power in kW
            efficiency: Round-trip efficiency (0-1)
            initial_soc: Initial state of charge (0-1)
            degradation_rate: Capacity degradation per cycle (0-1)
            temperature_c: Operating temperature in °C
        """
        self.initial_capacity = capacity_kwh
        self.capacity = capacity_kwh
        self.max_power = max_power_kw
        self.efficiency = efficiency
        self.soc = initial_soc
        self.degradation_rate = degradation_rate
        self.temperature_c = temperature_c
        self.cycles = 0
        self.energy_throughput = 0  # Total energy cycled in kWh

    def charge(self, power_kw: float, dt_hours: float = 1.0) -> float:
        """
        Charge the battery.

        Args:
            power_kw: Charging power in kW
            dt_hours: Time step in hours

        Returns:
            Actual energy charged in kWh
        """
        # Temperature derating
        temp_factor = self._temperature_factor()
        available_power = self.max_power * temp_factor

        power_kw = min(power_kw, available_power)
        energy_kwh = power_kw * dt_hours
        available_capacity = self.capacity * (1 - self.soc)
        energy_kwh = min(energy_kwh, available_capacity)

        self.soc += energy_kwh / self.capacity
        self.energy_throughput += energy_kwh
        return energy_kwh

    def discharge(self, power_kw: float, dt_hours: float = 1.0) -> float:
        """
        Discharge the battery.

        Args:
            power_kw: Discharging power in kW
            dt_hours: Time step in hours

        Returns:
            Actual energy discharged in kWh
        """
        # Temperature derating
        temp_factor = self._temperature_factor()
        available_power = self.max_power * temp_factor

        power_kw = min(power_kw, available_power)
        energy_kwh = power_kw * dt_hours
        available_energy = self.capacity * self.soc
        energy_kwh = min(energy_kwh, available_energy)

        self.soc -= energy_kwh / self.capacity
        self.energy_throughput += energy_kwh
        return energy_kwh

    def apply_degradation(self):
        """
        Apply cycle-based degradation to battery capacity.
        """
        # Estimate cycles based on energy throughput
        # Rough approximation: 1 cycle = 1 full discharge
        new_cycles = self.energy_throughput / self.initial_capacity
        cycle_degradation = new_cycles * self.degradation_rate

        # Calendar aging (simplified)
        calendar_degradation = 0.00001  # Per time step

        total_degradation = min(cycle_degradation + calendar_degradation, 0.3)  # Max 30% degradation
        self.capacity = self.initial_capacity * (1 - total_degradation)

    def _temperature_factor(self) -> float:
        """
        Calculate temperature derating factor.

        Returns:
            Power derating factor (0-1)
        """
        # Simplified temperature model
        if self.temperature_c < 0:
            return 0.5  # Cold temperature derating
        elif self.temperature_c > 45:
            return 0.7  # Hot temperature derating
        else:
            return 1.0  # Optimal temperature


class SolarPV:
    """
    Solar photovoltaic generation model with weather effects.
    """

    def __init__(self, capacity_kw: float, efficiency: float = 0.2,
                 latitude: float = 37.7749, longitude: float = -122.4194,
                 tilt_angle: float = 30, azimuth_angle: float = 180):
        """
        Initialize solar PV model.

        Args:
            capacity_kw: Installed capacity in kW
            efficiency: System efficiency (0-1)
            latitude: Location latitude in degrees
            longitude: Location longitude in degrees
            tilt_angle: Panel tilt angle in degrees (0=horizontal, 90=vertical)
            azimuth_angle: Panel azimuth angle in degrees (180=south-facing)
        """
        self.capacity = capacity_kw
        self.efficiency = efficiency
        self.latitude = latitude
        self.longitude = longitude
        self.tilt = tilt_angle
        self.azimuth = azimuth_angle

    def generate(self, datetime, cloud_cover: float = 0.0,
                temperature_c: float = 25, wind_speed_ms: float = 1.0) -> float:
        """
        Calculate PV generation with weather effects.

        Args:
            datetime: Pandas Timestamp for the time
            cloud_cover: Cloud cover fraction (0-1)
            temperature_c: Ambient temperature in °C
            wind_speed_ms: Wind speed in m/s

        Returns:
            Power generation in kW
        """
        # Calculate clear sky irradiance
        clear_irradiance = self._clear_sky_irradiance(datetime)

        # Apply weather effects
        irradiance = clear_irradiance * (1 - 0.75 * cloud_cover)  # Cloud attenuation

        # Temperature derating
        temp_derate = 1 - 0.005 * (temperature_c - 25)

        # Wind cooling effect (slight performance boost)
        wind_boost = 1 + 0.001 * wind_speed_ms

        # Calculate power
        power_kw = self.capacity * (irradiance / 1000) * self.efficiency * temp_derate * wind_boost

        return np.maximum(0, power_kw)

    def _clear_sky_irradiance(self, datetime) -> float:
        """
        Calculate clear sky irradiance using simplified solar position model.

        Args:
            datetime: Pandas Timestamp

        Returns:
            Irradiance in W/m²
        """
        # Extract time components
        day_of_year = datetime.dayofyear
        hour = datetime.hour + datetime.minute / 60.0

        # Solar declination (simplified)
        declination = 23.45 * np.sin(np.radians(360 * (284 + day_of_year) / 365))

        # Equation of time (simplified)
        equation_of_time = 4 * (0.000075 + 0.001868 * np.cos(np.radians(360 * day_of_year / 365)) -
                               0.032077 * np.sin(np.radians(360 * day_of_year / 365)) -
                               0.014615 * np.cos(np.radians(720 * day_of_year / 365)) -
                               0.040849 * np.sin(np.radians(720 * day_of_year / 365)))

        # Solar time
        solar_time = hour + equation_of_time / 60 + self.longitude / 15

        # Hour angle
        hour_angle = 15 * (solar_time - 12)

        # Solar elevation angle
        elevation = np.arcsin(
            np.sin(np.radians(self.latitude)) * np.sin(np.radians(declination)) +
            np.cos(np.radians(self.latitude)) * np.cos(np.radians(declination)) * np.cos(np.radians(hour_angle))
        )

        # Solar azimuth angle
        azimuth = np.arctan2(
            np.sin(np.radians(hour_angle)),
            np.cos(np.radians(hour_angle)) * np.sin(np.radians(self.latitude)) -
            np.tan(np.radians(declination)) * np.cos(np.radians(self.latitude))
        )

        # Convert to degrees
        elevation_deg = np.degrees(elevation)
        azimuth_deg = np.degrees(azimuth)

        # Air mass (simplified)
        air_mass = 1 / np.cos(np.radians(90 - elevation_deg))

        # Extraterrestrial irradiance
        solar_constant = 1366  # W/m²
        extraterrestrial = solar_constant * (1 + 0.033 * np.cos(np.radians(360 * day_of_year / 365)))

        # Clear sky irradiance model (simplified)
        irradiance = extraterrestrial * np.exp(-0.000118 * elevation_deg - 0.001127 * air_mass)

        # Incidence angle modifier for tilted panels
        incidence_angle = self._incidence_angle(elevation_deg, azimuth_deg)
        incidence_modifier = np.cos(np.radians(incidence_angle))

        # Apply night time condition
        irradiance = np.where(elevation_deg <= 0, 0, irradiance * incidence_modifier)

        return np.maximum(0, irradiance)

    def _incidence_angle(self, solar_elevation: float, solar_azimuth: float) -> float:
        """
        Calculate incidence angle on tilted panel.

        Args:
            solar_elevation: Solar elevation angle in degrees
            solar_azimuth: Solar azimuth angle in degrees

        Returns:
            Incidence angle in degrees
        """
        # Simplified incidence angle calculation
        zenith = 90 - solar_elevation
        azimuth_diff = solar_azimuth - self.azimuth

        cos_incidence = (np.cos(np.radians(zenith)) * np.cos(np.radians(self.tilt)) +
                        np.sin(np.radians(zenith)) * np.sin(np.radians(self.tilt)) * np.cos(np.radians(azimuth_diff)))

        incidence = np.arccos(np.clip(cos_incidence, -1, 1))
        return np.degrees(incidence)


class DemandProfile:
    """
    Data center demand profile model with critical and flexible loads.
    """

    def __init__(self, base_load_kw: float = 1000,
                 peak_factor: float = 1.5, flexible_fraction: float = 0.3):
        """
        Initialize demand profile.

        Args:
            base_load_kw: Base load in kW
            peak_factor: Peak load multiplier
            flexible_fraction: Fraction of load that can be shifted (0-1)
        """
        self.base_load = base_load_kw
        self.peak_factor = peak_factor
        self.flexible_fraction = flexible_fraction

    def get_demand(self, hour_of_day: int, day_of_week: int = 0) -> Dict[str, float]:
        """
        Get demand for given time, split into critical and flexible.

        Args:
            hour_of_day: Hour of day (0-23)
            day_of_week: Day of week (0-6, 0=Monday)

        Returns:
            Dict with 'critical' and 'flexible' demand in kW
        """
        # Calculate total demand
        if 9 <= hour_of_day <= 17:  # Peak hours
            total_demand = self.base_load * self.peak_factor
        else:
            total_demand = self.base_load

        # Split into critical and flexible
        critical_demand = total_demand * (1 - self.flexible_fraction)
        flexible_demand = total_demand * self.flexible_fraction

        return {
            'critical': critical_demand,
            'flexible': flexible_demand,
            'total': total_demand
        }

    def shift_flexible_load(self, original_hour: int, new_hour: int,
                           flexible_load_kw: float) -> Dict[str, float]:
        """
        Shift flexible load from one hour to another.

        Args:
            original_hour: Original hour (0-23)
            new_hour: New hour (0-23)
            flexible_load_kw: Amount of flexible load to shift

        Returns:
            Dict with load changes for original and new hours
        """
        return {
            'original_hour_change': -flexible_load_kw,
            'new_hour_change': flexible_load_kw
        }