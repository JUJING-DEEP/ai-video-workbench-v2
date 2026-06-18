from __future__ import annotations

from ..video_provider import VideoGenerationProvider, VideoProviderError, VideoProviderTimeoutError


class JimengProvider(VideoGenerationProvider):
    def generate_video(self, keyframe_path: str, api_key: str, base_url: str) -> bytes:
        if api_key == "timeout":
            raise VideoProviderTimeoutError("Video provider request timeout.")
        if api_key == "provider-error":
            raise VideoProviderError("Video provider error.")

        return f"jimeng-video generated from {keyframe_path} via {base_url}".encode("utf-8")
