import os
import unittest
from unittest.mock import patch

from casdoor_faceid_service.config import Settings


class SettingsTest(unittest.TestCase):
    def test_defaults_enable_liveness_for_local_cpu_service(self):
        settings = Settings.from_env({})

        self.assertEqual(settings.device, "cpu")
        self.assertEqual(settings.host, "0.0.0.0")
        self.assertEqual(settings.port, 8100)
        self.assertEqual(settings.api_key, "")
        self.assertTrue(settings.enable_liveness)
        self.assertEqual(settings.providers, ["CPUExecutionProvider"])

    def test_gpu_device_selects_cuda_with_cpu_fallback(self):
        settings = Settings.from_env({"FACEID_DEVICE": "gpu"})

        self.assertEqual(settings.device, "gpu")
        self.assertEqual(settings.providers, ["CUDAExecutionProvider", "CPUExecutionProvider"])

    def test_boolean_and_threshold_values_are_read_from_env(self):
        env = {
            "FACEID_ENABLE_LIVENESS": "true",
            "FACEID_SIMILARITY_THRESHOLD": "0.72",
            "FACEID_LIVENESS_THRESHOLD": "0.81",
            "FACEID_API_KEY": "secret",
        }

        settings = Settings.from_env(env)

        self.assertEqual(settings.api_key, "secret")
        self.assertTrue(settings.enable_liveness)
        self.assertEqual(settings.similarity_threshold, 0.72)
        self.assertEqual(settings.liveness_threshold, 0.81)


if __name__ == "__main__":
    unittest.main()
