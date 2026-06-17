from __future__ import annotations

import os
from collections import Counter
from typing import Any

from .config import Settings
from .image import decode_base64_image
from .preload import apply_model_url_rewrites


class UniFaceEngine:
    def __init__(self, settings: Settings):
        self.settings = settings
        apply_model_url_rewrites(
            os.environ.get("UNIFACE_MODEL_URL_REWRITE"),
            os.environ.get("UNIFACE_GITHUB_PROXY"),
        )
        self.detector = self._build_detector()
        self.recognizer = self._build_recognizer()
        self.spoofer = None
        self.parser = None

    def detect(self, image_value: str) -> list[dict[str, Any]]:
        image = decode_base64_image(image_value, self.settings.max_image_bytes)
        faces = self.detector.detect(image)
        return [self._face_to_dict(face) for face in faces]

    def anti_spoof(self, image_value: str) -> dict[str, Any]:
        image = decode_base64_image(image_value, self.settings.max_image_bytes)
        face = self._primary_face(image)
        spoofer = self._get_spoofer()
        result = spoofer.predict(image, face.bbox)
        return {
            "isReal": bool(result.is_real),
            "confidence": round(float(result.confidence), 6),
        }

    def parse(self, image_value: str) -> dict[str, Any]:
        image = decode_base64_image(image_value, self.settings.max_image_bytes)
        face = self._primary_face(image)
        parser = self._get_parser()

        x1, y1, x2, y2 = [int(v) for v in face.bbox]
        face_crop = image[max(y1, 0):max(y2, 0), max(x1, 0):max(x2, 0)]
        if face_crop.size == 0:
            raise ValueError("face crop is empty")

        mask = parser.parse(face_crop)
        counts = Counter(int(value) for value in mask.flatten())
        return {
            "bbox": [float(v) for v in face.bbox],
            "maskSize": [int(mask.shape[0]), int(mask.shape[1])],
            "classPixelCounts": {str(key): value for key, value in sorted(counts.items())},
        }

    def compare(self, reference_image_value: str, probe_image_value: str) -> float:
        reference_image = decode_base64_image(reference_image_value, self.settings.max_image_bytes)
        probe_image = decode_base64_image(probe_image_value, self.settings.max_image_bytes)
        reference_face = self._primary_face(reference_image)
        probe_face = self._primary_face(probe_image)

        reference_embedding = self.recognizer.get_normalized_embedding(reference_image, reference_face.landmarks)
        probe_embedding = self.recognizer.get_normalized_embedding(probe_image, probe_face.landmarks)

        from uniface.face_utils import compute_similarity

        return float(compute_similarity(reference_embedding, probe_embedding))

    def _primary_face(self, image):
        faces = self.detector.detect(image)
        if len(faces) == 0:
            raise ValueError("no face detected")
        if len(faces) > 1:
            raise ValueError("multiple faces detected")
        return faces[0]

    def _build_detector(self):
        if self.settings.detector == "scrfd":
            from uniface.detection import SCRFD

            return SCRFD(providers=self.settings.providers)
        if self.settings.detector == "yolov5":
            from uniface.detection import YOLOv5Face

            return YOLOv5Face(providers=self.settings.providers)
        if self.settings.detector == "yolov8":
            from uniface.detection import YOLOv8Face

            return YOLOv8Face(providers=self.settings.providers)
        from uniface.detection import RetinaFace

        return RetinaFace(providers=self.settings.providers)

    def _build_recognizer(self):
        if self.settings.recognizer == "adaface":
            from uniface.recognition import AdaFace

            return AdaFace(providers=self.settings.providers)
        if self.settings.recognizer == "edgeface":
            from uniface.recognition import EdgeFace

            return EdgeFace(providers=self.settings.providers)
        if self.settings.recognizer == "mobileface":
            from uniface.recognition import MobileFace

            return MobileFace(providers=self.settings.providers)
        if self.settings.recognizer == "sphereface":
            from uniface.recognition import SphereFace

            return SphereFace(providers=self.settings.providers)
        from uniface.recognition import ArcFace

        return ArcFace(providers=self.settings.providers)

    def _get_spoofer(self):
        if self.spoofer is None:
            from uniface.spoofing import MiniFASNet

            self.spoofer = MiniFASNet(providers=self.settings.providers)
        return self.spoofer

    def _get_parser(self):
        if self.parser is None:
            if self.settings.parser == "xseg":
                from uniface.parsing import XSeg

                self.parser = XSeg(providers=self.settings.providers)
            else:
                from uniface.parsing import BiSeNet

                self.parser = BiSeNet(providers=self.settings.providers)
        return self.parser

    @staticmethod
    def _face_to_dict(face) -> dict[str, Any]:
        return {
            "confidence": round(float(face.confidence), 6),
            "bbox": [float(value) for value in face.bbox],
            "landmarks": [[float(x), float(y)] for x, y in face.landmarks],
        }
