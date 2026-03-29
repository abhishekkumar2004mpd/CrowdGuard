import unittest

from crowdguard.risk_engine import estimate_area_sq_meters, estimate_safe_capacity, evaluate_risk


class RiskEngineTests(unittest.TestCase):
    def test_area_estimation_uses_dimensions(self):
        self.assertEqual(estimate_area_sq_meters(10, 5, 20), 50)

    def test_safe_capacity_has_minimum(self):
        self.assertEqual(estimate_safe_capacity(0, 2.5), 0)
        self.assertEqual(estimate_safe_capacity(10, 2.5), 25)

    def test_warning_and_critical_states(self):
        warning = evaluate_risk(21, 10, 2.5, 0.8, 1.0)
        critical = evaluate_risk(25, 10, 2.5, 0.8, 1.0)
        self.assertEqual(warning.status, "WARNING")
        self.assertEqual(critical.status, "CRITICAL")


if __name__ == "__main__":
    unittest.main()
