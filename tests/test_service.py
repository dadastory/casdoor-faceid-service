import unittest

from casdoor_faceid_service.config import Settings
from casdoor_faceid_service.service import FaceAnalysisService


class FakeEngine:
    def __init__(self, similarities, liveness=None):
        self.similarities = list(similarities)
        self.liveness = list(liveness or [])
        self.compared = []

    def compare(self, reference_image, probe_image):
        self.compared.append((reference_image, probe_image))
        return self.similarities.pop(0)

    def anti_spoof(self, image):
        return self.liveness.pop(0)


class FaceAnalysisServiceTest(unittest.TestCase):
    def test_compare_returns_best_match_across_registered_and_probe_images(self):
        settings = Settings(enable_liveness=False, similarity_threshold=0.6)
        engine = FakeEngine([0.41, 0.63, 0.59, 0.88])
        service = FaceAnalysisService(engine, settings)

        result = service.compare(["registered-a", "registered-b"], ["probe-a", "probe-b"])

        self.assertTrue(result["matched"])
        self.assertEqual(result["score"], 0.88)
        self.assertEqual(result["threshold"], 0.6)
        self.assertEqual(result["referenceIndex"], 1)
        self.assertEqual(result["probeIndex"], 1)

    def test_compare_rejects_when_best_score_is_below_threshold(self):
        settings = Settings(enable_liveness=False, similarity_threshold=0.7)
        engine = FakeEngine([0.69])
        service = FaceAnalysisService(engine, settings)

        result = service.compare(["registered"], ["probe"])

        self.assertFalse(result["matched"])
        self.assertEqual(result["score"], 0.69)

    def test_compare_runs_liveness_on_probe_images_when_enabled(self):
        settings = Settings(enable_liveness=True, liveness_threshold=0.7, similarity_threshold=0.6)
        engine = FakeEngine([0.91], [{"isReal": True, "confidence": 0.82}])
        service = FaceAnalysisService(engine, settings)

        result = service.compare(["registered"], ["probe"])

        self.assertTrue(result["matched"])
        self.assertEqual(result["liveness"], {"isReal": True, "confidence": 0.82})

    def test_compare_rejects_when_liveness_fails(self):
        settings = Settings(enable_liveness=True, liveness_threshold=0.7, similarity_threshold=0.6)
        engine = FakeEngine([0.99], [{"isReal": False, "confidence": 0.95}])
        service = FaceAnalysisService(engine, settings)

        result = service.compare(["registered"], ["probe"])

        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "liveness_failed")
        self.assertEqual(result["score"], 0.99)

    def test_compare_uses_best_live_probe_when_some_probe_images_fail_liveness(self):
        settings = Settings(enable_liveness=True, liveness_threshold=0.7, similarity_threshold=0.6)
        engine = FakeEngine(
            [0.99, 0.78],
            [
                {"isReal": False, "confidence": 0.95},
                {"isReal": True, "confidence": 0.82},
            ],
        )
        service = FaceAnalysisService(engine, settings)

        result = service.compare(["registered"], ["fake-probe", "live-probe"])

        self.assertTrue(result["matched"])
        self.assertEqual(result["score"], 0.78)
        self.assertEqual(result["probeIndex"], 1)
        self.assertEqual(result["liveness"], {"isReal": True, "confidence": 0.82})

    def test_compare_requires_at_least_one_image_on_each_side(self):
        service = FaceAnalysisService(FakeEngine([]), Settings())

        with self.assertRaises(ValueError):
            service.compare([], ["probe"])

        with self.assertRaises(ValueError):
            service.compare(["registered"], [])


if __name__ == "__main__":
    unittest.main()
