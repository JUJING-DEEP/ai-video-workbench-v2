import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.video_workbench.api import get_nano_banana_client, get_repository, router
from app.video_workbench.nano_banana import (
    NanoBananaInvalidKeyError,
    NanoBananaProviderError,
    NanoBananaTimeoutError,
)
from app.video_workbench.repository import VideoWorkbenchRepository


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    repository = VideoWorkbenchRepository(
        db_path=tmp_path / "video-workbench.db",
        projects_root=tmp_path / "projects",
    )
    repository.init_schema()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_repository] = lambda: repository
    return TestClient(app)


STORYBOARD_TEXT = (
    "第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）\n"
    "台词：你好 / Hello\n"
    "--- 提示词 ---\n"
    "Scene: Test"
)

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
    assert response.json() == {"status": "ok"}


def test_parse_storyboard_endpoint(client):
    response = client.post(
        "/api/video-workbench/parse",
        json={"text": STORYBOARD_TEXT},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["shots"][0]["shot_id"] == 1
    assert payload["shots"][0]["dialogue_zh"] == "你好"


def test_parse_storyboard_endpoint_returns_400_for_malformed_storyboard(client):
    response = client.post(
        "/api/video-workbench/parse",
        json={"text": "第 1 张图片 时间坏掉"},
    )

    assert response.status_code == 400
    assert "parse" in response.json()["detail"].lower()


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
    project = create_response.json()["project"]
    assert project["id"] == 1
    assert project["title"] == "Revenge Bedtime"
    assert project["slug"] == "revenge-bedtime"

    list_response = client.get("/api/video-workbench/projects")

    assert list_response.status_code == 200
    assert list_response.json()["projects"][0]["id"] == project["id"]


def test_create_project_requires_title(client):
    response = client.post("/api/video-workbench/projects", json={"title": "   "})

    assert response.status_code == 400
    assert "title" in response.json()["detail"].lower()


def test_import_storyboard_replaces_project_shots(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Storyboard Import"},
    ).json()["project"]["id"]

    import_response = client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    assert import_response.status_code == 200
    payload = import_response.json()
    assert payload["project"]["id"] == project_id
    assert payload["shots"][0]["shot_id"] == 1
    assert payload["shots"][0]["dialogue_zh"] == "你好"

    shots_response = client.get(f"/api/video-workbench/projects/{project_id}/shots")

    assert shots_response.status_code == 200
    assert shots_response.json()["shots"][0]["image_prompt"] == "Scene: Test"


def test_import_storyboard_returns_404_for_missing_project(client):
    response = client.post(
        "/api/video-workbench/projects/999/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    assert response.status_code == 404
    assert "project not found" in response.json()["detail"].lower()


def test_bind_shot_asset_updates_path_and_status(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Asset Binding"},
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "image", "path": "/renders/shot-001.png"},
    )

    assert response.status_code == 200
    shot = response.json()["shot"]
    assert shot["image_path"] == "/renders/shot-001.png"
    assert shot["status"] == "image_ready"


def test_bind_shot_asset_rejects_unknown_asset_type(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Bad Asset Type"},
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "audio", "path": "/renders/voice.mp3"},
    )

    assert response.status_code == 400
    assert "asset_type" in response.json()["detail"]


def test_bind_shot_asset_requires_path(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Path"},
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/assets",
        json={"asset_type": "image", "path": "   "},
    )

    assert response.status_code == 400
    assert "path" in response.json()["detail"].lower()


def test_create_project_asset_success(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Asset Library"},
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "Shot 001", "path": "/renders/shot-001.png"},
    )

    assert response.status_code == 200
    asset = response.json()["asset"]
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
    ).json()["project"]["id"]
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
    assets = response.json()["assets"]
    assert [asset["asset_type"] for asset in assets] == ["image", "video"]
    assert [asset["name"] for asset in assets] == ["Shot 001", "Hook Video"]


def test_create_project_asset_rejects_unknown_asset_type(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Bad Library Asset Type"},
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "audio", "name": "Voice", "path": "/renders/voice.mp3"},
    )

    assert response.status_code == 400
    assert "asset_type" in response.json()["detail"]


def test_create_project_asset_requires_name(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Asset Name"},
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "   ", "path": "/renders/shot-001.png"},
    )

    assert response.status_code == 400
    assert "name" in response.json()["detail"].lower()


