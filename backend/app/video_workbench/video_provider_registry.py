from __future__ import annotations

from .providers.jimeng_provider import JimengProvider
from .video_provider import MockVideoProvider, VideoGenerationProvider


def get_video_provider(provider: str) -> VideoGenerationProvider:
    normalized = provider.strip().lower()
    if normalized == "mock":
        return MockVideoProvider()
    if normalized == "jimeng":
        return JimengProvider()
    raise ValueError(f"Unknown video provider: {provider}")
