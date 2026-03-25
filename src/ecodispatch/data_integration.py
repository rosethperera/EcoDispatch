"""
Data integration module for real and synthetic input data.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import numpy as np
import pandas as pd
import requests


def _load_local_env() -> None:
    """Load simple KEY=VALUE pairs from `.env.local` or `.env` if present."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    for filename in (".env.local", ".env"):
        env_path = os.path.join(project_root, filename)
        if not os.path.exists(env_path):
            continue

        with open(env_path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
        break


_load_local_env()


def _utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def _coerce_utc(dt: datetime) -> datetime:
    """Normalize a datetime into timezone-aware UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _hourly_index(start_time: datetime, end_time: datetime) -> pd.DatetimeIndex:
    """Create an hourly UTC index covering the requested range."""
    start = _coerce_utc(start_time).replace(minute=0, second=0, microsecond=0)
    end = _coerce_utc(end_time).replace(minute=0, second=0, microsecond=0)

    if end < start:
        end = start

    return pd.date_range(start=start, end=end, freq="h", tz="UTC")


def _isoformat_z(dt: datetime) -> str:
    """Format a datetime as an ISO-8601 UTC string."""
    return _coerce_utc(dt).isoformat().replace("+00:00", "Z")


def _series_from_emaps_payload(payload: Dict, value_keys: list[str]) -> pd.DataFrame:
    """
    Parse a range-like Electricity Maps response into a DataFrame.

    The API may return lists under keys like `history` or `data`.
    """
    records = None
    for key in ("history", "data"):
        if isinstance(payload.get(key), list):
            records = payload[key]
            break

    if records is None and isinstance(payload, list):
        records = payload

    if not records:
        raise ValueError("No range records returned by provider")

    rows = []
    for record in records:
        timestamp = record.get("datetime")
        value = None
        for key in value_keys:
            if key in record and record[key] is not None:
                value = record[key]
                break
        if timestamp is not None and value is not None:
            rows.append({"timestamp": timestamp, "value": value})

    if not rows:
        raise ValueError("Provider response did not include usable timestamp/value pairs")

    frame = pd.DataFrame(rows)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame = frame.set_index("timestamp").sort_index()
    return frame


class CarbonIntensityAPI:
    """
    Interface to carbon intensity data providers.

    Supported providers:
    - `electricitymaps`: real historical/current carbon intensity with API token
    - `synthetic`: realistic fallback profile for demo mode
    """

    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELECTRICITYMAPS_API_TOKEN")
        configured_provider = provider or os.getenv("ECODISPATCH_CARBON_PROVIDER")
        if configured_provider:
            self.provider = configured_provider.lower()
        else:
            self.provider = "electricitymaps" if self.api_key else "synthetic"
        self.base_url = "https://api.electricitymaps.com/v3"
        self.session = requests.Session()

    def get_carbon_intensity(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """Get historical carbon intensity data."""
        if self.provider == "electricitymaps" and self.api_key:
            try:
                return self._get_electricitymaps_carbon(latitude, longitude, start_time, end_time)
            except Exception:
                pass

        return self._get_synthetic_carbon(start_time, end_time)

    def get_realtime_carbon_intensity(self, latitude: float, longitude: float) -> float:
        """Get current carbon intensity."""
        if self.provider == "electricitymaps" and self.api_key:
            try:
                headers = {"auth-token": self.api_key}
                response = self.session.get(
                    f"{self.base_url}/carbon-intensity/latest",
                    headers=headers,
                    params={"lat": latitude, "lon": longitude},
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                for key in ("carbonIntensity", "carbonIntensityGco2eqPerKwh", "value"):
                    if key in payload and payload[key] is not None:
                        return float(payload[key])
            except Exception:
                pass

        current_hour = datetime.now().hour
        base_intensity = 350
        variation = 50 * np.sin(2 * np.pi * current_hour / 24)
        noise = np.random.normal(0, 10)
        return max(200, base_intensity + variation + noise)

    def _get_electricitymaps_carbon(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """Fetch historical carbon intensity from Electricity Maps."""
        headers = {"auth-token": self.api_key}
        response = self.session.get(
            f"{self.base_url}/carbon-intensity/past-range",
            headers=headers,
            params={
                "lat": latitude,
                "lon": longitude,
                "start": _isoformat_z(start_time),
                "end": _isoformat_z(end_time + timedelta(hours=1)),
                "temporalGranularity": "hourly",
            },
            timeout=30,
        )
        response.raise_for_status()

        frame = _series_from_emaps_payload(
            response.json(),
            ["carbonIntensity", "carbonIntensityGco2eqPerKwh", "value"],
        )
        frame = frame.rename(columns={"value": "carbon_gco2_per_kwh"})
        return frame

    def _get_synthetic_carbon(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Generate a realistic fallback carbon intensity profile."""
        timestamps = _hourly_index(start_time, end_time)
        n_hours = len(timestamps)

        base_intensity = 350
        diurnal_variation = 50 * np.sin(2 * np.pi * np.arange(n_hours) / 24)
        weekly_variation = 30 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 7))
        noise = np.random.normal(0, 20, n_hours)

        carbon_intensity = base_intensity + diurnal_variation + weekly_variation + noise
        carbon_intensity = np.clip(carbon_intensity, 200, 600)

        df = pd.DataFrame(
            {"carbon_gco2_per_kwh": carbon_intensity},
            index=timestamps,
        )
        df.index.name = "timestamp"
        return df


