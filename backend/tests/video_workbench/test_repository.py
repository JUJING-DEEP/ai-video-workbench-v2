import pytest

from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.repository import VideoWorkbenchRepository


def test_create_project_and_list_projects(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()

    project = repo.create_project(
        title="Sleep Video",
        role_card="Protagonist role",
        audio_path="audio/voiceover.wav",
        audio_duration_seconds=538,
    )

    projects = repo.list_projects()
    assert projects[0]["id"] == project["id"]
    assert projects[0]["title"] == "Sleep Video"
    assert projects[0]["audio_duration_seconds"] == 538


def test_replace_project_shots_and_fetch(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()
    project = repo.create_project("Sleep Video", "", "", None)

    repo.replace_project_shots(
        project["id"],
        [
            Shot(
                shot_id=1,
                start_seconds=0,
                end_seconds=2,
                duration_seconds=2,
                kind=ShotKind.IMAGE,
                mode=ShotMode.MODE_B,
                dialogue_zh="真相是，你完全被骗了...",
                image_prompt="Scene: bed",
            )
        ],
    )

    shots = repo.get_project_shots(project["id"])
    assert len(shots) == 1
    assert shots[0].shot_id == 1
    assert shots[0].dialogue_zh == "真相是，你完全被骗了..."


def test_duplicate_project_titles_get_unique_slugs(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()

    first = repo.create_project("Sleep Video", "", "", None)
    second = repo.create_project("Sleep Video!", "", "", None)
    third = repo.create_project("Sleep Video", "", "", None)

    assert first["slug"] == "sleep-video"
    assert second["slug"] == "sleep-video-2"
    assert third["slug"] == "sleep-video-3"
    assert (temp_projects_root / "sleep-video").is_dir()
    assert (temp_projects_root / "sleep-video-2").is_dir()
    assert (temp_projects_root / "sleep-video-3").is_dir()


def test_bind_asset_updates_image_path_and_status(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()
    project = repo.create_project("Sleep Video", "", "", None)
    repo.replace_project_shots(
        project["id"],
        [
            Shot(
                shot_id=1,
                start_seconds=0,
                end_seconds=2,
                duration_seconds=2,
                kind=ShotKind.IMAGE,
                mode=ShotMode.MODE_B,
            )
        ],
    )

    repo.bind_asset(project["id"], 1, "image", "assets/shot-001.png")

    shot = repo.get_project_shots(project["id"])[0]
    assert shot.image_path == "assets/shot-001.png"
    assert shot.status.value == "image_ready"


def test_bind_asset_missing_shot_raises_key_error(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()
    project = repo.create_project("Sleep Video", "", "", None)

    with pytest.raises(KeyError, match="Shot not found"):
        repo.bind_asset(project["id"], 999, "image", "assets/missing.png")


def test_replace_project_shots_missing_project_raises_key_error(
    temp_db_path, temp_projects_root
):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()

    with pytest.raises(KeyError, match="Project not found"):
        repo.replace_project_shots(
            999,
            [
                Shot(
                    shot_id=1,
                    start_seconds=0,
                    end_seconds=2,
                    duration_seconds=2,
                    kind=ShotKind.IMAGE,
                    mode=ShotMode.MODE_B,
                )
            ],
        )
