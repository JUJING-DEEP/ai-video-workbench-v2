from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from .models import Shot


def generate_srt(shots: list[Shot], language: str = "zh") -> str:
    lines = []
    index = 1
    for shot in sorted(shots, key=_shot_sort_key):
        text = shot.dialogue_zh if language == "zh" else shot.dialogue_en
        if not text:
            continue
        lines.extend(
            [
                str(index),
                f"{_srt_time(shot.start_seconds)} --> {_srt_time(shot.end_seconds)}",
                text,
                "",
            ]
        )
        index += 1
    return "\n".join(lines)


def generate_ass(shots: list[Shot]) -> str:
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H00FFFFFF,&H00000000,&H80000000,-1,0,1,3,1,2,80,80,90,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for shot in sorted(shots, key=_shot_sort_key):
        text = _bilingual_text(shot)
        if not text:
            continue
        events.append(
            f"Dialogue: 0,{_ass_time(shot.start_seconds)},{_ass_time(shot.end_seconds)},Default,,0,0,0,,{text}"
        )
    return header + "\n".join(events) + "\n"


def _bilingual_text(shot: Shot) -> str:
    if shot.dialogue_zh and shot.dialogue_en:
        return f"{_ass_text(shot.dialogue_zh)}\\N{_ass_text(shot.dialogue_en)}"
    return _ass_text(shot.dialogue_zh or shot.dialogue_en)


def _ass_text(text: str) -> str:
    return (
        text.replace("\\", "＼")
        .replace("{", "｛")
        .replace("}", "｝")
        .replace("\r\n", " ")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _srt_time(seconds: float) -> str:
    milliseconds = _round_half_up_units(seconds, 1000)
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    secs = milliseconds // 1000
    millis = milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _ass_time(seconds: float) -> str:
    centiseconds = _round_half_up_units(seconds, 100)
    hours = centiseconds // 360_000
    centiseconds %= 360_000
    minutes = centiseconds // 6_000
    centiseconds %= 6_000
    secs = centiseconds // 100
    cents = centiseconds % 100
    return f"{hours}:{minutes:02d}:{secs:02d}.{cents:02d}"


def _round_half_up_units(seconds: float, units_per_second: int) -> int:
    return int(
        (Decimal(str(seconds)) * units_per_second).to_integral_value(
            rounding=ROUND_HALF_UP
        )
    )


def _shot_sort_key(shot: Shot) -> tuple[float, int]:
    return (shot.start_seconds, shot.shot_id)
