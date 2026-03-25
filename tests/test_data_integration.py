import unittest
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ecodispatch.data_integration import CarbonIntensityAPI, WeatherAPI


class TestWeatherAPI(unittest.TestCase):
    @patch("ecodispatch.data_integration.requests.Session.get")
    def test_open_meteo_weather_is_parsed_into_expected_columns(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "hourly": {
                "time": [
                    "2026-03-20T00:00",
                    "2026-03-20T01:00",
                    "2026-03-20T02:00",
                ],
                "cloud_cover": [0, 50, 100],
                "temperature_2m": [10.0, 11.0, 12.0],
                "wind_speed_10m": [1.0, 2.0, 3.0],
            }
        }
        mock_get.return_value = mock_response

        api = WeatherAPI()
        start = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 20, 2, 0, tzinfo=timezone.utc)

        data = api.get_weather_data(37.7749, -122.4194, start, end)

        self.assertListEqual(
            list(data.columns),
            ["cloud_cover", "temperature_c", "wind_speed_ms"],
        )
        self.assertEqual(len(data), 3)
        self.assertAlmostEqual(float(data.iloc[1]["cloud_cover"]), 0.5)
        self.assertAlmostEqual(float(data.iloc[2]["temperature_c"]), 12.0)
        self.assertAlmostEqual(float(data.iloc[0]["wind_speed_ms"]), 1.0)


class TestCarbonIntensityAPI(unittest.TestCase):
    @patch("ecodispatch.data_integration.requests.Session.get")
    def test_electricitymaps_carbon_history_is_parsed(self, mock_get):
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "history": [
                {"datetime": "2026-03-20T00:00:00Z", "carbonIntensity": 300},
                {"datetime": "2026-03-20T01:00:00Z", "carbonIntensity": 320},
            ]
        }
        mock_get.return_value = mock_response

        api = CarbonIntensityAPI(api_key="test-token", provider="electricitymaps")
        start = datetime(2026, 3, 20, 0, 0, tzinfo=timezone.utc)
        end = datetime(2026, 3, 20, 1, 0, tzinfo=timezone.utc)

        data = api.get_carbon_intensity(37.7749, -122.4194, start, end)

        self.assertEqual(list(data.columns), ["carbon_gco2_per_kwh"])
        self.assertEqual(len(data), 2)
        self.assertAlmostEqual(float(data.iloc[0]["carbon_gco2_per_kwh"]), 300.0)

    @patch("ecodispatch.data_integration.requests.Session.get", side_effect=Exception("network error"))
    def test_carbon_falls_back_to_synthetic_when_provider_fails(self, mock_get):
        api = CarbonIntensityAPI(api_key="test-token", provider="electricitymaps")
        start = datetime.now(timezone.utc) - timedelta(hours=2)
        end = datetime.now(timezone.utc)

        data = api.get_carbon_intensity(37.7749, -122.4194, start, end)

        self.assertIn("carbon_gco2_per_kwh", data.columns)
        self.assertGreaterEqual(len(data), 1)


if __name__ == "__main__":
    unittest.main()
