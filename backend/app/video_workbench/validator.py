from __future__ import annotations

from .models import Shot, ShotKind, ShotMode


def validate_project(
    shots: list[Shot],
    audio_duration_seconds: float | None,
    tolerance: float = 0.25,
) -> dict:
    issues = []
    sorted_shots = sorted(shots, key=lambda shot: shot.start_seconds)
    by_id = {shot.shot_id: shot for shot in sorted_shots}

    _check_duplicate_ids(sorted_shots, issues)
    _check_shot_durations(sorted_shots, issues, tolerance)
    _check_time_continuity(sorted_shots, issues, tolerance)
    _check_assets(sorted_shots, by_id, issues)
    _check_audio_end(sorted_shots, audio_duration_seconds, issues, tolerance)

    return {"render_ready": len(issues) == 0, "issues": issues}


def _check_duplicate_ids(shots: list[Shot], issues: list[dict]):
    seen = set()
    for shot in shots:
        if shot.shot_id in seen:
            issues.append(
                {
                    "code": "duplicate_shot_id",
                    "shot_id": shot.shot_id,
                    "message": f"Duplicate shot id {shot.shot_id}",
                }
            )
        seen.add(shot.shot_id)


def _check_shot_durations(shots: list[Shot], issues: list[dict], tolerance: float):
    for shot in shots:
        expected_duration = shot.end_seconds - shot.start_seconds
        if shot.end_seconds <= shot.start_seconds:
            issues.append(
                {
                    "code": "invalid_duration",
                    "shot_id": shot.shot_id,
                    "message": (
                        f"Shot {shot.shot_id} end must be greater than start"
                    ),
                }
            )
        if abs(shot.duration_seconds - expected_duration) > tolerance:
            issues.append(
                {
                    "code": "duration_mismatch",
                    "shot_id": shot.shot_id,
                    "message": (
                        f"Shot {shot.shot_id} duration is "
                        f"{shot.duration_seconds:.2f}s but timeline spans "
                        f"{expected_duration:.2f}s"
                    ),
                }
            )


def _check_time_continuity(shots: list[Shot], issues: list[dict], tolerance: float):
    if shots and shots[0].start_seconds > tolerance:
        issues.append(
            {
                "code": "initial_time_gap",
                "shot_id": shots[0].shot_id,
                "message": f"Gap before shot {shots[0].shot_id}",
            }
        )
    for previous, current in zip(shots, shots[1:]):
        if current.start_seconds > previous.end_seconds + tolerance:
            issues.append(
                {
                    "code": "time_gap",
                    "shot_id": current.shot_id,
                    "message": f"Gap before shot {current.shot_id}",
                }
            )
        if current.start_seconds < previous.end_seconds - tolerance:
            issues.append(
                {
                    "code": "time_overlap",
                    "shot_id": current.shot_id,
                    "message": f"Overlap before shot {current.shot_id}",
                }
            )


def _check_assets(shots: list[Shot], by_id: dict[int, Shot], issues: list[dict]):
    for shot in shots:
        if shot.kind == ShotKind.IMAGE and not shot.image_path:
            issues.append(
                {
                    "code": "missing_image",
                    "shot_id": shot.shot_id,
                    "message": f"Shot {shot.shot_id} needs an image",
                }
            )
        if shot.kind == ShotKind.KEY_NODE_VIDEO:
            if not shot.keyframe_path:
                issues.append(
                    {
                        "code": "missing_keyframe",
                        "shot_id": shot.shot_id,
                        "message": f"Shot {shot.shot_id} needs a keyframe",
                    }
                )
            if not shot.video_path:
                issues.append(
                    {
                        "code": "missing_video",
                        "shot_id": shot.shot_id,
                        "message": f"Shot {shot.shot_id} needs a video",
                    }
                )
        if shot.mode == ShotMode.MODE_A:
            base = by_id.get(shot.base_image_shot_id or -1)
            if base is None or not base.image_path:
                issues.append(
                    {
                        "code": "missing_base_image",
                        "shot_id": shot.shot_id,
                        "message": (
                            f"Shot {shot.shot_id} needs base image "
                            f"{shot.base_image_shot_id}"
                        ),
                    }
                )


def _check_audio_end(
    shots: list[Shot],
    audio_duration_seconds: float | None,
    issues: list[dict],
    tolerance: float,
):
    if audio_duration_seconds is None or not shots:
        return
    final_end = max(shot.end_seconds for shot in shots)
    if abs(final_end - audio_duration_seconds) > tolerance:
        issues.append(
            {
                "code": "audio_timeline_mismatch",
                "shot_id": None,
                "message": (
                    f"Timeline ends at {final_end:.2f}s but audio is "
                    f"{audio_duration_seconds:.2f}s"
                ),
            }
        )
