from __future__ import annotations


class VideoProviderError(Exception):
    status_code = 502


class VideoProviderTimeoutError(VideoProviderError):
    status_code = 504


class VideoGenerationProvider:
    def generate_video(self, keyframe_path: str, api_key: str, base_url: str) -> bytes:
        raise NotImplementedError


class MockVideoProvider(VideoGenerationProvider):
    def generate_video(self, keyframe_path: str, api_key: str, base_url: str) -> bytes:
        if api_key == "timeout":
            raise VideoProviderTimeoutError("Video provider request timeout.")
        if api_key == "provider-error":
            raise VideoProviderError("Video provider error.")

        return f"mock-video generated from {keyframe_path} via {base_url}".encode("utf-8")
