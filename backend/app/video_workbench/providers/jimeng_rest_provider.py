from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from urllib import error, request
from urllib.parse import urlencode
from urllib.parse import urlparse

from ..video_provider import VideoProviderError, VideoProviderTimeoutError
from .volcengine_v4_signer import sign_request

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


class JimengRestSubmitTransport:
    def post_json(self, request: JimengRestRequest, body_json: str, timeout_seconds: int) -> dict:
        raise NotImplementedError("Jimeng REST submit transport is not configured.")


class JimengRestPollTransport:
    def post_json(self, request: JimengRestRequest, body_json: str, timeout_seconds: int) -> dict:
        raise NotImplementedError("Jimeng REST poll transport is not configured.")


class VolcEngineTransport(JimengRestSubmitTransport, JimengRestPollTransport):
    def post_json(self, rest_request: JimengRestRequest, body_json: str, timeout_seconds: int) -> dict:
        url = f"{rest_request.endpoint}?{urlencode(rest_request.query)}"
        http_request = request.Request(
            url=url,
            data=body_json.encode("utf-8"),
            headers=rest_request.headers,
            method=rest_request.method,
        )

        try:
            with request.urlopen(http_request, timeout=timeout_seconds) as response:
                payload = response.read().decode("utf-8")
        except error.HTTPError as exc:
            message = exc.read().decode("utf-8", errors="replace")
            raise VideoProviderError(f"Jimeng REST request failed: {exc.code} {message}") from exc
        except TimeoutError:
            raise
        except error.URLError as exc:
            if isinstance(exc.reason, TimeoutError):
                raise TimeoutError(str(exc)) from exc
            raise VideoProviderError(f"Jimeng REST request failed: {exc}") from exc

        try:
            return json.loads(payload)
        except json.JSONDecodeError as exc:
            raise VideoProviderError("Invalid Jimeng REST response: malformed JSON.") from exc


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


def _optional_setting(settings: dict, key: str) -> str:
    return str(settings.get(key, "")).strip()


