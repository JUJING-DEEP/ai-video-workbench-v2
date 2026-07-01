import pytest
from datetime import datetime, timezone

from app.video_workbench.providers.jimeng_rest_provider import (
    JimengRestPollClient,
    JimengRestSubmitClient,
    build_poll_request,
    build_submit_request,
    map_provider_status,
    parse_poll_response,
    parse_submit_response,
    validate_video_url,
)
from app.video_workbench.video_provider import VideoProviderError, VideoProviderTimeoutError


SETTINGS = {
    "endpoint": "https://visual.volcengineapi.com",
    "region": "cn-north-1",
    "service": "cv",
    "version": "2022-08-31",
    "req_key": "jimeng_ti2v_v30_pro",
    "access_key": "ak-test",
    "secret_key": "sk-test",
}
FIXED_TIME = datetime(2026, 6, 30, 12, 34, 56, tzinfo=timezone.utc)


class FakeSubmitTransport:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {
            "code": 10000,
            "message": "Success",
            "data": {"task_id": "7392616336519610409"},
        }
        self.error = error
        self.calls = []

    def post_json(self, request, body_json, timeout_seconds):
        self.calls.append((request, body_json, timeout_seconds))
        if self.error == "timeout":
            raise TimeoutError("submit timed out")
        return self.payload


class FakePollTransport:
    def __init__(self, payload=None, error=None):
        self.payload = payload or {
            "code": 10000,
            "message": "Success",
            "data": {"status": "generating"},
        }
        self.error = error
        self.calls = []

    def post_json(self, request, body_json, timeout_seconds):
        self.calls.append((request, body_json, timeout_seconds))
        if self.error == "timeout":
            raise TimeoutError("poll timed out")
        if self.error == "signature":
            raise PermissionError("signature mismatch")
        return self.payload


def test_submit_request_includes_official_action_version_and_req_key():
    request = build_submit_request(
        keyframe_url="https://assets.example/keyframe.png",
        prompt="camera slowly pushes in",
        settings=SETTINGS,
    )

    assert request.method == "POST"
    assert request.endpoint == "https://visual.volcengineapi.com"
    assert request.query["Action"] == "CVSync2AsyncSubmitTask"
    assert request.query["Version"] == "2022-08-31"
    assert request.body["req_key"] == "jimeng_ti2v_v30_pro"
    assert request.body["image_urls"] == ["https://assets.example/keyframe.png"]
    assert request.body["prompt"] == "camera slowly pushes in"
    assert request.region == "cn-north-1"
    assert request.service == "cv"


def test_submit_response_parses_task_id():
    task_id = parse_submit_response(
        {
            "code": 10000,
            "message": "Success",
            "data": {"task_id": "7392616336519610409"},
        }
    )

    assert task_id == "7392616336519610409"


def test_real_submit_client_signs_request_and_returns_task_id():
    transport = FakeSubmitTransport()
    client = JimengRestSubmitClient(
        transport=transport,
        request_datetime=FIXED_TIME,
    )

    task_id = client.submit_job(
        "https://assets.example/keyframe.png",
        {
            **SETTINGS,
            "prompt": "camera slowly pushes in",
        },
    )

    assert task_id == "7392616336519610409"
    assert len(transport.calls) == 1
    request, body_json, timeout_seconds = transport.calls[0]
    assert timeout_seconds == 10
    assert request.query == {
        "Action": "CVSync2AsyncSubmitTask",
        "Version": "2022-08-31",
    }
    assert request.body["req_key"] == "jimeng_ti2v_v30_pro"
    assert request.body["image_urls"] == ["https://assets.example/keyframe.png"]
    assert request.body["prompt"] == "camera slowly pushes in"
    assert '"req_key":"jimeng_ti2v_v30_pro"' in body_json
    assert request.headers["Host"] == "visual.volcengineapi.com"
    assert request.headers["X-Date"] == "20260630T123456Z"
    assert request.headers["Authorization"].startswith(
        "HMAC-SHA256 Credential=ak-test/20260630/cn-north-1/cv/request"
    )


def test_real_submit_client_maps_provider_error_response():
    client = JimengRestSubmitClient(
        transport=FakeSubmitTransport({"code": 50412, "message": "input text failed"}),
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="input text failed"):
        client.submit_job(
            "https://assets.example/keyframe.png",
            {
                **SETTINGS,
                "prompt": "blocked prompt",
            },
        )


def test_real_submit_client_maps_transport_timeout():
    client = JimengRestSubmitClient(
        transport=FakeSubmitTransport(error="timeout"),
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderTimeoutError, match="Jimeng submit request timeout"):
        client.submit_job(
            "https://assets.example/keyframe.png",
            {
                **SETTINGS,
                "prompt": "camera slowly pushes in",
            },
        )


def test_real_submit_client_rejects_missing_credentials_before_transport_call():
    transport = FakeSubmitTransport()
    client = JimengRestSubmitClient(
        transport=transport,
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="credentials"):
        client.submit_job(
            "https://assets.example/keyframe.png",
            {
                **SETTINGS,
                "access_key": "",
                "prompt": "camera slowly pushes in",
            },
        )

    assert transport.calls == []


def test_invalid_submit_response_returns_provider_error():
    with pytest.raises(VideoProviderError, match="task_id"):
        parse_submit_response({"code": 10000, "message": "Success", "data": {}})


def test_poll_request_includes_official_action_version_and_task_id():
    request = build_poll_request("7392616336519610409", SETTINGS)

    assert request.method == "POST"
    assert request.endpoint == "https://visual.volcengineapi.com"
    assert request.query["Action"] == "CVSync2AsyncGetResult"
    assert request.query["Version"] == "2022-08-31"
    assert request.body == {
        "req_key": "jimeng_ti2v_v30_pro",
        "task_id": "7392616336519610409",
    }
    assert request.region == "cn-north-1"
    assert request.service == "cv"


