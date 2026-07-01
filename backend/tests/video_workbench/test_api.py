import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from app.video_workbench.api import (
    get_jimeng_rest_provider,
    get_nano_banana_client,
    get_repository,
    router,
)
from app.video_workbench.nano_banana import (
    NanoBananaInvalidKeyError,
    NanoBananaProviderError,
    NanoBananaTimeoutError,
)
from app.video_workbench.providers.jimeng_rest_provider import FakeJimengRestClient, JimengRestProvider
from app.video_workbench.repository import VideoWorkbenchRepository


@pytest.fixture()
def client(tmp_path, monkeypatch):
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
    app.dependency_overrides[get_jimeng_rest_provider] = lambda: JimengRestProvider(
        FakeJimengRestClient()
    )
    return TestClient(app)


STORYBOARD_TEXT = (
    "第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）\n"
    "台词：你好 / Hello\n"
    "--- 提示词 ---\n"
    "Scene: Test"
)


def response_data(response):
    payload = json.loads(response.content)
    assert payload["success"] is True
    return payload["data"]


def response_error(response):
    payload = json.loads(response.content)
    assert payload["success"] is False
    return payload["error"]


def response_error_message(response):
    return response_error(response)["message"]

MULTI_SHOT_STORYBOARD_TEXT = (
    "第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）\n"
    "台词：第一镜 / First shot\n"
    "--- 提示词 ---\n"
    "Scene: First\n"
    "————————————————————————\n"
    "第 2 张图片 ▏时间：0:02 — 0:05 ▏模式：B（全新构图）\n"
    "台词：第二镜 / Second shot\n"
    "--- 提示词 ---\n"
    "Scene: Second\n"
    "————————————————————————\n"
    "第 3 张图片 ▏时间：0:05 — 0:09 ▏模式：B（全新构图）\n"
    "台词：第三镜 / Third shot\n"
    "--- 提示词 ---\n"
    "Scene: Third"
)


class SuccessfulNanoBananaClient:
    def generate_image(self, prompt: str, api_key: str, base_url: str) -> bytes:
        return b"generated-image"


class InvalidKeyNanoBananaClient:
    def generate_image(self, prompt: str, api_key: str, base_url: str) -> bytes:
        raise NanoBananaInvalidKeyError("Invalid Nano Banana API key.")


class TimeoutNanoBananaClient:
    def generate_image(self, prompt: str, api_key: str, base_url: str) -> bytes:
        raise NanoBananaTimeoutError("Nano Banana request timeout.")


class ProviderErrorNanoBananaClient:
    def generate_image(self, prompt: str, api_key: str, base_url: str) -> bytes:
        raise NanoBananaProviderError("Nano Banana provider error.")


def test_video_workbench_health(client):
    response = client.get("/api/video-workbench/health")

    assert response.status_code == 200
    assert response_data(response) == {"status": "ok"}


def test_api_success_and_error_responses_use_standard_envelope(client):
    success_response = client.get("/api/video-workbench/health")
    assert success_response.status_code == 200
    assert response_data(success_response) == {"status": "ok"}

    error_response = client.post("/api/video-workbench/projects", json={"title": "   "})
    assert error_response.status_code == 400
    error = response_error(error_response)
    assert error["code"] == "bad_request"
    assert "title" in error["message"].lower()