def test_create_project_asset_requires_path(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Asset Path"},
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/assets",
        json={"asset_type": "image", "name": "Shot 001", "path": "   "},
    )

    assert response.status_code == 400
    assert "path" in response.json()["detail"].lower()


def test_upload_project_asset_saves_file_and_returns_metadata(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Upload Asset"},
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "image"},
        files={"file": ("shot-001.png", b"image-bytes", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
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
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/upload",
        data={"asset_type": "audio"},
        files={"file": ("voice.mp3", b"audio", "audio/mpeg")},
    )

    assert response.status_code == 400
    assert "asset_type" in response.json()["detail"]


def test_save_and_get_nano_banana_provider_settings(client):
    save_response = client.put(
        "/api/video-workbench/provider-settings/nano-banana",
        json={
            "nano_banana_api_key": "test-key",
            "nano_banana_base_url": "https://nano.example/generate",
        },
    )

    assert save_response.status_code == 200
    settings = save_response.json()["settings"]
    assert settings["provider"] == "nano_banana"
    assert settings["nano_banana_api_key"] == "test-key"
    assert settings["nano_banana_base_url"] == "https://nano.example/generate"

    get_response = client.get("/api/video-workbench/provider-settings/nano-banana")

    assert get_response.status_code == 200
    assert get_response.json()["settings"] == settings


def test_create_project_asset_persists_source_and_prompt(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Source Prompt"},
    ).json()["project"]["id"]

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
    asset = response.json()["asset"]
    assert asset["source"] == "nano_banana"
    assert asset["prompt"] == "Draw a tired stickman."


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
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_type"] == "image"
    assert payload["image_path"].startswith(f"data/uploads/{project_id}/generated/")
    assert payload["asset_id"] == 1
    assert Path(payload["image_path"]).read_bytes() == b"generated-image"

    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets").json()["assets"]
    assert assets[0]["source"] == "nano_banana"
    assert assets[0]["prompt"] == "Draw a tired stickman."


def test_generate_image_rejects_missing_prompt(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Generate Prompt"},
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "   "},
    )

    assert response.status_code == 400
    assert "prompt" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 504
    assert "timeout" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/generate-image",
        json={"prompt": "Draw a tired stickman."},
    )

    assert response.status_code == 502
    assert "provider" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_type"] == "keyframe"
    assert payload["shot_id"] == 1
    assert payload["asset_id"] == 1
    assert payload["path"].startswith(f"data/uploads/{project_id}/generated/keyframes/")
    assert Path(payload["path"]).read_bytes() == b"generated-image"


def test_generate_keyframe_empty_prompt(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Keyframe Prompt"},
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "   "},
    )

    assert response.status_code == 400
    assert "prompt" in response.json()["detail"].lower()


def test_generate_keyframe_unknown_project(client):
    response = client.post(
        "/api/video-workbench/projects/999/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 404
    assert "project" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/999/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 404
    assert "shot" in response.json()["detail"].lower()


def test_generate_keyframe_missing_provider_settings(client):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": "Missing Provider Settings"},
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 400
    assert "provider settings" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets").json()["assets"]
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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    payload = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    ).json()

    shot = client.get(f"/api/video-workbench/projects/{project_id}/shots").json()["shots"][0]
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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 504
    assert "timeout" in response.json()["detail"].lower()


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
    ).json()["project"]["id"]
    client.post(
        f"/api/video-workbench/projects/{project_id}/storyboard",
        json={"text": STORYBOARD_TEXT},
    )

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-keyframe",
        json={"prompt": "Draw a keyframe."},
    )

    assert response.status_code == 502
    assert "provider" in response.json()["detail"].lower()


def _create_project_with_shot(client, title="Video Project"):
    project_id = client.post(
        "/api/video-workbench/projects",
        json={"title": title},
    ).json()["project"]["id"]
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
    ).json()["project"]["id"]
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
    settings = response.json()["settings"]
    assert settings["provider"] == "jimeng"
    assert settings["api_key"] == "test-key"
    assert settings["base_url"] == "https://jimeng.example/generate"


def test_jimeng_settings_load(client):
    saved = _save_jimeng_settings(client).json()["settings"]

    response = client.get("/api/video-workbench/provider-settings/jimeng")

    assert response.status_code == 200
    assert response.json()["settings"] == saved


