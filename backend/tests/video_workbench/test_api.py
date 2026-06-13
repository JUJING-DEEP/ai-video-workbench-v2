import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.video_workbench.api import get_repository, router
from app.video_workbench.repository import VideoWorkbenchRepository


@pytest.fixture()
def client(tmp_path):
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