def test_parse_storyboard_endpoint(client):
    response = client.post(
        "/api/video-workbench/parse",
        json={"text": STORYBOARD_TEXT},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["shots"][0]["shot_id"] == 1
    assert payload["shots"][0]["dialogue_zh"] == "你好"


def test_parse_storyboard_endpoint_returns_400_for_malformed_storyboard(client):
    response = client.post(
        "/api/video-workbench/parse",
        json={"text": "第 1 张图片 时间坏掉"},
    )

    assert response.status_code == 400
    assert "parse" in response_error_message(response).lower()


def test_create_and_list_projects(client):
    create_response = client.post(
        "/api/video-workbench/projects",
        json={
            "title": "Revenge Bedtime",
            "role_card": "Protagonist: tired stickman",
            "audio_path": "/tmp/audio.mp3",
            "audio_duration_seconds": 538,
        },
    )

    assert create_response.status_code == 200
    project = response_data(create_response)["project"]
    assert project["id"] == 1
    assert project["title"] == "Revenge Bedtime"
    assert project["slug"] == "revenge-bedtime"

    list_response = client.get("/api/video-workbench/projects")

    assert list_response.status_code == 200
    assert response_data(list_response)["projects"][0]["id"] == project["id"]


def test_create_project_requires_title(client):
    response = client.post("/api/video-workbench/projects", json={"title": "   "})

    assert response.status_code == 400
    assert "title" in response_error_message(response).lower()


def test_import_storyboard_replaces_project_shots(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Storyboard Import"},
    )["project"]["id"]

    import_response = client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    assert import_response.status_code == 200
    payload = response_data(import_response)
    assert payload["project"]["id"] == project_id
    assert payload["shots"][0]["shot_id"] == 1
    assert payload["shots"][0]["dialogue_zh"] == "你好"

    shots_response = client.get(f"/api/video-workbench/projects/{project_id}/shots")

    assert shots_response.status_code == 200
    assert response_data(shots_response)["shots"][0]["image_prompt"] == "Scene: Test"


def test_import_storyboard_returns_404_for_missing_project(client):
    response = client.post(
        "/api/video-workbench/projects/999/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    assert response.status_code == 404
    assert "project not found" in response_error_message(response).lower()


def test_bind_shot_asset_updates_path_and_status(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Asset Binding"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "image", "path": "/renders/shot-001.png"},
    )

    assert response.status_code == 200
    shot = response_data(response)["shot"]
    assert shot["image_path"] == "/renders/shot-001.png"
    assert shot["status"] == "image_ready"


def test_bind_shot_asset_rejects_unknown_asset_type(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Bad Asset Type"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "audio", "path": "/renders/voice.mp3"},
    )

    assert response.status_code == 400
    assert "asset_type" in response_error_message(response)


def test_bind_shot_asset_requires_path(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Path"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "image", "path": "   "},
    )

    assert response.status_code == 400
    assert "path" in response_error_message(response).lower()


def test_bind_shot_asset_rejects_path_traversal(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Unsafe Bound Path"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "image", "path": "../outside.png"},
    )

    assert response.status_code == 400
    assert "path" in response_error_message(response).lower()


def test_create_project_asset_success(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Asset Library"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "Shot 001", "path": "/renders/shot-001.png"},
    )

    assert response.status_code == 200
    asset = response_data(response)["asset"]
    assert asset["id"] == 1
    assert asset["project_id"] == project_id
    assert asset["asset_type"] == "image"
    assert asset["name"] == "Shot 001"
    assert asset["path"] == "/renders/shot-001.png"
    assert asset["created_at"]


def test_list_project_assets_success(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Asset List"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "Shot 001", "path": "/renders/shot-001.png"},
    )
    client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "video", "name": "Hook Video", "path": "/renders/hook.mp4"},
    )

    response = client.get(f"/api/video-workbench/projects/{project_id}/assets")

    assert response.status_code == 200
    assets = response_data(response)["assets"]
    assert [asset["asset_type"] for asset in assets] == ["image", "video"]
    assert [asset["name"] for asset in assets] == ["Shot 001", "Hook Video"]


def test_create_project_asset_rejects_unknown_asset_type(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Bad Library Asset Type"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "audio", "name": "Voice", "path": "/renders/voice.mp3"},
    )

    assert response.status_code == 400
    assert "asset_type" in response_error_message(response)


def test_create_project_asset_requires_name(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Asset Name"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "   ", "path": "/renders/shot-001.png"},
    )

    assert response.status_code == 400
    assert "name" in response_error_message(response).lower()


def test_create_project_asset_requires_path(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Asset Path"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "Shot 001", "path": "   "},
    )

    assert response.status_code == 400
    assert "path" in response_error_message(response).lower()