def test_generate_video_success(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Generate Video")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["asset_type"] == "video"
    assert payload["shot_id"] == 1
    assert payload["asset_id"] == 1
    assert payload["video_path"].startswith(f"data/uploads/{project_id}/generated/videos/")
    assert Path(payload["video_path"]).read_bytes().startswith(b"mock-video")


def test_generate_video_without_keyframe(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Video Missing Keyframe")

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 400
    assert "keyframe" in response.json()["detail"].lower()


def test_generate_video_unknown_project(client):
    response = client.post(
        "/api/video-workbench/projects/999/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 404
    assert "project" in response.json()["detail"].lower()


def test_generate_video_unknown_shot(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Unknown Video Shot")

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/999/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 404
    assert "shot" in response.json()["detail"].lower()


def test_generate_video_creates_asset(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Video Asset")
    _bind_keyframe(client, project_id)

    client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assets = client.get(f"/api/video-workbench/projects/{project_id}/assets").json()["assets"]
    assert assets[0]["asset_type"] == "video"
    assert assets[0]["source"] == "jimeng"
    assert assets[0]["path"].startswith(f"data/uploads/{project_id}/generated/videos/")


def test_generate_video_binds_to_shot(client):
    _save_jimeng_settings(client)
    project_id = _create_project_with_shot(client, "Bind Video")
    _bind_keyframe(client, project_id)

    payload = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    ).json()

    shot = client.get(f"/api/video-workbench/projects/{project_id}/shots").json()["shots"][0]
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
    assert "timeout" in response.json()["detail"].lower()


def test_provider_error(client):
    _save_jimeng_settings(client, api_key="provider-error")
    project_id = _create_project_with_shot(client, "Video Provider Error")
    _bind_keyframe(client, project_id)

    response = client.post(
        f"/api/video-workbench/projects/{project_id}/shots/1/generate-video",
        json={"provider": "jimeng"},
    )

    assert response.status_code == 502
    assert "provider" in response.json()["detail"].lower()


def test_generate_render_plan(client):
    project_id = _create_project_with_multi_shots(client)
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    _bind_video(client, project_id, 2, "/renders/shot-002.mp4")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    payload = response.json()
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
    ).json()["project"]["id"]

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_generate_render_plan_only_includes_video_shots(client):
    project_id = _create_project_with_multi_shots(client, "Only Video Shots")
    _bind_video(client, project_id, 2, "/renders/shot-002.mp4")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    items = response.json()["items"]
    assert [item["shot_id"] for item in items] == [2]


def test_get_render_plan(client):
    project_id = _create_project_with_multi_shots(client, "Get Render Plan")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    created = client.post(f"/api/video-workbench/projects/{project_id}/render-plan").json()

    response = client.get(f"/api/video-workbench/projects/{project_id}/render-plan")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["items"] == created["items"]


def test_export_render_plan(client):
    project_id = _create_project_with_multi_shots(client, "Export Render Plan")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")
    client.post(f"/api/video-workbench/projects/{project_id}/render-plan")

    response = client.post(f"/api/video-workbench/projects/{project_id}/render-plan/export")

    assert response.status_code == 200
    payload = response.json()
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
    path = Path(response.json()["path"])
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
    assert response.json() == {"project_id": project_id, "shot_ids": [3, 1, 2]}


def test_reorder_unknown_project(client):
    response = client.put(
        "/api/video-workbench/projects/999/shots/reorder",
        json={"shot_ids": [3, 1, 2]},
    )

    assert response.status_code == 404
    assert "project" in response.json()["detail"].lower()


def test_reorder_invalid_shot(client):
    project_id = _create_project_with_multi_shots(client, "Invalid Reorder Shot")

    response = client.put(
        f"/api/video-workbench/projects/{project_id}/shots/reorder",
        json={"shot_ids": [3, 1, 999]},
    )

    assert response.status_code == 400
    assert "shot" in response.json()["detail"].lower()


def test_get_timeline(client):
    project_id = _create_project_with_multi_shots(client, "Get Timeline")
    _bind_video(client, project_id, 1, "/renders/shot-001.mp4")

    response = client.get(f"/api/video-workbench/projects/{project_id}/timeline")

    assert response.status_code == 200
    assert response.json()["project_id"] == project_id
    assert response.json()["shots"] == [
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
    assert [shot["shot_id"] for shot in response.json()["shots"]] == [3, 1, 2]
    assert [shot["order"] for shot in response.json()["shots"]] == [1, 2, 3]
