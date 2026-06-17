import unittest

from fastapi import HTTPException

from casdoor_faceid_service.api import CompareRequest, _images_for_request, verify_api_key
from casdoor_faceid_service.config import Settings


class ApiAuthTest(unittest.TestCase):
    def test_verify_api_key_allows_requests_when_api_key_is_not_configured(self):
        verify_api_key(None, Settings(api_key=""))

    def test_verify_api_key_accepts_matching_bearer_token(self):
        verify_api_key("Bearer secret", Settings(api_key="secret"))

    def test_verify_api_key_rejects_missing_bearer_token(self):
        with self.assertRaises(HTTPException) as context:
            verify_api_key(None, Settings(api_key="secret"))

        self.assertEqual(context.exception.status_code, 401)

    def test_verify_api_key_rejects_invalid_bearer_token(self):
        with self.assertRaises(HTTPException) as context:
            verify_api_key("Bearer wrong", Settings(api_key="secret"))

        self.assertEqual(context.exception.status_code, 401)

    def test_images_for_request_accepts_casdoor_image_fields(self):
        request = CompareRequest(imageA="login-image", imageB="registered-image")

        reference_images, probe_images = _images_for_request(request)

        self.assertEqual(reference_images, ["registered-image"])
        self.assertEqual(probe_images, ["login-image"])

    def test_images_for_request_keeps_batch_images_before_casdoor_images(self):
        request = CompareRequest(
            imageA="login-image",
            imageB="registered-image",
            referenceImages=["registered-batch"],
            probeImages=["probe-batch"],
        )

        reference_images, probe_images = _images_for_request(request)

        self.assertEqual(reference_images, ["registered-batch", "registered-image"])
        self.assertEqual(probe_images, ["probe-batch", "login-image"])


if __name__ == "__main__":
    unittest.main()
