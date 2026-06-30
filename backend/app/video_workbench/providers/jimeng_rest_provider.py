from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from ..video_provider import VideoProviderError, VideoProviderTimeoutError

DEFAULT_ENDPOINT = "https://visual.volcengineapi.com"
DEFAULT_REGION = "cn-north-1"
DEFAULT_SERVICE = "cv"
DEFAULT_VERSION = "2022-08-31"
DEFAULT_REQ_KEY = "jimeng_ti2v_v30_pro"
SUBMIT_ACTION = "CVSync2AsyncSubmitTask"
POLL_ACTION = "CVSync2AsyncGetResult"


@dataclass
class JimengJobResult:
    status: str
    result_url: str = ""
    error_message: str = ""


@dataclass
class JimengRestRequest:
    method: str
    endpoint: str
    query: dict
    headers: dict
    body: dict
    region: str
    service: str
    signing_required: bool = True


def _setting(settings: dict, key: str, default: str) -> str:
    value = str(settings.get(key, "")).strip()
    return value or default


def _rest_config(settings: dict) -> dict:
    return {
        "endpoint": _setting(settings, "endpoint", DEFAULT_ENDPOINT),
        "region": _setting(settings, "region", DEFAULT_REGION),
        "service": _setting(settings, "service", DEFAULT_SERVICE),
        "version": _setting(settings, "version", DEFAULT_VERSION),
        "req_key": _setting(settings, "req_key", DEFAULT_REQ_KEY),
    }


def _build_request(settings: dict, action: str, body: dict) -> JimengRestRequest:
    config = _rest_config(settings)
    return JimengRestRequest(
        method="POST",
        endpoint=config["endpoint"],
        query={
            "Action": action,
            "Version": config["version"],
        },
        headers={
            "Content-Type": "application/json",
        },
        body=body,
        region=config["region"],
        service=config["service"],
    )


def build_submit_request(
    keyframe_url: str,
    prompt: str,
    settings: dict,
    frames: int = 121,
    aspect_ratio: str = "16:9",
    seed: int = -1,
) -> JimengRestRequest:
    config = _rest_config(settings)
    body = {
        "req_key": config["req_key"],
        "image_urls": [keyframe_url],
        "prompt": prompt,
        "seed": seed,
        "frames": frames,
        "aspect_ratio": aspect_ratio,
    }
    return _build_request(settings, SUBMIT_ACTION, body)


def parse_submit_response(payload: dict) -> str:
    if not isinstance(payload, dict):
        raise VideoProviderError("Invalid Jimeng submit response.")
    if payload.get("code") != 10000:
        message = payload.get("message", "Jimeng submit failed.")
        raise VideoProviderError(f"Jimeng submit failed: {message}")

    data = payload.get("data")
    task_id = data.get("task_id", "") if isinstance(data, dict) else ""
    if not str(task_id).strip():
        raise VideoProviderError("Invalid Jimeng submit response: missing task_id.")
    return str(task_id).strip()


def build_poll_request(task_id: str, settings: dict) -> JimengRestRequest:
    config = _rest_config(settings)
    return _build_request(
        settings,
        POLL_ACTION,
        {
            "req_key": config["req_key"],
            "task_id": task_id,
        },
    )


def validate_video_url(video_url: str) -> str:
    value = str(video_url or "").strip()
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise VideoProviderError("Invalid Jimeng poll response: missing or invalid video_url.")
    return value


def map_provider_status(status: str) -> str:
    if status in {"in_queue", "generating", "processing"}:
        return "processing"
    if status == "done":
        return "completed"
    if status in {"not_found", "expired"}:
        return "failed"
    raise VideoProviderError(f"Unknown Jimeng provider state: {status}")


def parse_poll_response(payload: dict) -> JimengJobResult:
    if not isinstance(payload, dict):
        raise VideoProviderError("Invalid Jimeng poll response.")
    if payload.get("code") != 10000:
        message = payload.get("message", "Jimeng poll failed.")
        raise VideoProviderError(f"Jimeng poll failed: {message}")

    data = payload.get("data")
    if not isinstance(data, dict) or not str(data.get("status", "")).strip():
        raise VideoProviderError("Invalid Jimeng poll response: missing status.")

    remote_status = str(data["status"]).strip()
    if remote_status in {"not_found", "expired"}:
        raise VideoProviderError(f"Jimeng task {remote_status}.")

    local_status = map_provider_status(remote_status)
    if local_status == "completed":
        return JimengJobResult(
            status=local_status,
            result_url=validate_video_url(data.get("video_url", "")),
        )
    return JimengJobResult(status=local_status)


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
