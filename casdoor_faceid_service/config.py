from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


def _env_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_float(env: Mapping[str, str], name: str, default: float) -> float:
    value = env.get(name)
    if value is None or value == "":
        return default
    return float(value)


def _env_int(env: Mapping[str, str], name: str, default: int) -> int:
    value = env.get(name)
    if value is None or value == "":
        return default
    return int(value)


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8100
    api_key: str = ""
    device: str = "cpu"
    model_cache_dir: str = "/data/models"
    detector: str = "retinaface"
    recognizer: str = "arcface"
    parser: str = "bisenet"
    enable_liveness: bool = True
    similarity_threshold: float = 0.6
    liveness_threshold: float = 0.7
    max_image_bytes: int = 8 * 1024 * 1024

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        return cls(
            host=env.get("FACEID_HOST", cls.host),
            port=_env_int(env, "FACEID_PORT", cls.port),
            api_key=env.get("FACEID_API_KEY", cls.api_key),
            device=env.get("FACEID_DEVICE", cls.device).strip().lower(),
            model_cache_dir=env.get("UNIFACE_CACHE_DIR", cls.model_cache_dir),
            detector=env.get("FACEID_DETECTOR", cls.detector).strip().lower(),
            recognizer=env.get("FACEID_RECOGNIZER", cls.recognizer).strip().lower(),
            parser=env.get("FACEID_PARSER", cls.parser).strip().lower(),
            enable_liveness=_env_bool(env.get("FACEID_ENABLE_LIVENESS"), cls.enable_liveness),
            similarity_threshold=_env_float(env, "FACEID_SIMILARITY_THRESHOLD", cls.similarity_threshold),
            liveness_threshold=_env_float(env, "FACEID_LIVENESS_THRESHOLD", cls.liveness_threshold),
            max_image_bytes=_env_int(env, "FACEID_MAX_IMAGE_BYTES", cls.max_image_bytes),
        )

    @property
    def providers(self) -> list[str]:
        if self.device == "gpu":
            return ["CUDAExecutionProvider", "CPUExecutionProvider"]
        return ["CPUExecutionProvider"]