def test_upload_project_asset_saves_file_and_returns_metadata(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Upload Asset"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("shot-001.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload == {
        "name": "shot-001.png",
        "path": f"data/uploads/{project_id}/shot-001.png",
        "asset_type": "image",
    }
    assert Path(payload["path"]).read_bytes() == b"image-bytes"


def test_upload_project_asset_rejects_unknown_asset_type(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Bad Upload Type"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "audio"},
        files={"file": ("voice.mp3", b"audio", "audio/mpeg")},
    )

    assert response.status_code == 400
    assert "asset_type" in response_error_message(response)


def test_upload_project_asset_rejects_unsafe_filename(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Unsafe Upload Name"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("../outside.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 400
    assert "filename" in response_error_message(response).lower()


def test_upload_project_asset_rejects_invalid_mime_for_asset_type(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Invalid Upload MIME"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("payload.txt", b"not-an-image", "text/plain")},
    )

    assert response.status_code == 400
    assert "file type" in response_error_message(response).lower()


def test_upload_project_asset_rejects_oversized_file(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Oversized Upload"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("large.png", b"0" * (26 * 1024 * 1024), "image/png")},
    )

    assert response.status_code == 413
    assert "too large" in response_error_message(response).lower()


def test_upload_project_asset_rejects_existing_filename(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Duplicate Upload"},
    )["project"]["id"]

    first_response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("shot-001.png", b"first", "image/png")},
    )
    second_response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("shot-001.png", b"second", "image/png")},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    assert Path(response_data(first_response)["path"]).read_bytes() == b"first"


def test_save_and_get_nano_banana_provider_settings(client):
    save_response = client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )

    assert save_response.status_code == 200
    settings = response_data(save_response)["settings"]
    assert settings["provider"] == "nano_banana"
    assert settings["configured"] is True
    assert settings["enabled"] is True
    assert settings["base_url"] == "https://nano.example/generate"

    get_response = client.get("/api/video-workbench/provider-settings/nano-banana")

    assert get_response.status_code == 200
    public_settings = response_data(get_response)["settings"]
    assert public_settings["provider"] == "nano_banana"
    assert public_settings["configured"] is True
    assert public_settings["enabled"] is True
    assert public_settings["base_url"] == "https://nano.example/generate"


def test_provider_settings_put_does_not_return_credentials(client):
    nano_response = client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "secret-nano-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    jimeng_response = client.put(
        "/api/video-workbench/provider-settings/jimeng",
        json={
            "api_key": "secret-jimeng-key",
            "base_url": "https://jimeng.example/generate",
            "access_key": "secret-access-key",
            "secret_key": "secret-secret-key",
            "endpoint": "https://open.volcengineapi.com",
            "model": "jimeng-v3",
        },
    )

    for response in (nano_response, jimeng_response):
        assert response.status_code == 200
        body = json.dumps(response.json())
        assert "secret-nano-key" not in body
        assert "secret-jimeng-key" not in body
        assert "secret-access-key" not in body
        assert "secret-secret-key" not in body
        settings = response_data(response)["settings"]
        assert "api_key" not in settings
        assert "nano_banana_api_key" not in settings
        assert "access_key" not in settings
        assert "secret_key" not in settings


def test_provider_settings_get_does_not_return_api_key(client):
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "secret-nano-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    _save_jimeng_settings(client, api_key="secret-jimeng-key")

    nano_settings = client.get("/api/video-workbench/provider-settings/nano-banana")["settings"]
    jimeng_settings = client.get("/api/video-workbench/provider-settings/jimeng")["settings"]

    for settings in (nano_settings, jimeng_settings):
        assert "api_key" not in settings
        assert "nano_banana_api_key" not in settings
    assert "secret-nano-key" not in json.dumps(nano_settings)
    assert "secret-jimeng-key" not in json.dumps(jimeng_settings)


def test_provider_settings_get_does_not_return_access_key(client):
    _save_jimeng_rest_settings(client, access_key="secret-access-key")

    settings = client.get("/api/video-workbench/provider-settings/jimeng")["settings"]

    assert "access_key" not in settings
    assert "secret-access-key" not in json.dumps(settings)


def test_provider_settings_get_does_not_return_secret_key(client):
    _save_jimeng_rest_settings(client, secret_key="secret-secret-key")

    settings = client.get("/api/video-workbench/provider-settings/jimeng")["settings"]

    assert "secret_key" not in settings
    assert "secret-secret-key" not in json.dumps(settings)


def test_provider_settings_reports_configured(client):
    empty_settings = client.get("/api/video-workbench/provider-settings/jimeng")["settings"]
    assert empty_settings["provider"] == "jimeng"
    assert empty_settings["configured"] is False
    assert empty_settings["enabled"] is False

    _save_jimeng_rest_settings(client)

    configured_settings = client.get("/api/video-workbench/provider-settings/jimeng")["settings"]
    assert configured_settings["provider"] == "jimeng"
    assert configured_settings["configured"] is True
    assert configured_settings["enabled"] is True


