from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.video_workbench.api import get_jimeng_rest_provider, get_repository, router
from app.video_workbench.providers.jimeng_rest_provider import JimengJobResult, JimengRestProvider
from app.video_workbench.repository import VideoWorkbenchRepository
from app.video_workbench.video_provider import VideoProviderError, VideoProviderTimeoutError

CONTRACT_STATUSES = {
    "pending",
    "submitted",
    "processing",
    "completed",
    "failed",
    "timeout",
    "cancelled",
}

STORYBOARD_TEXT = (
    "第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）\n"
    "台词：你好 / Hello\n"
    "--- 提示词 ---\n"
    "Scene: Provider contract test\n"
    "--- 图生视频提示词 (I2V) ---\n"
    "Camera slowly pushes in for provider contract test."
)


def response_payload(response):
    return json.loads(response.content)


def response_data(response):
    payload = response_payload(response)
    assert payload["success"] is True
    return payload["data"]


def response_error(response):
    payload = response_payload(response)
    assert payload["success"] is False
    return payload["error"]


class DeterministicJimengRestClient:
    def __init__(
        self,
        statuses=None,
        submit_error=None,
        poll_error=None,
        result_url="https://jimeng.example/results/contract-job.mp4",
    ):
        self.statuses = list(statuses or ["completed"])
        self.submit_error = submit_error
        self.poll_error = poll_error
        self.result_url = result_url
        self.calls = []

    def submit_job(self, keyframe_path, settings):
        self.calls.append(("submit", keyframe_path, settings.get("model", ""), settings.get("prompt", "")))
        if self.submit_error == "timeout":
            raise VideoProviderTimeoutError("Jimeng provider request timeout.")
        if self.submit_error == "provider":
            raise VideoProviderError("Jimeng provider error.")
        return "contract-submit-001"

    def get_result(self, submit_id, settings):
        self.calls.append(("poll", submit_id, settings.get("model", "")))
        if self.poll_error == "timeout":
            raise VideoProviderTimeoutError("Jimeng provider request timeout.")
        if self.poll_error == "provider":
            raise VideoProviderError("Jimeng provider error.")

        status = self.statuses.pop(0) if self.statuses else "completed"
        if status == "failed":
            return JimengJobResult(status="failed", error_message="Jimeng job failed.")
        if status == "processing":
            return JimengJobResult(status="processing")
        if status == "invalid":
            return JimengJobResult(status="invalid-provider-status", result_url=self.result_url)
        return JimengJobResult(status="completed", result_url=self.result_url)

class MalformedJimengRestClient(DeterministicJimengRestClient):
    def __init__(self, payload_kind):
        super().__init__()
        self.payload_kind = payload_kind

    def get_result(self, submit_id, settings):
        self.calls.append(("poll", submit_id, settings.get("model", "")))
        if self.payload_kind == "malformed-json":
            return {"not": "a JimengJobResult"}
        if self.payload_kind == "empty-body":
            return None
        if self.payload_kind == "partial-response":
            return JimengJobResult(status="completed")
        return super().get_result(submit_id, settings)


class ProviderApiHarness:
    def __init__(self, client, provider_client=None):
        self.client = client
        self.provider_client = provider_client

    def save_settings(
        self,
        access_key="ak-contract",
        secret_key="sk-contract",
        region="cn-north-1",
        endpoint="https://open.volcengineapi.com",
        model="jimeng-v3",
        enabled=True,
    ):
        return self.client.put(
            "/api/video-workbench/provider-settings/jimeng",
            json={
                "access_key": access_key,
                "secret_key": secret_key,
                "region": region,
                "endpoint": endpoint,
                "model": model,
                "enabled": enabled,
            },
        )

    def create_project_with_keyframe(self, title="Provider Contract"):
        project_id = self.client.post(
            "/api/video-workbench/projects",
            json={"title": title},
        )["project"]["id"]
        self.client.post(
            f"/api/video-workbench/projects/{project_id}/storyboard",
            json={"text": STORYBOARD_TEXT},
        )
        self.client.post(
            f"/api/video-workbench/projects/{project_id}/shots/1/assets",
            json={"asset_type": "keyframe", "path": "/renders/contract-keyframe.png"},
        )
        return project_id

    def submit(self, project_id, shot_id=1):
        return self.client.post(f"/api/video-workbench/projects/{project_id}/shots/{shot_id}/video-jobs")

    def poll(self, job_id):
        return self.client.post(f"/api/video-workbench/video-jobs/{job_id}/poll")

    def get_job(self, job_id):
        return self.client.get(f"/api/video-workbench/video-jobs/{job_id}")

    def list_assets(self, project_id):
        return self.client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]

    def list_shots(self, project_id):
        return self.client.get(f"/api/video-workbench/projects/{project_id}/shots")["shots"]


