import unittest

import pandas as pd

from ecodispatch.models import Battery, SolarPV, DemandProfile
from ecodispatch.simulation import EcoDispatch


class TestBattery(unittest.TestCase):
    def setUp(self):
        self.battery = Battery(capacity_kwh=100, max_power_kw=20, efficiency=0.95)

    def test_charge(self):
        energy_charged = self.battery.charge(10, 1.0)
        self.assertAlmostEqual(energy_charged, 10, places=2)
        self.assertAlmostEqual(self.battery.soc, 0.6, places=2)

    def test_discharge(self):
        energy_discharged = self.battery.discharge(10, 1.0)
        self.assertAlmostEqual(energy_discharged, 10, places=2)
        self.assertAlmostEqual(self.battery.soc, 0.4, places=2)


class TestSolarPV(unittest.TestCase):
    def setUp(self):
        self.solar = SolarPV(capacity_kw=100, latitude=37.7749, longitude=-122.4194)

    def test_generation_is_non_negative(self):
        power = self.solar.generate(pd.Timestamp("2023-06-21 12:00:00"))
        self.assertGreaterEqual(power, 0)


class TestDemandProfile(unittest.TestCase):
    def setUp(self):
        self.demand = DemandProfile(base_load_kw=1000)

    def test_peak_demand(self):
        peak_demand = self.demand.get_demand(12)
        self.assertEqual(peak_demand["total"], 1500)

    def test_off_peak_demand(self):
        off_peak_demand = self.demand.get_demand(2)
        self.assertEqual(off_peak_demand["total"], 1000)


class TestSimulation(unittest.TestCase):
    def test_simulation_uses_input_demand_and_preserves_shifted_energy(self):
        index = pd.date_range("2023-01-01", periods=4, freq="h")
        demand = pd.DataFrame(
            {
                "demand_kw": [100.0, 200.0, 300.0, 400.0],
                "flexible_fraction": [0.25, 0.25, 0.25, 0.25],
            },
            index=index,
        )
        carbon = pd.DataFrame(
            {"carbon_gco2_per_kwh": [500.0, 250.0, 200.0, 450.0]},
            index=index,
        )
        price = pd.DataFrame(
            {"price_usd_per_kwh": [0.10, 0.10, 0.10, 0.10]},
            index=index,
        )
        solar = pd.DataFrame({"solar_kw": [0.0, 50.0, 50.0, 0.0]}, index=index)
        data = {
            "demand": demand,
            "carbon_intensity": carbon,
            "price": price,
            "solar_generation": solar,
            "config": {
                "battery_capacity_kwh": 100.0,
                "battery_max_power_kw": 50.0,
                "solar_capacity_kw": 50.0,
                "flexible_load_fraction": 0.25,
            },
        }

        results = EcoDispatch.simulate(data, strategy="carbon_min")

        dispatched_energy = results["dispatch"].sum(axis=1)
        expected_served_load = demand["demand_kw"] + results["workload_shifts"]["shifted_load_kw"]
        self.assertTrue(((dispatched_energy - expected_served_load).abs() <= 1e-6).all())
        self.assertAlmostEqual(
            float(results["workload_shifts"]["shifted_load_kw"].sum()),
            0.0,
            places=6,
        )
        self.assertTrue(results["battery_soc"]["soc"].between(0, 1).all())
        self.assertEqual(len(results["solar_available"]), len(index))


if __name__ == "__main__":
    unittest.main()