def test_provider_settings_use_unified_public_schema(client):
    nano_response = client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={"api_key": "nano-secret", "base_url": "https://nano.example/generate"},
    )
    jimeng_response = client.put(
        "/api/video-workbench/provider-settings/jimeng",
        json={
            "api_key": "jimeng-secret",
            "base_url": "https://jimeng.example/generate",
            "access_key": "access-secret",
            "secret_key": "secret-secret",
            "region": "cn-north-1",
            "endpoint": "https://open.volcengineapi.com",
            "model": "jimeng-v3",
            "enabled": True,
        },
    )

    nano = response_data(nano_response)["settings"]
    jimeng = response_data(jimeng_response)["settings"]

    assert nano["provider"] == "nano_banana"
    assert nano["enabled"] is True
    assert nano["configured"] is True
    assert nano["credentials"] == {"api_key": True}
    assert nano["base_url"] == "https://nano.example/generate"

    assert jimeng["provider"] == "jimeng"
    assert jimeng["enabled"] is True
    assert jimeng["configured"] is True
    assert jimeng["credentials"] == {
        "api_key": True,
        "access_key": True,
        "secret_key": True,
    }
    assert jimeng["base_url"] == "https://jimeng.example/generate"
    assert jimeng["region"] == "cn-north-1"
    assert jimeng["endpoint"] == "https://open.volcengineapi.com"
    assert jimeng["model"] == "jimeng-v3"

    assert "nano-secret" not in json.dumps(nano)
    assert "jimeng-secret" not in json.dumps(jimeng)
    assert "access-secret" not in json.dumps(jimeng)
    assert "secret-secret" not in json.dumps(jimeng)


def test_provider_settings_rejects_invalid_base_url(client):
    response = client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "file:///etc/passwd",
        },
    )

    assert response.status_code == 400
    assert "url" in response_error_message(response).lower()


def test_jimeng_settings_rejects_invalid_endpoint_url(client):
    response = client.put(
        "/api/video-workbench/provider-settings/jimeng",
        json={
            "access_key": "ak-test",
            "secret_key": "sk-test",
            "endpoint": "javascript:alert(1)",
            "model": "jimeng-v3",
        },
    )

    assert response.status_code == 400
    assert "url" in response_error_message(response).lower()


def test_jimeng_rest_settings_reports_non_secret_fields(client):
    response = _save_jimeng_rest_settings(
        client,
        region="cn-north-1",
        endpoint="https://open.volcengineapi.com",
        model="jimeng-v3",
    )
    settings = response_data(response)["settings"]

    assert response.status_code == 200
    assert settings["provider"] == "jimeng"
    assert settings["configured"] is True
    assert settings["enabled"] is True
    assert settings["region"] == "cn-north-1"
    assert settings["endpoint"] == "https://open.volcengineapi.com"
    assert settings["model"] == "jimeng-v3"
    assert "access_key" not in settings
    assert "secret_key" not in settings


def test_create_project_asset_persists_source_and_prompt(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Source Prompt"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={
            "asset_type": "image",
            "name": "Generated Shot",
            "path": "data/uploads/1/generated/generated-shot.png",
            "source": "nano_banana",
            "prompt": "Draw a tired stickman.",
        },
    )

    assert response.status_code == 200
    asset = response_data(response)["asset"]
    assert asset["source"] == "nano_banana"
    assert asset["prompt"] == "Draw a tired stickman."


def test_create_project_asset_rejects_path_traversal(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Unsafe Asset Path"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "Unsafe", "path": "../outside.png"},
    )

    assert response.status_code == 400
    assert "path" in response_error_message(response).lower()


def test_generate_image_creates_asset_from_nano_banana(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: SuccessfulNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Generated Image"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["asset_type"] == "image"
    assert payload["image_path"].startswith(f"data/uploads/{project_id}/generated/")
    assert payload["asset_id"] == 1
    assert Path(payload["image_path"]).read_bytes() == b"generated-image"

    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]
    assert assets[0]["source"] == "nano_banana"
    assert assets[0]["prompt"] == "Draw a tired stickman."


def test_generate_image_rejects_missing_prompt(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Generate Prompt"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "   "},
    )

    assert response.status_code == 400
    assert "prompt" in response_error_message(response).lower()


