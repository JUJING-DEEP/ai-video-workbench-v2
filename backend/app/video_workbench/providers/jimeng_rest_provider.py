from __future__ import annotations

from dataclasses import dataclass

from ..video_provider import VideoProviderError, VideoProviderTimeoutError


@dataclass
class JimengJobResult:
    status: str
    result_url: str = ""
    error_message: str = ""


class FakeJimengRestClient:
    def submit_job(self, keyframe_path: str, settings: dict) -> str:
        model = settings.get("model", "")
        if model == "submit-timeout":
            raise VideoProviderTimeoutError("Jimeng provider request timeout.")
        if model == "submit-error":
            raise VideoProviderError("Jimeng provider error.")
        return f"fake-jimeng-{abs(hash(keyframe_path + model))}"

    def get_result(self, submit_id: str, settings: dict) -> JimengJobResult:
        model = settings.get("model", "")
        if model == "provider-error":
            raise VideoProviderError("Jimeng provider error.")
        if model == "timeout":
            raise VideoProviderTimeoutError("Jimeng provider request timeout.")
        if model == "processing":
            return JimengJobResult(status="processing")
        if model == "failed":
            return JimengJobResult(status="failed", error_message="Jimeng job failed.")
        return JimengJobResult(status="completed", result_url=f"https://jimeng.example/results/{submit_id}.mp4")

    def download_video(self, result_url: str, settings: dict) -> bytes:
        return f"jimeng-rest-video downloaded from {result_url}".encode("utf-8")


class JimengRestProvider:
    def __init__(self, client: FakeJimengRestClient | None = None):
        self.client = client or FakeJimengRestClient()

    def submit_job(self, keyframe_path: str, settings: dict) -> str:
        return self.client.submit_job(keyframe_path, settings)

    def get_result(self, submit_id: str, settings: dict) -> JimengJobResult:
        return self.client.get_result(submit_id, settings)

    def download_video(self, result_url: str, settings: dict) -> bytes:
        return self.client.download_video(result_url, settings)
