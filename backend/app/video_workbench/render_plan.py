from __future__ import annotations

from .models import Shot, ShotKind


def build_render_plan(
    project_slug: str,
    shots: list[Shot],
    audio_path: str,
    audio_duration_seconds: float,
    subtitles_path: str,
) -> dict:
    _validate_unique_shot_ids(shots)

    segments = []
    for shot in sorted(shots, key=lambda item: (item.start_seconds, item.shot_id)):
        if shot.kind == ShotKind.IMAGE:
            if not shot.image_path:
                raise ValueError(f"Shot {shot.shot_id} is missing image path")
            segments.append(
                {
                    "shot_id": shot.shot_id,
                    "operation": "image_to_video",
                    "input": shot.image_path,
                    "start_seconds": shot.start_seconds,
                    "duration_seconds": shot.duration_seconds,
                    "output": f"renders/segments/shot_{shot.shot_id:03d}.mp4",
                }
            )
        else:
            if not shot.keyframe_path:
                raise ValueError(f"Shot {shot.shot_id} is missing keyframe path")
            if not shot.video_path:
                raise ValueError(f"Shot {shot.shot_id} is missing video path")
            segments.append(
                {
                    "shot_id": shot.shot_id,
                    "operation": "normalize_video",
                    "input": shot.video_path,
                    "keyframe": shot.keyframe_path,
                    "start_seconds": shot.start_seconds,
                    "duration_seconds": shot.duration_seconds,
                    "output": f"renders/segments/shot_{shot.shot_id:03d}.mp4",
                }
            )

    return {
        "project_slug": project_slug,
        "audio": audio_path,
        "subtitles": subtitles_path,
        "duration_seconds": audio_duration_seconds,
        "segments": segments,
        "outputs": {
            "clean": "renders/final_clean.mp4",
            "with_subtitles": "renders/final_with_subtitles.mp4",
        },
    }


def _validate_unique_shot_ids(shots: list[Shot]):
    seen = set()
    for shot in shots:
        if shot.shot_id in seen:
            raise ValueError(f"Duplicate shot id {shot.shot_id}")
        seen.add(shot.shot_id)