class WeatherAPI:
    """
    Interface to weather APIs for solar irradiance modeling.

    Uses Open-Meteo by default because it supports real data without an API key.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.archive_url = "https://archive-api.open-meteo.com/v1/archive"
        self.forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.session = requests.Session()

    def get_weather_data(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """Get historical weather data."""
        try:
            return self._get_open_meteo_weather(latitude, longitude, start_time, end_time)
        except Exception:
            return self._get_synthetic_weather(start_time, end_time)

    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, float]:
        """Get current weather conditions."""
        try:
            response = self.session.get(
                self.forecast_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current": "temperature_2m,cloud_cover,wind_speed_10m",
                    "wind_speed_unit": "ms",
                    "timezone": "UTC",
                },
                timeout=20,
            )
            response.raise_for_status()
            current = response.json().get("current", {})
            return {
                "cloud_cover": float(current.get("cloud_cover", 0.0)) / 100.0,
                "temperature_c": float(current.get("temperature_2m", 20.0)),
                "wind_speed_ms": float(current.get("wind_speed_10m", 3.0)),
            }
        except Exception:
            return {
                "cloud_cover": np.random.uniform(0, 1),
                "temperature_c": 20 + np.random.normal(0, 5),
                "wind_speed_ms": max(0, 3 + np.random.normal(0, 2)),
            }

    def _get_open_meteo_weather(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """Fetch historical weather from Open-Meteo."""
        start_utc = _coerce_utc(start_time)
        end_utc = _coerce_utc(end_time)

        response = self.session.get(
            self.archive_url,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_utc.date().isoformat(),
                "end_date": end_utc.date().isoformat(),
                "hourly": "temperature_2m,cloud_cover,wind_speed_10m",
                "wind_speed_unit": "ms",
                "timezone": "UTC",
            },
            timeout=30,
        )
        response.raise_for_status()
        hourly = response.json().get("hourly", {})
        if not hourly:
            raise ValueError("Open-Meteo returned no hourly data")

        frame = pd.DataFrame(
            {
                "timestamp": pd.to_datetime(hourly["time"], utc=True),
                "cloud_cover": pd.Series(hourly["cloud_cover"], dtype="float64") / 100.0,
                "temperature_c": pd.Series(hourly["temperature_2m"], dtype="float64"),
                "wind_speed_ms": pd.Series(hourly["wind_speed_10m"], dtype="float64"),
            }
        ).set_index("timestamp")

        frame = frame.sort_index()
        requested_index = _hourly_index(start_utc, end_utc)
        frame = frame.reindex(requested_index).interpolate(limit_direction="both")
        frame.index.name = "timestamp"
        return frame

    def _get_synthetic_weather(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Generate realistic fallback weather patterns."""
        timestamps = _hourly_index(start_time, end_time)
        n_hours = len(timestamps)

        cloud_base = 0.3
        diurnal_cloud = 0.2 * np.sin(2 * np.pi * np.arange(n_hours) / 24)
        cloud_cover = np.clip(cloud_base + diurnal_cloud + np.random.normal(0, 0.1, n_hours), 0, 1)

        temp_base = 20
        diurnal_temp = 10 * np.sin(2 * np.pi * (np.arange(n_hours) - 6) / 24)
        seasonal_temp = 5 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 365))
        temperature = temp_base + diurnal_temp + seasonal_temp + np.random.normal(0, 2, n_hours)

        wind_speed = 3 + np.random.exponential(2, n_hours)

        df = pd.DataFrame(
            {
                "cloud_cover": cloud_cover,
                "temperature_c": temperature,
                "wind_speed_ms": wind_speed,
            },
            index=timestamps,
        )
        df.index.name = "timestamp"
        return df


