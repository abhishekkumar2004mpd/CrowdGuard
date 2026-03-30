import unittest

from crowdguard.detector import CrowdDetector
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

    def test_pose_threshold_requires_shoulders_and_feature_points(self):
        detector = CrowdDetector.__new__(CrowdDetector)
        detector.min_keypoints = 5
        detector.min_keypoint_confidence = 0.35
        detector.partial_min_keypoints = 3
        detector.partial_confidence_threshold = 0.55
        detector.min_bbox_height = 40
        detector.box_only_confidence_threshold = 0.72

        confidences = [0.0] * 17
        for index in (1, 2, 5, 6, 7):
            confidences[index] = 0.9

        self.assertTrue(detector._passes_pose_threshold([0, 0, 80, 120], 0.9, [(0, 0)] * 17, confidences))
        confidences[5] = 0.1
        confidences[6] = 0.1
        self.assertFalse(detector._passes_pose_threshold([0, 0, 80, 120], 0.5, [(0, 0)] * 17, confidences))

    def test_pose_threshold_allows_partial_pose_for_occluded_people(self):
        detector = CrowdDetector.__new__(CrowdDetector)
        detector.min_keypoints = 5
        detector.min_keypoint_confidence = 0.35
        detector.partial_min_keypoints = 3
        detector.partial_confidence_threshold = 0.55
        detector.min_bbox_height = 32
        detector.box_only_confidence_threshold = 0.72

        confidences = [0.0] * 17
        for index in (5, 6, 7):
            confidences[index] = 0.8

        self.assertTrue(detector._passes_pose_threshold([0, 0, 60, 90], 0.7, [(0, 0)] * 17, confidences))


if __name__ == "__main__":
    unittest.main()
