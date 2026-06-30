import pytest

from app.video_workbench.providers.jimeng_rest_provider import (
    build_poll_request,
    build_submit_request,
    map_provider_status,
    parse_poll_response,
    parse_submit_response,
    validate_video_url,
)
from app.video_workbench.video_provider import VideoProviderError


SETTINGS = {
    "endpoint": "https://visual.volcengineapi.com",
    "region": "cn-north-1",
    "service": "cv",
    "version": "2022-08-31",
    "req_key": "jimeng_ti2v_v30_pro",
    "access_key": "ak-test",
    "secret_key": "sk-test",
}


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