class ElectricityPriceAPI:
    """
    Interface to electricity price providers.

    Supported providers:
    - `electricitymaps`: day-ahead market prices with API token
    - `synthetic`: fallback hourly price curve
    """

    def __init__(self, api_key: Optional[str] = None, provider: Optional[str] = None):
        self.api_key = api_key or os.getenv("ELECTRICITYMAPS_API_TOKEN")
        configured_provider = provider or os.getenv("ECODISPATCH_PRICE_PROVIDER")
        if configured_provider:
            self.provider = configured_provider.lower()
        else:
            self.provider = "electricitymaps" if self.api_key else "synthetic"
        self.base_url = "https://api.electricitymaps.com/v3"
        self.session = requests.Session()

    def get_price_data(
        self,
        region: str,
        start_time: datetime,
        end_time: datetime,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> pd.DataFrame:
        """Get historical electricity price data."""
        if self.provider == "electricitymaps" and self.api_key and latitude is not None and longitude is not None:
            try:
                return self._get_electricitymaps_price(latitude, longitude, start_time, end_time)
            except Exception:
                pass

        return self._get_synthetic_price(start_time, end_time)

    def _get_electricitymaps_price(
        self,
        latitude: float,
        longitude: float,
        start_time: datetime,
        end_time: datetime,
    ) -> pd.DataFrame:
        """Fetch day-ahead prices from Electricity Maps and convert to USD/kWh."""
        headers = {"auth-token": self.api_key}
        response = self.session.get(
            f"{self.base_url}/price-day-ahead/past-range",
            headers=headers,
            params={
                "lat": latitude,
                "lon": longitude,
                "start": _isoformat_z(start_time),
                "end": _isoformat_z(end_time + timedelta(hours=1)),
                "temporalGranularity": "hourly",
            },
            timeout=30,
        )
        response.raise_for_status()

        frame = _series_from_emaps_payload(
            response.json(),
            ["price", "priceEur", "priceUsd", "priceDayAhead", "value"],
        )

        # Electricity Maps prices are documented in local currency per MWh.
        frame["price_usd_per_kwh"] = frame["value"].astype(float) / 1000.0
        return frame[["price_usd_per_kwh"]]

    def _get_synthetic_price(self, start_time: datetime, end_time: datetime) -> pd.DataFrame:
        """Generate a realistic fallback price profile."""
        timestamps = _hourly_index(start_time, end_time)
        n_hours = len(timestamps)

        base_price = 0.12
        tod_premium = 0.05 * np.maximum(0, np.sin(2 * np.pi * (np.arange(n_hours) % 24 - 6) / 24))
        demand_premium = 0.03 * np.maximum(0, np.sin(2 * np.pi * (np.arange(n_hours) % 24 - 12) / 24))

        price = base_price + tod_premium + demand_premium + np.random.normal(0, 0.01, n_hours)
        price = np.maximum(price, 0.05)

        df = pd.DataFrame({"price_usd_per_kwh": price}, index=timestamps)
        df.index.name = "timestamp"
        return df


def lookup_location_name(latitude: float, longitude: float) -> str:
    """
    Reverse geocode coordinates into a readable place name.

    Uses OpenStreetMap Nominatim and falls back to raw coordinates if lookup fails.
    """
    try:
        response = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={
                "lat": latitude,
                "lon": longitude,
                "format": "jsonv2",
                "zoom": 10,
                "addressdetails": 1,
            },
            headers={
                "User-Agent": "EcoDispatch/0.1.0 (educational prototype reverse geocoding)"
            },
            timeout=20,
        )
        response.raise_for_status()
        payload = response.json()
        address = payload.get("address", {})

        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("municipality")
            or address.get("county")
        )
        state = address.get("state") or address.get("region")
        country = address.get("country")

        parts = [part for part in (city, state, country) if part]
        if parts:
            return ", ".join(parts)

        if payload.get("display_name"):
            return str(payload["display_name"]).split(",")[0]
    except Exception:
        pass

    return f"{latitude:.4f}, {longitude:.4f}"


def load_real_data(
    latitude: float = 37.7749,
    longitude: float = -122.4194,
    days: int = 1,
) -> Dict[str, pd.DataFrame]:
    """
    Load data for simulation.

    Real weather is fetched from Open-Meteo when available.
    Carbon intensity and electricity price can use live Electricity Maps data
    when `ELECTRICITYMAPS_API_TOKEN` is configured and the corresponding
    provider environment variables are set. Otherwise the function falls back
    to synthetic benchmark data.
    """
    end_time = _utc_now()
    start_time = end_time - timedelta(days=days)

    carbon_api = CarbonIntensityAPI()
    weather_api = WeatherAPI()
    price_api = ElectricityPriceAPI()

    carbon_data = carbon_api.get_carbon_intensity(latitude, longitude, start_time, end_time)
    weather_data = weather_api.get_weather_data(latitude, longitude, start_time, end_time)
    price_data = price_api.get_price_data("CAISO", start_time, end_time, latitude, longitude)

    timestamps = carbon_data.index
    n_hours = len(timestamps)

    base_demand = 1000
    diurnal_demand = 300 * np.sin(2 * np.pi * (np.arange(n_hours) % 24 - 6) / 24)
    weekly_demand = 100 * np.sin(2 * np.pi * np.arange(n_hours) / (24 * 7))
    noise = np.random.normal(0, 50, n_hours)

    demand_kw = base_demand + diurnal_demand + weekly_demand + noise
    demand_kw = np.maximum(demand_kw, 500)

    demand_data = pd.DataFrame({"demand_kw": demand_kw}, index=timestamps)
    demand_data.index.name = "timestamp"

    return {
        "demand": demand_data,
        "carbon_intensity": carbon_data,
        "weather": weather_data,
        "price": price_data,
    }
