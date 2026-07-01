from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.video_workbench.api import get_jimeng_rest_provider, get_repository, router
from app.video_workbench.providers.jimeng_rest_provider import JimengRestProvider
from app.video_workbench.repository import VideoWorkbenchRepository

from .fixtures import (
    DeterministicJimengRestClient,
    MalformedJimengRestClient,
    ProviderApiHarness,
    response_data,
    response_error,
)


def make_harness(tmp_path, monkeypatch, provider_client):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        Response,
        "__getitem__",
        lambda response, key: response_data(response)[key],
        raising=False,
    )
    repository = VideoWorkbenchRepository(
        db_path=tmp_path / "video-workbench.db",
        projects_root=tmp_path / "projects",
    )
    repository.init_schema()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_jimeng_rest_provider] = lambda: JimengRestProvider(provider_client)
    return ProviderApiHarness(TestClient(app, raise_server_exceptions=False), provider_client), repository


def create_submitted_job(harness):
    harness.save_settings()
    project_id = harness.create_project_with_keyframe()
    submitted = response_data(harness.submit(project_id))["job"]
    return project_id, submitted


def assert_job_not_bound(harness, project_id, job_id, expected_status):
    job = response_data(harness.get_job(job_id))["job"]
    assert job["status"] == expected_status
    assert job["output_path"] == ""
    assert harness.list_shots(project_id)[0]["video_path"] == ""
    assert harness.list_assets(project_id) == []


def test_invalid_provider_response_marks_job_failed(tmp_path, monkeypatch):
    harness, _ = make_harness(tmp_path, monkeypatch, MalformedJimengRestClient("malformed-json"))
    project_id, submitted = create_submitted_job(harness)

    response = harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "invalid provider response" in response_error(response)["message"].lower()
    assert_job_not_bound(harness, project_id, submitted["id"], "failed")


def test_empty_provider_response_marks_job_failed(tmp_path, monkeypatch):
    harness, _ = make_harness(tmp_path, monkeypatch, MalformedJimengRestClient("empty-body"))
    project_id, submitted = create_submitted_job(harness)

    response = harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "invalid provider response" in response_error(response)["message"].lower()
    assert_job_not_bound(harness, project_id, submitted["id"], "failed")


def test_partial_provider_response_missing_video_url_marks_job_failed(tmp_path, monkeypatch):
    harness, _ = make_harness(tmp_path, monkeypatch, MalformedJimengRestClient("partial-response"))
    project_id, submitted = create_submitted_job(harness)

    response = harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "result_url" in response_error(response)["message"].lower()
    assert_job_not_bound(harness, project_id, submitted["id"], "failed")


def test_missing_submit_id_guard_rejects_malformed_job_payload(provider_api_harness):
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    repository = provider_api_harness.client.app.dependency_overrides[get_repository]()
    pending = repository.create_video_generation_job(project_id, 1, "jimeng")

    response = provider_api_harness.poll(pending["id"])

    assert response.status_code == 409
    assert "submit_id" in response_error(response)["message"]


def test_missing_video_url_marks_job_failed(provider_api_harness):
    provider_api_harness.provider_client.result_url = ""
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "result_url" in response_error(response)["message"].lower()
    assert_job_not_bound(provider_api_harness, project_id, submitted["id"], "failed")


def test_unexpected_local_job_status_rejected(tmp_path, monkeypatch):
    harness, repository = make_harness(tmp_path, monkeypatch, DeterministicJimengRestClient())
    _, submitted = create_submitted_job(harness)
    repository.update_video_generation_job(submitted["id"], status="paused")

    response = harness.poll(submitted["id"])

    assert response.status_code == 409
    assert "status" in response_error(response)["message"].lower()


def test_unknown_provider_state_marks_job_failed(provider_api_harness):
    provider_api_harness.provider_client.statuses = ["invalid"]
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]

    response = provider_api_harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "unknown provider state" in response_error(response)["message"].lower()
    assert_job_not_bound(provider_api_harness, project_id, submitted["id"], "failed")


def test_invalid_bind_result_rejected(tmp_path, monkeypatch):
    harness, repository = make_harness(tmp_path, monkeypatch, DeterministicJimengRestClient())
    project_id, submitted = create_submitted_job(harness)
    original_bind_asset = repository.bind_asset

    def failing_bind_asset(project_id, shot_id, asset_type, path):
        raise KeyError("Shot not found during bind")

    repository.bind_asset = failing_bind_asset

    response = harness.poll(submitted["id"])

    assert response.status_code == 502
    assert "bind" in response_error(response)["message"].lower()
    assert_job_not_bound(harness, project_id, submitted["id"], "failed")
    repository.bind_asset = original_bind_asset


def test_duplicate_bind_rejected(provider_api_harness):
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]
    first = provider_api_harness.poll(submitted["id"])

    response = provider_api_harness.poll(submitted["id"])

    assert first.status_code == 200
    assert response.status_code == 409
    assert "terminal" in response_error(response)["message"].lower()
    assert len(provider_api_harness.list_assets(project_id)) == 1


def test_timeout_retry_exhaustion_keeps_timed_out_job_unbound(provider_api_harness):
    provider_api_harness.provider_client.poll_error = "timeout"
    provider_api_harness.save_settings()
    project_id = provider_api_harness.create_project_with_keyframe()
    submitted = response_data(provider_api_harness.submit(project_id))["job"]
    first = provider_api_harness.poll(submitted["id"])

    response = provider_api_harness.poll(submitted["id"])

    assert first.status_code == 504
    assert response.status_code == 409
    assert "terminal" in response_error(response)["message"].lower()
    assert_job_not_bound(provider_api_harness, project_id, submitted["id"], "timeout")
