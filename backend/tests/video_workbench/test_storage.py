import pytest

from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.storage import ProjectStorage


def test_create_project_directories(temp_projects_root):
    storage = ProjectStorage(temp_projects_root)
    paths = storage.ensure_project_dirs("sleep-video")
    assert paths["audio"].is_dir()
    assert paths["prompts_nano_images"].is_dir()
    assert paths["assets_videos"].is_dir()
    assert paths["renders"].is_dir()


@pytest.mark.parametrize("slug", ["../outside", "/tmp/outside"])
def test_create_project_directories_rejects_unsafe_slugs(temp_projects_root, slug):
    storage = ProjectStorage(temp_projects_root)
    with pytest.raises(ValueError, match="Invalid project slug"):
        storage.ensure_project_dirs(slug)


def test_export_prompt_packages(temp_projects_root):
    storage = ProjectStorage(temp_projects_root)
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B, image_prompt="Prompt image 1"),
        Shot(
            2,
            2,
            4,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_A,
            image_prompt="Prompt image 2",
            base_image_shot_id=1,
        ),
        Shot(
            10,
            18,
            21,
            3,
            ShotKind.KEY_NODE_VIDEO,
            ShotMode.KEY_NODE,
            i2v_prompt="Prompt video 10",
        ),
    ]
    files = storage.export_prompt_packages("sleep-video", shots)
    assert files["nano_images"].exists()
    assert files["nano_keyframes"].exists()
    assert files["jimeng_i2v"].exists()
    assert "shot_001_image.png" in files["nano_images"].read_text()
    assert "shot_010_keyframe.png" in files["nano_keyframes"].read_text()
    assert "shot_010_video.mp4" in files["jimeng_i2v"].read_text()
