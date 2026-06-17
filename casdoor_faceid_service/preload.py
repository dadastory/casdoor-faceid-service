from __future__ import annotations

import os
from typing import Sequence

from .config import Settings

GITHUB_URL_PREFIX = "https://github.com/"


def parse_url_rewrites(value: str | None) -> list[tuple[str, str]]:
    if not value:
        return []

    rules = []
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError("UNIFACE_MODEL_URL_REWRITE items must use old_prefix=new_prefix")
        old_prefix, new_prefix = item.split("=", 1)
        old_prefix = old_prefix.strip()
        new_prefix = new_prefix.strip()
        if not old_prefix or not new_prefix:
            raise ValueError("UNIFACE_MODEL_URL_REWRITE prefixes cannot be empty")
        rules.append((old_prefix, new_prefix))
    return rules


def github_proxy_url_rewrites(value: str | None) -> list[tuple[str, str]]:
    if not value:
        return []

    proxy_prefix = value.strip()
    if not proxy_prefix:
        return []
    if not proxy_prefix.endswith("/"):
        proxy_prefix = f"{proxy_prefix}/"

    return [(GITHUB_URL_PREFIX, f"{proxy_prefix}{GITHUB_URL_PREFIX}")]


def get_model_url_rewrites(value: str | None, github_proxy: str | None) -> list[tuple[str, str]]:
    rules = parse_url_rewrites(value)
    if rules:
        return rules
    return github_proxy_url_rewrites(github_proxy)


def rewrite_model_url(url: str, rules: Sequence[tuple[str, str]]) -> str:
    for old_prefix, new_prefix in rules:
        if url.startswith(old_prefix):
            return f"{new_prefix}{url[len(old_prefix):]}"
    return url


def apply_model_url_rewrites(value: str | None, github_proxy: str | None = None) -> int:
    rules = get_model_url_rewrites(value, github_proxy)
    if not rules:
        return 0

    from dataclasses import replace

    from uniface import constants as const

    changed = 0
    for model_name, model_info in list(const.MODEL_REGISTRY.items()):
        rewritten_url = rewrite_model_url(model_info.url, rules)
        if rewritten_url != model_info.url:
            const.MODEL_REGISTRY[model_name] = replace(model_info, url=rewritten_url)
            changed += 1
    return changed


def get_preload_components(settings: Settings, mode: str) -> list[str]:
    normalized = mode.strip().lower()
    if normalized in {"", "none", "false", "0", "off"}:
        return []
    if normalized == "all":
        return ["detector", "recognizer", "spoofer", "parser"]

    components = ["detector", "recognizer"]
    if settings.enable_liveness:
        components.append("spoofer")
    return components


def get_preload_model_names(settings: Settings, components: Sequence[str]):
    from uniface.constants import ArcFaceWeights, MiniFASNetWeights, ParsingWeights, RetinaFaceWeights

    model_names = []
    if "detector" in components:
        model_names.append(RetinaFaceWeights.MNET_V2)
    if "recognizer" in components:
        model_names.append(ArcFaceWeights.MNET)
    if "spoofer" in components:
        model_names.append(MiniFASNetWeights.V2)
    if "parser" in components:
        model_names.append(ParsingWeights.RESNET18)
    return model_names


def preload_models(settings: Settings, mode: str) -> dict[str, str]:
    components = get_preload_components(settings, mode)
    if not components:
        return {}

    import uniface

    uniface.set_cache_dir(settings.model_cache_dir)
    apply_model_url_rewrites(
        os.environ.get("UNIFACE_MODEL_URL_REWRITE"),
        os.environ.get("UNIFACE_GITHUB_PROXY"),
    )
    model_names = get_preload_model_names(settings, components)
    downloaded = uniface.download_models(model_names)
    return {model.value: path for model, path in downloaded.items()}


def main() -> None:
    settings = Settings.from_env(os.environ)
    mode = os.environ.get("FACEID_PRELOAD_MODE", "all")
    downloaded = preload_models(settings, mode)
    if downloaded:
        print(f"Preloaded {len(downloaded)} UniFace model(s) into {settings.model_cache_dir}:")
        for name, path in sorted(downloaded.items()):
            print(f"- {name}: {path}")
    else:
        print("UniFace model preload disabled.")


if __name__ == "__main__":
    main()