def _json_body(body: dict) -> str:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def _endpoint_host(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise VideoProviderError("Invalid Jimeng endpoint URL.")
    return parsed.netloc


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


def _signed_request(
    request: JimengRestRequest,
    body_json: str,
    access_key: str,
    secret_key: str,
    request_datetime: datetime | None,
) -> JimengRestRequest:
    signed = sign_request(
        method=request.method,
        path="/",
        query=request.query,
        headers={
            **request.headers,
            "Host": _endpoint_host(request.endpoint),
        },
        payload=body_json,
        access_key=access_key,
        secret_key=secret_key,
        region=request.region,
        service=request.service,
        request_datetime=request_datetime,
    )
    request.headers = signed.headers
    return request


def _credentials(settings: dict) -> tuple[str, str]:
    access_key = _optional_setting(settings, "access_key")
    secret_key = _optional_setting(settings, "secret_key")
    if not access_key or not secret_key:
        raise VideoProviderError("Jimeng REST credentials are required.")
    return access_key, secret_key


class JimengRestSubmitClient:
    def __init__(
        self,
        transport: JimengRestSubmitTransport | None = None,
        request_datetime: datetime | None = None,
        timeout_seconds: int = 10,
    ):
        self.transport = transport
        self.request_datetime = request_datetime
        self.timeout_seconds = timeout_seconds

    def submit_job(self, keyframe_path: str, settings: dict) -> str:
        if self.transport is None:
            raise VideoProviderError("Jimeng REST submit transport is not configured.")

        access_key, secret_key = _credentials(settings)

        prompt = _optional_setting(settings, "prompt")
        if not prompt:
            raise VideoProviderError("Jimeng REST submit prompt is required.")

        request = build_submit_request(
            keyframe_url=keyframe_path,
            prompt=prompt,
            settings=settings,
        )
        body_json = _json_body(request.body)
        request = _signed_request(
            request=request,
            body_json=body_json,
            access_key=access_key,
            secret_key=secret_key,
            request_datetime=self.request_datetime,
        )

        try:
            payload = self.transport.post_json(request, body_json, self.timeout_seconds)
        except TimeoutError as exc:
            raise VideoProviderTimeoutError("Jimeng submit request timeout.") from exc
        except VideoProviderTimeoutError:
            raise
        except VideoProviderError:
            raise
        except Exception as exc:
            raise VideoProviderError(f"Jimeng submit request failed: {exc}") from exc

        return parse_submit_response(payload)


class JimengRestPollClient:
    def __init__(
        self,
        transport: JimengRestPollTransport | None = None,
        request_datetime: datetime | None = None,
        timeout_seconds: int = 10,
    ):
        self.transport = transport
        self.request_datetime = request_datetime
        self.timeout_seconds = timeout_seconds

    def poll_job_status(self, task_id: str, settings: dict) -> JimengJobResult:
        if self.transport is None:
            raise VideoProviderError("Jimeng REST poll transport is not configured.")

        value = str(task_id or "").strip()
        if not value:
            raise VideoProviderError("Jimeng REST poll task_id is required.")

        access_key, secret_key = _credentials(settings)
        request = build_poll_request(value, settings)
        body_json = _json_body(request.body)
        request = _signed_request(
            request=request,
            body_json=body_json,
            access_key=access_key,
            secret_key=secret_key,
            request_datetime=self.request_datetime,
        )

        try:
            payload = self.transport.post_json(request, body_json, self.timeout_seconds)
        except TimeoutError as exc:
            raise VideoProviderTimeoutError("Jimeng poll request timeout.") from exc
        except VideoProviderTimeoutError:
            raise
        except VideoProviderError:
            raise
        except Exception as exc:
            raise VideoProviderError(f"Jimeng poll request failed: {exc}") from exc

        return parse_poll_response(payload)

    def retrieve_video_url(self, task_id: str, settings: dict) -> str:
        result = self.poll_job_status(task_id, settings)
        if result.status != "completed":
            raise VideoProviderError("Jimeng task is not completed; video_url is not available.")
        return validate_video_url(result.result_url)


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
    def __init__(
        self,
        client: FakeJimengRestClient | None = None,
        submit_client: JimengRestSubmitClient | None = None,
        poll_client: JimengRestPollClient | None = None,
    ):
        transport = VolcEngineTransport()
        self.client = client
        self.submit_client = submit_client or JimengRestSubmitClient(transport)
        self.poll_client = poll_client or JimengRestPollClient(transport)

    def submit_video_generation_job(self, job_id: int, shot_data, settings: dict) -> str:
        prompt = str(getattr(shot_data, "i2v_prompt", "") or "").strip()
        request_settings = {**settings, "prompt": prompt}
        keyframe_path = str(getattr(shot_data, "keyframe_path", "") or "").strip()
        if self.client is not None:
            return self.client.submit_job(keyframe_path, request_settings)
        return self.submit_client.submit_job(keyframe_path, request_settings)

    def poll_video_generation_job(self, task_id: str, settings: dict) -> JimengJobResult:
        if self.client is not None:
            return self.client.get_result(task_id, settings)
        return self.poll_client.poll_job_status(task_id, settings)

    def retrieve_video_url(self, task_id: str, settings: dict) -> str:
        if self.client is not None:
            result = self.client.get_result(task_id, settings)
            if result.status != "completed":
                raise VideoProviderError("Jimeng task is not completed; video_url is not available.")
            return validate_video_url(result.result_url)
        return self.poll_client.retrieve_video_url(task_id, settings)

    def submit_job(self, keyframe_path: str, settings: dict) -> str:
        if self.client is None:
            return self.submit_client.submit_job(keyframe_path, settings)
        return self.client.submit_job(keyframe_path, settings)

    def get_result(self, submit_id: str, settings: dict) -> JimengJobResult:
        if self.client is None:
            return self.poll_client.poll_job_status(submit_id, settings)
        return self.client.get_result(submit_id, settings)

    def download_video(self, result_url: str, settings: dict) -> bytes:
        if self.client is None:
            raise VideoProviderError("Jimeng REST provider does not download videos in this phase.")
        return self.client.download_video(result_url, settings)
