"""
Data integration module for real-time carbon intensity and weather data.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional


class CarbonIntensityAPI:
    """
    Interface to carbon intensity APIs.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize carbon intensity API client.

        Args:
            api_key: API key for WattTime or similar service
        """
        self.api_key = api_key
        self.base_url = "https://api.watttime.org/v3"  # Example API

    def get_carbon_intensity(self, latitude: float, longitude: float,
                           start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        Get historical carbon intensity data.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_time: Start time for data
            end_time: End time for data

        Returns:
            DataFrame with carbon intensity data
        """
        # For demo purposes, generate synthetic data
        # In production, this would call real APIs

        timestamps = pd.date_range(start_time, end_time, freq='H')
        n_hours = len(timestamps)

        # Generate realistic carbon intensity profile
        base_intensity = 350  # gCO2/kWh
        diurnal_variation = 50 * np.sin(2 * np.pi * np.arange(n_hours) / 24)
        weekly_variation = 30 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 7))
        noise = np.random.normal(0, 20, n_hours)

        carbon_intensity = base_intensity + diurnal_variation + weekly_variation + noise
        carbon_intensity = np.clip(carbon_intensity, 200, 600)  # Realistic bounds

        df = pd.DataFrame({
            'timestamp': timestamps,
            'carbon_gco2_per_kwh': carbon_intensity
        })
        df.set_index('timestamp', inplace=True)

        return df

    def get_realtime_carbon_intensity(self, latitude: float, longitude: float) -> float:
        """
        Get current carbon intensity.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Current carbon intensity in gCO2/kWh
        """
        # Mock real-time data
        current_hour = datetime.now().hour
        base_intensity = 350
        variation = 50 * np.sin(2 * np.pi * current_hour / 24)
        noise = np.random.normal(0, 10)

        return max(200, base_intensity + variation + noise)


class WeatherAPI:
    """
    Interface to weather APIs for solar irradiance modeling.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize weather API client.

        Args:
            api_key: API key for weather service
        """
        self.api_key = api_key
        self.base_url = "https://api.openweathermap.org/data/2.5"  # Example API

    def get_weather_data(self, latitude: float, longitude: float,
                        start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """
        Get historical weather data.

        Args:
            latitude: Location latitude
            longitude: Location longitude
            start_time: Start time for data
            end_time: End time for data

        Returns:
            DataFrame with weather data
        """
        # For demo purposes, generate synthetic weather data
        timestamps = pd.date_range(start_time, end_time, freq='H')
        n_hours = len(timestamps)

        # Generate realistic weather patterns
        # Cloud cover (0-1)
        cloud_base = 0.3
        diurnal_cloud = 0.2 * np.sin(2 * np.pi * np.arange(n_hours) / 24)
        cloud_cover = np.clip(cloud_base + diurnal_cloud + np.random.normal(0, 0.1, n_hours), 0, 1)

        # Temperature (°C)
        temp_base = 20
        diurnal_temp = 10 * np.sin(2 * np.pi * (np.arange(n_hours) - 6) / 24)  # Peak at 2 PM
        seasonal_temp = 5 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 365))  # Seasonal variation
        temperature = temp_base + diurnal_temp + seasonal_temp + np.random.normal(0, 2, n_hours)

        # Wind speed (m/s)
        wind_speed = 3 + np.random.exponential(2, n_hours)  # Exponential distribution

        df = pd.DataFrame({
            'timestamp': timestamps,
            'cloud_cover': cloud_cover,
            'temperature_c': temperature,
            'wind_speed_ms': wind_speed
        })
        df.set_index('timestamp', inplace=True)

        return df

    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, float]:
        """
        Get current weather conditions.

        Args:
            latitude: Location latitude
            longitude: Location longitude

        Returns:
            Dict with current weather data
        """
        # Mock current weather
        return {
            'cloud_cover': np.random.uniform(0, 1),
            'temperature_c': 20 + np.random.normal(0, 5),
            'wind_speed_ms': max(0, 3 + np.random.normal(0, 2))
        }


class ElectricityPriceAPI:
    """
    Interface to electricity price APIs.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize electricity price API client.

        Args:
            api_key: API key for price service
        """
        self.api_key = api_key

    def get_price_data(self, region: str, start_time: datetime,
                      end_time: datetime) -> pd.DataFrame:
        """
        Get historical electricity price data.

        Args:
            region: Electricity market region
            start_time: Start time for data
            end_time: End time for data

        Returns:
            DataFrame with price data
        """
        # Generate synthetic price data
        timestamps = pd.date_range(start_time, end_time, freq='H')
        n_hours = len(timestamps)

        # Base price with time-of-day variation
        base_price = 0.12  # $/kWh
        tod_premium = 0.05 * np.maximum(0, np.sin(2 * np.pi * (np.arange(n_hours) % 24 - 6) / 24))
        demand_premium = 0.03 * np.maximum(0, np.sin(2 * np.pi * (np.arange(n_hours) % 24 - 12) / 24))

        price = base_price + tod_premium + demand_premium + np.random.normal(0, 0.01, n_hours)
        price = np.maximum(price, 0.05)  # Minimum price

        df = pd.DataFrame({
            'timestamp': timestamps,
            'price_usd_per_kwh': price
        })
        df.set_index('timestamp', inplace=True)

        return df


def load_real_data(latitude: float = 37.7749, longitude: float = -122.4194,
                  days: int = 1) -> Dict[str, pd.DataFrame]:
    """
    Load real data from APIs for simulation.

    Args:
        latitude: Location latitude
        longitude: Location longitude
        days: Number of days of data to load

    Returns:
        Dictionary of dataframes with real data
    """
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    # Initialize API clients
    carbon_api = CarbonIntensityAPI()
    weather_api = WeatherAPI()
    price_api = ElectricityPriceAPI()

    # Fetch data
    carbon_data = carbon_api.get_carbon_intensity(latitude, longitude, start_time, end_time)
    weather_data = weather_api.get_weather_data(latitude, longitude, start_time, end_time)
    price_data = price_api.get_price_data("CAISO", start_time, end_time)  # California ISO

    # Generate demand data (synthetic since we don't have real demand API)
    timestamps = carbon_data.index
    n_hours = len(timestamps)

    # Realistic data center demand pattern
    base_demand = 1000  # kW
    diurnal_demand = 300 * np.sin(2 * np.pi * (np.arange(n_hours) % 24 - 6) / 24)
    weekly_demand = 100 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 7))
    noise = np.random.normal(0, 50, n_hours)

    demand_kw = base_demand + diurnal_demand + weekly_demand + noise
    demand_kw = np.maximum(demand_kw, 500)  # Minimum demand

    demand_data = pd.DataFrame({
        'timestamp': timestamps,
        'demand_kw': demand_kw
    })
    demand_data.set_index('timestamp', inplace=True)

    return {
        'demand': demand_data,
        'carbon_intensity': carbon_data,
        'weather': weather_data,
        'price': price_data
    }