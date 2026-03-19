import unittest
from ecodispatch.models import Battery, SolarPV, DemandProfile


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
        self.solar = SolarPV(capacity_kw=100)

    def test_generation(self):
        power = self.solar.generate(800)  # 800 W/m²
        expected = 100 * (800 / 1000) * 0.2  # Simplified calculation
        self.assertAlmostEqual(power, expected, places=2)


class TestDemandProfile(unittest.TestCase):
    def setUp(self):
        self.demand = DemandProfile(base_load_kw=1000)

    def test_peak_demand(self):
        peak_demand = self.demand.get_demand(12)  # Noon
        self.assertEqual(peak_demand, 1500)

    def test_off_peak_demand(self):
        off_peak_demand = self.demand.get_demand(2)  # 2 AM
        self.assertEqual(off_peak_demand, 1000)


if __name__ == '__main__':
    unittest.main()