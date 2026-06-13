import subprocess

import pytest

from app.video_workbench.media_probe import probe_duration_seconds
from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.render_plan import build_render_plan


def _image_shot(shot_id=1, start_seconds=0, image_path="assets/images/shot_001_image.png"):
    return Shot(
        shot_id,
        start_seconds,
        start_seconds + 2,
        2,
        ShotKind.IMAGE,
        ShotMode.MODE_B,
        image_path=image_path,
    )


def _key_node_shot(
    shot_id=10,
    start_seconds=2,
    keyframe_path="assets/keyframes/shot_010_keyframe.png",
    video_path="assets/videos/shot_010_video.mp4",
):
    return Shot(
        shot_id,
        start_seconds,
        start_seconds + 3,
        3,
        ShotKind.KEY_NODE_VIDEO,
        ShotMode.KEY_NODE,
        keyframe_path=keyframe_path,
        video_path=video_path,
    )


def test_build_render_plan_for_images_and_video():
    shots = [_image_shot(), _key_node_shot()]

    plan = build_render_plan(
        project_slug="sleep-video",
        shots=shots,
        audio_path="audio/voiceover.wav",
        audio_duration_seconds=5,
        subtitles_path="subtitles/bilingual.ass",
    )

    assert plan["duration_seconds"] == 5
    assert plan["segments"][0]["operation"] == "image_to_video"
    assert plan["segments"][1]["operation"] == "normalize_video"
    assert plan["outputs"]["clean"] == "renders/final_clean.mp4"
    assert plan["outputs"]["with_subtitles"] == "renders/final_with_subtitles.mp4"


def test_build_render_plan_rejects_missing_image_path():
    with pytest.raises(ValueError, match="Shot 1.*image"):
        build_render_plan(
            project_slug="sleep-video",
            shots=[_image_shot(image_path="")],
            audio_path="audio/voiceover.wav",
            audio_duration_seconds=2,
            subtitles_path="subtitles/bilingual.ass",
        )


def test_build_render_plan_rejects_missing_keyframe_path():
    with pytest.raises(ValueError, match="Shot 10.*keyframe"):
        build_render_plan(
            project_slug="sleep-video",
            shots=[_key_node_shot(keyframe_path="")],
            audio_path="audio/voiceover.wav",
            audio_duration_seconds=3,
            subtitles_path="subtitles/bilingual.ass",
        )


def test_build_render_plan_rejects_missing_video_path():
    with pytest.raises(ValueError, match="Shot 10.*video"):
        build_render_plan(
            project_slug="sleep-video",
            shots=[_key_node_shot(video_path="")],
            audio_path="audio/voiceover.wav",
            audio_duration_seconds=3,
            subtitles_path="subtitles/bilingual.ass",
        )


def test_build_render_plan_rejects_duplicate_shot_ids():
    with pytest.raises(ValueError, match="Duplicate shot id.*1"):
        build_render_plan(
            project_slug="sleep-video",
            shots=[_image_shot(shot_id=1), _image_shot(shot_id=1, start_seconds=2)],
            audio_path="audio/voiceover.wav",
            audio_duration_seconds=4,
            subtitles_path="subtitles/bilingual.ass",
        )


def test_build_render_plan_orders_equal_start_times_by_shot_id():
    plan = build_render_plan(
        project_slug="sleep-video",
        shots=[_image_shot(shot_id=2), _image_shot(shot_id=1)],
        audio_path="audio/voiceover.wav",
        audio_duration_seconds=2,
        subtitles_path="subtitles/bilingual.ass",
    )

    assert [segment["shot_id"] for segment in plan["segments"]] == [1, 2]


def test_probe_duration_seconds_wraps_ffprobe_failure(monkeypatch):
    def fail_ffprobe(*args, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=args[0],
            stderr="not a media file",
        )

    monkeypatch.setattr(subprocess, "run", fail_ffprobe)

    with pytest.raises(RuntimeError, match="clip.mp4.*not a media file"):
        probe_duration_seconds("clip.mp4")


def test_probe_duration_seconds_wraps_invalid_json(monkeypatch):
    class Result:
        stdout = "{}"

    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: Result())

    with pytest.raises(RuntimeError, match="clip.mp4"):
        probe_duration_seconds("clip.mp4")
