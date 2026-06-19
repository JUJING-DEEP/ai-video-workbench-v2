from __future__ import annotations

import re

from .models import ParsedStoryboard, ProjectPlanning, Shot, ShotKind, ShotMode
from .timecode import parse_timecode

DIVIDER_RE = re.compile(r"—{8,}")
SHOT_HEADER_RE = re.compile(
    r"第\s*(\d+)\s*张图片\s*▏时间：\s*([0-9:]+)\s*[—-]\s*([0-9:]+)(.*)"
)
SECTION_MARKERS = ("--- 提示词 ---", "--- 图生视频提示词 (I2V) ---")
STORYBOARD_HINTS = ("张图片", "时间：")


def parse_storyboard_text(text: str) -> ParsedStoryboard:
    planning = _parse_planning(text)
    blocks = _split_shot_blocks(text)
    if not blocks and _looks_storyboardish(text):
        raise ValueError("No parseable shot blocks found in storyboard text")
    shots = [_parse_shot_block(block) for block in blocks]
    return ParsedStoryboard(planning=planning, shots=shots, raw_batches=[text])


def _split_shot_blocks(text: str) -> list[str]:
    headers = list(SHOT_HEADER_RE.finditer(text))
    blocks = []
    for index, header in enumerate(headers):
        end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
        block = text[header.start() : end].strip()
        block = DIVIDER_RE.sub("", block).strip()
        if block:
            blocks.append(block)
    return blocks


def _looks_storyboardish(text: str) -> bool:
    return any(hint in text for hint in STORYBOARD_HINTS)


def _parse_planning(text: str) -> ProjectPlanning:
    return ProjectPlanning(
        audio_duration_seconds=_first_number(text, r"音频总时长：\s*([0-9]+)\s*秒"),
        estimated_regular_images=_first_number(
            text, r"预计常规图片总数：\s*约?\s*([0-9]+)\s*张"
        ),
        estimated_key_nodes=_first_number(text, r"预计关键节点数：\s*([0-9]+)\s*个"),
        estimated_batches=_first_number(text, r"预计分批次数：\s*约?\s*([0-9]+)\s*批"),
        batch_size=_first_number(text, r"每批\s*([0-9]+)\s*张"),
    )


def _first_number(text: str, pattern: str):
    match = re.search(pattern, text)
    return int(match.group(1)) if match else None


def _parse_shot_block(block: str) -> Shot:
    header = SHOT_HEADER_RE.search(block)
    if not header:
        raise ValueError(f"Cannot parse shot header: {block[:120]}")

    shot_id = int(header.group(1))
    start = parse_timecode(header.group(2))
    end = parse_timecode(header.group(3))
    suffix = header.group(4)
    is_key_node = "关键节点" in suffix or "关键节点" in block
    mode = _parse_mode(suffix, is_key_node)
    kind = ShotKind.KEY_NODE_VIDEO if is_key_node else ShotKind.IMAGE
    dialogue_zh, dialogue_en = _parse_dialogue(block)
    image_prompt = _section_after(block, "--- 提示词 ---")
    i2v_prompt = _section_after(block, "--- 图生视频提示词 (I2V) ---")
    base_image_shot_id = _parse_base_image(image_prompt)

    return Shot(
        shot_id=shot_id,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=end - start,
        kind=kind,
        mode=mode,
        dialogue_zh=dialogue_zh,
        dialogue_en=dialogue_en,
        image_prompt=image_prompt,
        i2v_prompt=i2v_prompt,
        key_node_type=_bracket_value(block, "节点类型"),
        visual_style=_bracket_value(block, "画面风格"),
        output_form=_line_value(block, "输出形式"),
        base_image_shot_id=base_image_shot_id,
        keep_unchanged=_line_value(image_prompt, "Keep Unchanged"),
        add_new_element=_line_value(image_prompt, "Add New Element"),
    )


def _parse_mode(header_suffix: str, is_key_node: bool) -> ShotMode:
    if is_key_node:
        return ShotMode.KEY_NODE
    if "模式：A" in header_suffix:
        return ShotMode.MODE_A
    return ShotMode.MODE_B


def _parse_dialogue(block: str) -> tuple[str, str]:
    value = _line_value(block, "台词")
    if " / " in value:
        zh, en = value.split(" / ", 1)
        return zh.strip(), en.strip()
    return value.strip(), ""


def _section_after(block: str, marker: str) -> str:
    if marker not in block:
        return ""
    content = block.split(marker, 1)[1]
    end = len(content)
    for next_marker in SECTION_MARKERS:
        if next_marker == marker:
            continue
        marker_index = content.find(next_marker)
        if marker_index != -1:
            end = min(end, marker_index)
    return DIVIDER_RE.sub("", content[:end]).strip()


def _parse_base_image(prompt: str):
    match = re.search(r"Base Image:\s*Use Image\s+([0-9]+)", prompt)
    return int(match.group(1)) if match else None


def _line_value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[：:]\s*(.+)", text)
    return match.group(1).strip() if match else ""


def _bracket_value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[：:]\s*\[([^\]]+)\]", text)
    return match.group(1).strip() if match else ""
