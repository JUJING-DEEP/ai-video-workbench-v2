from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.validator import validate_project


def test_validator_detects_time_gap_and_missing_asset():
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B),
        Shot(2, 3, 4, 1, ShotKind.IMAGE, ShotMode.MODE_B),
    ]
    report = validate_project(shots, audio_duration_seconds=4)
    codes = {issue["code"] for issue in report["issues"]}
    assert "time_gap" in codes
    assert "missing_image" in codes
    assert report["render_ready"] is False


def test_validator_accepts_complete_image_timeline():
    shots = [
        Shot(
            1,
            0,
            2,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            image_path="assets/images/shot_001_image.png",
        ),
        Shot(
            2,
            2,
            4,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            image_path="assets/images/shot_002_image.png",
        ),
    ]
    report = validate_project(shots, audio_duration_seconds=4)
    assert report["issues"] == []
    assert report["render_ready"] is True


def test_validator_detects_mode_a_missing_base_image():
    shots = [
        Shot(
            2,
            0,
            2,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_A,
            base_image_shot_id=1,
            image_path="assets/images/shot_002_image.png",
        ),
    ]
    report = validate_project(shots, audio_duration_seconds=2)
    assert report["issues"][0]["code"] == "missing_base_image"


def test_validator_detects_initial_time_gap():
    shots = [
        Shot(
            1,
            5,
            10,
            5,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            image_path="assets/images/shot_001_image.png",
        ),
    ]
    report = validate_project(shots, audio_duration_seconds=10)
    codes = {issue["code"] for issue in report["issues"]}
    assert "initial_time_gap" in codes
    assert report["render_ready"] is False


def test_validator_detects_invalid_duration():
    shots = [
        Shot(
            1,
            2,
            2,
            0,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            image_path="assets/images/shot_001_image.png",
        ),
        Shot(
            2,
            4,
            3,
            -1,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            image_path="assets/images/shot_002_image.png",
        ),
    ]
    report = validate_project(shots, audio_duration_seconds=4)
    codes = [issue["code"] for issue in report["issues"]]
    assert codes.count("invalid_duration") == 2
    assert report["render_ready"] is False


def test_validator_detects_duration_mismatch():
    shots = [
        Shot(
            1,
            0,
            3,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            image_path="assets/images/shot_001_image.png",
        ),
    ]
    report = validate_project(shots, audio_duration_seconds=3)
    codes = {issue["code"] for issue in report["issues"]}
    assert "duration_mismatch" in codes
    assert report["render_ready"] is False