def test_generate_image_returns_invalid_key_error(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: InvalidKeyNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "bad-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Invalid Key"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 401
    assert "invalid" in response_error_message(response).lower()


def test_generate_image_returns_timeout_error(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: TimeoutNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Timeout"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 504
    assert "timeout" in response_error_message(response).lower()


def test_generate_image_returns_provider_error(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: ProviderErrorNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Provider Error"},
    )["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 502
    assert "provider" in response_error_message(response).lower()


def test_generate_keyframe_success(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: SuccessfulNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Generated Keyframe"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["asset_type"] == "keyframe"
    assert payload["shot_id"] == 1
    assert payload["asset_id"] == 1
    assert payload["path"].startswith(f"data/uploads/{project_id}/generated/keyframes/")
    assert Path(payload["path"]).read_bytes() == b"generated-image"


def test_generate_keyframe_empty_prompt(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Keyframe Prompt"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "   "},
    )

    assert response.status_code == 400
    assert "prompt" in response_error_message(response).lower()


def test_generate_keyframe_unknown_project(client):
    response = client.post(
        "/api/video-workbench/projects/999/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 404
    assert "project" in response_error_message(response).lower()


def test_generate_keyframe_unknown_shot(client):
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Keyframe Shot"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/999/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 404
    assert "shot" in response_error_message(response).lower()


def test_generate_keyframe_missing_provider_settings(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Provider Settings"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 400
    assert "provider settings" in response_error_message(response).lower()


def test_generate_keyframe_creates_keyframe_asset(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: SuccessfulNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Keyframe Asset"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]
    assert assets[0]["asset_type"] == "keyframe"
    assert assets[0]["source"] == "nano_banana"
    assert assets[0]["prompt"] == "Draw a keyframe."


def test_generate_keyframe_binds_to_shot(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: SuccessfulNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Bind Keyframe"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )
    payload = response_data(response)

    shot = client.get(f"/api/video-workbench/projects/{project_id}/shots")["shots"][0]
    assert shot["keyframe_path"] == payload["path"]


def test_generate_keyframe_invalid_provider_key(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: InvalidKeyNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "bad-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Keyframe Invalid Key"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 401
    assert "invalid" in response_error_message(response).lower()


def test_generate_keyframe_provider_timeout(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: TimeoutNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Keyframe Timeout"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 504
    assert "timeout" in response_error_message(response).lower()


def test_generate_keyframe_provider_error(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: ProviderErrorNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Keyframe Provider Error"},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 502
    assert "provider" in response_error_message(response).lower()


def _create_project_with_shot(client, title="Video Project"):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": title},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )
    return project_id


def _save_jimeng_settings(client, api_key="test-key", base_url="https://jimeng.example/generate"):
    return client.put(
        "/api/video-workbench/provider-settings/jimeng",
        json={"api_key": api_key, "base_url": base_url},
    )


def _bind_keyframe(client, project_id, shot_id=1, path="/renders/keyframe.png"):
    return client.post(
        f"/api/video-workbench/projects/{project_id}/shots/{shot_id}/assets",
        json={"asset_type": "keyframe", "path": path},
    )


def _create_project_with_multi_shots(client, title="Render Project"):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": title},
    )["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": MULTI_SHOT_STORYBOARD_TEXT},
    )
    return project_id


def _bind_video(client, project_id, shot_id, path):
    return client.post(
        f"/api/video-workbench/projects/{project_id}/shots/{shot_id}/assets",
        json={"asset_type": "video", "path": path},
    )


def test_jimeng_settings_save(client):
    response = _save_jimeng_settings(client)

    assert response.status_code == 200
    settings = response_data(response)["settings"]
    assert settings["provider"] == "jimeng"
    assert settings["configured"] is True
    assert settings["base_url"] == "https://jimeng.example/generate"
    assert settings["enabled"] is True


def test_jimeng_settings_load(client):
    _save_jimeng_settings(client)

    response = client.get("/api/video-workbench/provider-settings/jimeng")

    assert response.status_code == 200
    settings = response_data(response)["settings"]
    assert settings["provider"] == "jimeng"
    assert settings["configured"] is True
    assert settings["enabled"] is True
    assert settings["base_url"] == "https://jimeng.example/generate"


def test_generate_video_success(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Generate Video")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["asset_type"] == "video"
    assert payload["shot_id"] == 1
    assert payload["asset_id"] == 1
    assert payload["video_path"].startswith(f"data/uploads/{project_id}/generated/videos/")
    assert Path(payload["video_path"]).read_bytes().startswith(b"jimeng-video")


def test_generate_video_without_keyframe(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Video Missing Keyframe")

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 400
    assert "keyframe" in response_error_message(response).lower()


def test_generate_video_unknown_project(client):
    response = client.post(
        "/api/video-workbench/projects/999/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 404
    assert "project" in response_error_message(response).lower()


def test_generate_video_unknown_shot(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Unknown Video Shot")

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/999/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 404
    assert "shot" in response_error_message(response).lower()


def test_generate_video_creates_asset(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Video Asset")
    _bind_keyframe(client, project_id)

    client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]
    assert assets[0]["asset_type"] == "video"
    assert assets[0]["source"] == "jimeng"
    assert assets[0]["path"].startswith(f"data/uploads/{project_id}/generated/videos/")


def test_generate_video_binds_to_shot(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Bind Video")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )
    payload = response_data(response)

    shot = client.get(f"/api/video-workbench/projects/{project_id}/shots")["shots"][0]
    assert shot["video_path"] == payload["video_path"]


def test_provider_timeout(client):
    _save_jimeng_settings(client, api_key="timeout")
    project_id = _create_project_with_shot(client, "Video Timeout")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 504
    assert "timeout" in response_error_message(response).lower()


def test_provider_error(client):
    _save_jimeng_settings(client, api_key="provider-error")
    project_id = _create_project_with_shot(client, "Video Provider Error")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 502
    assert "provider" in response_error_message(response).lower()


def test_generate_render_plan(client):
    project_id = _create_project_with_multi_shots(client)
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    _bind_video(client, project_id, 2, "/renders/shot-002.mp4")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["project_id"] == project_id
    assert payload["items"] == [
        {
            "shot_id": 1,
            "order": 1,
            "video_path": "/renders/shot-001.mp4",
            "duration_seconds": 2.0,
        },
        {
            "shot_id": 2,
            "order": 2,
            "video_path": "/renders/shot-002.mp4",
            "duration_seconds": 3.0,
        },
    ]


def test_generate_render_plan_empty_project(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Empty Render Project"},
    )["project"]["id"]

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    assert response_data(response)["items"] == []


def test_generate_render_plan_only_includes_video_shots(client):
    project_id = _create_project_with_multi_shots(client, "Only Video Shots")
    _bind_video(client, project_id, 2, "/renders/shot-002.mp4")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    items = response_data(response)["items"]
    assert [item["shot_id"] for item in items] == [2]


def test_get_render_plan(client):
    project_id = _create_project_with_multi_shots(client, "Get Render Plan")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    created_response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")
    created = response_data(created_response)

    response = client.get(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    assert response_data(response)["id"] == created["id"]
    assert response_data(response)["items"] == created["items"]


def test_export_render_plan(client):
    project_id = _create_project_with_multi_shots(client, "Export Render Plan")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan/export")

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["path"] == f"data/exports/{project_id}/render-plan.json"
    assert payload["render_plan"]["project_id"] == project_id
    assert payload["render_plan"]["shots"] == [
        {
            "shot_id": 1,
            "video_path": "/renders/shot-001.mp4",
            "duration_seconds": 2.0,
        }
    ]


def test_export_file_created(client):
    project_id = _create_project_with_multi_shots(client, "Export File")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan/export")

    assert response.status_code == 200
    path = Path(response_data(response)["path"])
    assert path.exists()
    exported = json.loads(path.read_text())
    assert exported["project_id"] == project_id
    assert exported["shots"][0]["video_path"] == "/renders/shot-001.mp4"


def test_reorder_shots(client):
    project_id = _create_project_with_multi_shots(client, "Reorder Shots")

    response = client.put(
        f"/api/video-workbench/projects/{project_id}/shots/reorder",
        json={"shot_ids": [3, 1, 2]},
    )

    assert response.status_code == 200
    assert response_data(response) == {"project_id": project_id, "shot_ids": [3, 1, 2]}


def test_reorder_unknown_project(client):
    response = client.put(
        "/api/video-workbench/projects/999/shots/reorder",
        json={"shot_ids": [3, 1, 2]},
    )

    assert response.status_code == 404
    assert "project" in response_error_message(response).lower()


def test_reorder_invalid_shot(client):
    project_id = _create_project_with_multi_shots(client, "Invalid Reorder Shot")

    response = client.put(
        f"/api/video-workbench/projects/{project_id}/shots/reorder",
        json={"shot_ids": [3, 1, 999]},
    )

    assert response.status_code == 400
    assert "shot" in response_error_message(response).lower()


def test_get_timeline(client):
    project_id = _create_project_with_multi_shots(client, "Get Timeline")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")

    response = client.get(f"/api/video-workbench/projects/{project_id}/timeline")

    assert response.status_code == 200
    assert response_data(response)["project_id"] == project_id
    assert response_data(response)["shots"] == [
        {
            "shot_id": 1,
            "order": 1,
            "title": "第一镜",
            "video_path": "/renders/shot-001.mp4",
            "duration_seconds": 2.0,
        },
        {
            "shot_id": 2,
            "order": 2,
            "title": "第二镜",
            "video_path": "",
            "duration_seconds": 3.0,
        },
        {
            "shot_id": 3,
            "order": 3,
            "title": "第三镜",
            "video_path": "",
            "duration_seconds": 4.0,
        },
    ]


def test_timeline_order_persistence(client):
    project_id = _create_project_with_multi_shots(client, "Timeline Persistence")
    client.put(
        f"/api/video-workbench/projects/{project_id}/shots/reorder",
        json={"shot_ids": [3, 1, 2]},
    )

    response = client.get(f"/api/video-workbench/projects/{project_id}/timeline")

    assert response.status_code == 200
    assert [shot["shot_id"] for shot in response_data(response)["shots"]] == [3, 1, 2]
    assert [shot["order"] for shot in response_data(response)["shots"]] == [1, 2, 3]


def test_unknown_provider(client):
    project_id = _create_project_with_shot(client, "Unknown Video Provider")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "missing-provider"},
    )

    assert response.status_code == 400
    assert "provider" in response_error_message(response).lower()


def test_disabled_provider(client):
    client.put(
        "/api/video-workbench/provider-settings/jimeng",
        json={"api_key": "test-key", "base_url": "https://jimeng.example/generate", "enabled": False},
    )
    project_id = _create_project_with_shot(client, "Disabled Video Provider")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 403
    assert "disabled" in response_error_message(response).lower()


def test_generate_video_with_mock(client):
    project_id = _create_project_with_shot(client, "Mock Video Provider")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "mock"},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["asset_type"] == "video"
    assert payload["video_path"].startswith(f"data/uploads/{project_id}/generated/videos/")
    assert Path(payload["video_path"]).read_bytes().startswith(b"mock-video")
    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]
    assert assets[0]["source"] == "mock"


def test_generate_video_with_jimeng(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Jimeng Video Provider")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 200
    payload = response_data(response)
    assert payload["asset_type"] == "video"
    assert Path(payload["video_path"]).read_bytes().startswith(b"jimeng-video")
    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]
    assert assets[0]["source"] == "jimeng"


def _save_jimeng_rest_settings(
    client,
    access_key="ak-test",
    secret_key="sk-test",
    region="cn-north-1",
    endpoint="https://open.volcengineapi.com",
    model="jimeng-v3",
    enabled=True,
):
    return client.put(
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


def test_create_video_job_success(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "REST Video Job")
    _bind_keyframe(client, project_id)

    response = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")

    assert response.status_code == 200
    job = response_data(response)["job"]
    assert job["project_id"] == project_id
    assert job["shot_id"] == 1
    assert job["provider"] == "jimeng"
    assert job["status"] == "submitted"
    assert job["submit_id"]


def test_video_workbench_smoke_project_shot_keyframe_video_render_plan(client):
    client.app.dependency_overrides[get_nano_banana_client] = lambda: SuccessfulNanoBananaClient()
    client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )

    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Smoke Chain"},
    )["project"]["id"]
    storyboard = client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )
    keyframe = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )
    video = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "mock"},
    )
    render_plan = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert storyboard.status_code == 200
    assert response_data(storyboard)["shots"][0]["shot_id"] == 1
    assert keyframe.status_code == 200
    assert response_data(keyframe)["asset_type"] == "keyframe"
    assert video.status_code == 200
    assert response_data(video)["asset_type"] == "video"
    assert render_plan.status_code == 200
    assert response_data(render_plan)["items"][0]["shot_id"] == 1
    assert response_data(render_plan)["items"][0]["video_path"] == response_data(video)["video_path"]


def test_create_video_job_without_keyframe(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "REST Video Job Missing Keyframe")

    response = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")

    assert response.status_code == 400
    assert "keyframe" in response_error_message(response).lower()


def test_create_video_job_disabled_provider(client):
    _save_jimeng_rest_settings(client, enabled=False)
    project_id = _create_project_with_shot(client, "REST Video Job Disabled")
    _bind_keyframe(client, project_id)

    response = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")

    assert response.status_code == 403
    assert "disabled" in response_error_message(response).lower()


def test_create_video_job_missing_credentials(client):
    _save_jimeng_rest_settings(client, access_key="", secret_key="")
    project_id = _create_project_with_shot(client, "REST Video Job Missing Credentials")
    _bind_keyframe(client, project_id)

    response = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")

    assert response.status_code == 400
    assert "credentials" in response_error_message(response).lower()


def test_get_video_job(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "Get REST Video Job")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.get(f"/api/video-workbench/video-jobs/{created['id']}")

    assert response.status_code == 200
    assert response_data(response)["job"]["id"] == created["id"]
    assert response_data(response)["job"]["status"] == "submitted"


def test_poll_video_job_processing(client):
    _save_jimeng_rest_settings(client, model="processing")
    project_id = _create_project_with_shot(client, "Processing REST Video Job")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert response.status_code == 200
    assert response_data(response)["job"]["status"] == "processing"


def test_poll_video_job_completed_creates_asset(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "Completed REST Video Asset")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert response.status_code == 200
    job = response_data(response)["job"]
    assert job["status"] == "completed"
    assert job["output_path"] == job["result_url"]
    assert job["result_url"].startswith("https://jimeng.example/results/")
    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets")["assets"]
    assert assets[0]["asset_type"] == "video"
    assert assets[0]["source"] == "jimeng"
    assert assets[0]["path"] == job["result_url"]


def test_poll_video_job_completed_binds_video(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "Completed REST Video Bind")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert response.status_code == 200
    shot = client.get(f"/api/video-workbench/projects/{project_id}/shots")["shots"][0]
    assert shot["video_path"] == response_data(response)["job"]["output_path"]


def test_poll_video_job_rejects_terminal_status(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "Terminal REST Video Job")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]
    first_poll = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert first_poll.status_code == 200
    assert response_data(first_poll)["job"]["status"] == "completed"
    assert response.status_code == 409
    assert "terminal" in response_error_message(response).lower()


def test_poll_video_job_failed(client):
    _save_jimeng_rest_settings(client, model="failed")
    project_id = _create_project_with_shot(client, "Failed REST Video Job")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert response.status_code == 200
    assert response_data(response)["job"]["status"] == "failed"
    assert "failed" in response_data(response)["job"]["error_message"].lower()


def test_poll_video_job_provider_error(client):
    _save_jimeng_rest_settings(client, model="provider-error")
    project_id = _create_project_with_shot(client, "Provider Error REST Video Job")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert response.status_code == 502
    job = client.get(f"/api/video-workbench/video-jobs/{created['id']}")["job"]
    assert job["status"] == "failed"
    assert "provider" in job["error_message"].lower()


def test_create_video_job_unknown_project(client):
    response = client.post("/api/video-workbench/projects/999/shots/1/video-jobs")

    assert response.status_code == 404
    assert "project" in response_error_message(response).lower()


def test_create_video_job_unknown_shot(client):
    _save_jimeng_rest_settings(client)
    project_id = _create_project_with_shot(client, "REST Video Job Unknown Shot")

    response = client.post(f"/api/video-workbench/projects/{project_id}/shots/999/video-jobs")

    assert response.status_code == 404
    assert "shot" in response_error_message(response).lower()


def test_poll_video_job_provider_timeout(client):
    _save_jimeng_rest_settings(client, model="timeout")
    project_id = _create_project_with_shot(client, "Timeout REST Video Job")
    _bind_keyframe(client, project_id)
    created = client.post(f"/api/video-workbench/projects/{project_id}/shots/1/video-jobs")["job"]

    response = client.post(f"/api/video-workbench/video-jobs/{created['id']}/poll")

    assert response.status_code == 504
    job = client.get(f"/api/video-workbench/video-jobs/{created['id']}")["job"]
    assert job["status"] == "timeout"