@pytest.fixture()
def provider_api_harness(tmp_path, monkeypatch):
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

    provider_client = DeterministicJimengRestClient()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_jimeng_rest_provider] = lambda: JimengRestProvider(provider_client)
    return ProviderApiHarness(TestClient(app), provider_client)


@dataclass
class ContractJob:
    id: str
    status: str = "pending"
    submit_id: str = ""
    result_url: str = ""
    output_path: str = ""
    attempts: int = 0
    bound: bool = False
    error_message: str = ""
    events: list[str] = field(default_factory=list)


class ContractProviderAdapter:
    def __init__(self, name, states=None, valid_credentials=True, malformed_payload=False, invalid_response=False):
        self.name = name
        self.states = list(states or ["completed"])
        self.valid_credentials = valid_credentials
        self.malformed_payload = malformed_payload
        self.invalid_response = invalid_response
        self.submissions = 0

    def submit(self, payload):
        if self.malformed_payload or not payload.get("keyframe_path"):
            raise ValueError("Malformed provider payload.")
        if not self.valid_credentials:
            raise PermissionError("Invalid provider credentials.")

        self.submissions += 1
        job = ContractJob(id=f"{self.name}-job-{self.submissions}")
        job.status = "submitted"
        job.submit_id = f"{self.name}-submit-{self.submissions}"
        job.attempts = 1
        job.events.append("submit")
        return job

    def poll(self, job):
        if job.status in {"completed", "failed", "timeout", "cancelled"}:
            raise RuntimeError("Cannot poll terminal provider job.")
        if not job.submit_id:
            raise RuntimeError("Cannot poll provider job without submit_id.")

        job.events.append("poll")
        state = self.states.pop(0) if self.states else "completed"
        if self.invalid_response or state == "invalid":
            raise ValueError("Invalid provider response.")
        if state == "provider-error":
            job.status = "failed"
            job.error_message = "Provider error."
            return job
        if state == "timeout":
            job.status = "timeout"
            job.error_message = "Provider timeout."
            return job
        if state == "processing":
            job.status = "processing"
            return job

        job.status = "completed"
        job.result_url = f"https://provider.example/results/{job.submit_id}.mp4"
        return job

    def download(self, job):
        if job.status != "completed" or not job.result_url:
            raise RuntimeError("Cannot download before provider completion.")

        job.events.append("download")
        return b"contract-video-bytes"

    def bind(self, job, video_bytes):
        if job.status != "completed" or not video_bytes:
            raise RuntimeError("Cannot bind missing provider video output.")

        job.events.append("bind")
        job.output_path = f"data/uploads/1/generated/videos/{job.id}.mp4"
        job.bound = True
        return job

    def cancel(self, job):
        if job.status in {"completed", "failed", "timeout"}:
            raise RuntimeError("Cannot cancel terminal provider job.")
        job.events.append("cancel")
        job.status = "cancelled"
        return job

    def retry(self, job):
        if job.status not in {"failed", "timeout"}:
            raise RuntimeError("Can only retry failed or timed-out provider jobs.")
        if job.attempts >= 2:
            raise RuntimeError("Provider retry budget exceeded.")
        job.attempts += 1
        job.events.append("retry")
        job.status = "submitted"
        return job


@pytest.fixture(params=["mock-provider", "future-real-jimeng-provider"])
def contract_provider(request):
    return ContractProviderAdapter(request.param, states=["processing", "completed"])