def test_poll_response_parses_processing_status():
    result = parse_poll_response(
        {
            "code": 10000,
            "message": "Success",
            "data": {"status": "generating"},
        }
    )

    assert result.status == "processing"
    assert result.result_url == ""


def test_poll_response_parses_completed_status_and_video_url():
    result = parse_poll_response(
        {
            "code": 10000,
            "message": "Success",
            "data": {
                "status": "done",
                "video_url": "https://results.example/generated.mp4",
            },
        }
    )

    assert result.status == "completed"
    assert result.result_url == "https://results.example/generated.mp4"


def test_real_poll_client_signs_request_and_returns_processing_status():
    transport = FakePollTransport()
    client = JimengRestPollClient(
        transport=transport,
        request_datetime=FIXED_TIME,
    )

    result = client.poll_job_status("7392616336519610409", SETTINGS)

    assert result.status == "processing"
    assert result.result_url == ""
    assert len(transport.calls) == 1
    request, body_json, timeout_seconds = transport.calls[0]
    assert timeout_seconds == 10
    assert request.query == {
        "Action": "CVSync2AsyncGetResult",
        "Version": "2022-08-31",
    }
    assert request.body == {
        "req_key": "jimeng_ti2v_v30_pro",
        "task_id": "7392616336519610409",
    }
    assert '"task_id":"7392616336519610409"' in body_json
    assert request.headers["Host"] == "visual.volcengineapi.com"
    assert request.headers["X-Date"] == "20260630T123456Z"
    assert request.headers["Authorization"].startswith(
        "HMAC-SHA256 Credential=ak-test/20260630/cn-north-1/cv/request"
    )


def test_real_poll_client_returns_completed_status_and_video_url():
    client = JimengRestPollClient(
        transport=FakePollTransport(
            {
                "code": 10000,
                "message": "Success",
                "data": {
                    "status": "done",
                    "video_url": "https://results.example/generated.mp4",
                },
            }
        ),
        request_datetime=FIXED_TIME,
    )

    result = client.poll_job_status("7392616336519610409", SETTINGS)

    assert result.status == "completed"
    assert result.result_url == "https://results.example/generated.mp4"


def test_real_poll_client_retrieves_completed_video_url():
    client = JimengRestPollClient(
        transport=FakePollTransport(
            {
                "code": 10000,
                "message": "Success",
                "data": {
                    "status": "done",
                    "video_url": "https://results.example/generated.mp4",
                },
            }
        ),
        request_datetime=FIXED_TIME,
    )

    video_url = client.retrieve_video_url("7392616336519610409", SETTINGS)

    assert video_url == "https://results.example/generated.mp4"


def test_real_poll_client_retrieve_video_url_rejects_processing_status():
    client = JimengRestPollClient(
        transport=FakePollTransport(),
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="not completed"):
        client.retrieve_video_url("7392616336519610409", SETTINGS)


def test_real_poll_client_maps_provider_failure_status():
    client = JimengRestPollClient(
        transport=FakePollTransport(
            {
                "code": 10000,
                "message": "Success",
                "data": {"status": "not_found"},
            }
        ),
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="not_found"):
        client.poll_job_status("missing-task", SETTINGS)


def test_real_poll_client_maps_timeout():
    client = JimengRestPollClient(
        transport=FakePollTransport(error="timeout"),
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderTimeoutError, match="Jimeng poll request timeout"):
        client.poll_job_status("7392616336519610409", SETTINGS)


def test_real_poll_client_maps_signature_error():
    client = JimengRestPollClient(
        transport=FakePollTransport(error="signature"),
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="signature mismatch"):
        client.poll_job_status("7392616336519610409", SETTINGS)


def test_real_poll_client_rejects_missing_task_id_before_transport_call():
    transport = FakePollTransport()
    client = JimengRestPollClient(
        transport=transport,
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="task_id"):
        client.poll_job_status("", SETTINGS)

    assert transport.calls == []


def test_real_poll_client_rejects_missing_credentials_before_transport_call():
    transport = FakePollTransport()
    client = JimengRestPollClient(
        transport=transport,
        request_datetime=FIXED_TIME,
    )

    with pytest.raises(VideoProviderError, match="credentials"):
        client.poll_job_status(
            "7392616336519610409",
            {
                **SETTINGS,
                "secret_key": "",
            },
        )

    assert transport.calls == []


def test_invalid_poll_response_returns_provider_error():
    with pytest.raises(VideoProviderError, match="Invalid Jimeng poll response"):
        parse_poll_response({"code": 10000, "message": "Success", "data": {}})


def test_expired_poll_response_returns_provider_error():
    with pytest.raises(VideoProviderError, match="expired"):
        parse_poll_response(
            {
                "code": 10000,
                "message": "Success",
                "data": {"status": "expired"},
            }
        )


def test_completed_poll_response_without_video_url_returns_provider_error():
    with pytest.raises(VideoProviderError, match="video_url"):
        parse_poll_response(
            {
                "code": 10000,
                "message": "Success",
                "data": {"status": "done"},
            }
        )


def test_validate_video_url_rejects_non_http_urls():
    with pytest.raises(VideoProviderError, match="video_url"):
        validate_video_url("file:///tmp/generated.mp4")


def test_map_provider_status_matches_official_states():
    assert map_provider_status("in_queue") == "processing"
    assert map_provider_status("generating") == "processing"
    assert map_provider_status("done") == "completed"
