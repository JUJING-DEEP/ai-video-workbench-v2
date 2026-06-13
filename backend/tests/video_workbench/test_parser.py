import pytest

from app.video_workbench.models import ShotKind, ShotMode
from app.video_workbench.parser import parse_storyboard_text


SAMPLE = """
分镜规划信息 (Storyboard Planning)
音频总时长： 538 秒
预计常规图片总数： 约 359 张
预计关键节点数： 10 个
预计分批次数： 约 24 批
每批 15 张
以下是 第 1 批（第 1 张 — 第 15 张） 的定格动画分镜提示词：
————————————————————————
第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）
台词：真相是，你完全被骗了... / The absolute truth is, you have been completely lied to...
--- 提示词 ---
STYLE LOCK — NON-NEGOTIABLE: flat cartoon.
Character Ref: Protagonist.
Scene: The Protagonist is lying in bed.
Mood & Color: Depressing.
————————————————————————
第 2 张图片 ▏时间：0:02 — 0:04 ▏模式：A（垫图叠加）
台词：...关于你为什么凌晨2点37分还醒着... / ...about why you are awake at 2:37 AM...
--- 提示词 ---
STYLE LOCK — NON-NEGOTIABLE: flat cartoon.
Base Image: Use Image 1 as the exact base image. Do not alter any existing elements.
Keep Unchanged: The protagonist in bed.
Add New Element: A massive red stamp.
Mood & Color: Shocking interruption.
————————————————————————
第 10 张图片 ▏时间：0:18 — 0:21 ▏⚡ 关键节点 ⚡
节点类型：[🔥 高潮 1]
画面风格：[极简文字爆破风] (理由：形成视觉震撼)
输出形式：直接图生视频
台词：互联网上每一个所谓的自救大师都会告诉你同样的垃圾废话。 / Every single self-help guru on the internet will tell you the exact same garbage.
--- 图生视频提示词 (I2V) ---
STYLE LOCK: 2D hand-drawn stickman comic style.
Subject Motion: Text slams into view.
Camera: Aggressive camera shake.
————————————————————————
"""


def test_parse_planning_metadata():
    parsed = parse_storyboard_text(SAMPLE)
    assert parsed.planning.audio_duration_seconds == 538
    assert parsed.planning.estimated_regular_images == 359
    assert parsed.planning.estimated_key_nodes == 10
    assert parsed.planning.estimated_batches == 24
    assert parsed.planning.batch_size == 15


def test_parse_mode_b_shot():
    shot = parse_storyboard_text(SAMPLE).shots[0]
    assert shot.shot_id == 1
    assert shot.start_seconds == 0
    assert shot.end_seconds == 2
    assert shot.duration_seconds == 2
    assert shot.kind == ShotKind.IMAGE
    assert shot.mode == ShotMode.MODE_B
    assert shot.dialogue_zh == "真相是，你完全被骗了..."
    assert shot.dialogue_en == "The absolute truth is, you have been completely lied to..."
    assert "Protagonist is lying in bed" in shot.image_prompt


def test_parse_mode_a_dependency():
    shot = parse_storyboard_text(SAMPLE).shots[1]
    assert shot.mode == ShotMode.MODE_A
    assert shot.base_image_shot_id == 1
    assert shot.keep_unchanged == "The protagonist in bed."
    assert shot.add_new_element == "A massive red stamp."


def test_parse_key_node_video():
    shot = parse_storyboard_text(SAMPLE).shots[2]
    assert shot.shot_id == 10
    assert shot.kind == ShotKind.KEY_NODE_VIDEO
    assert shot.mode == ShotMode.KEY_NODE
    assert shot.key_node_type == "🔥 高潮 1"
    assert shot.visual_style == "极简文字爆破风"
    assert shot.output_form == "直接图生视频"
    assert "Subject Motion" in shot.i2v_prompt


def test_key_node_image_prompt_stops_before_i2v_section():
    text = """
第 10 张图片 ▏时间：0:18 — 0:21 ▏⚡ 关键节点 ⚡
节点类型：[🔥 高潮 1]
画面风格：[极简文字爆破风]
输出形式：直接图生视频
台词：爆点来了。 / Here comes the impact.
--- 提示词 ---
STYLE LOCK: flat cartoon.
Scene: Red warning text fills the screen.
--- 图生视频提示词 (I2V) ---
Subject Motion: Text slams into view.
Camera: Aggressive camera shake.
"""
    shot = parse_storyboard_text(text).shots[0]

    assert "Red warning text" in shot.image_prompt
    assert "图生视频提示词" not in shot.image_prompt
    assert "Subject Motion: Text slams into view." in shot.i2v_prompt


def test_storyboardish_text_without_valid_shot_header_raises_value_error():
    text = """
分镜规划信息 (Storyboard Planning)
第 一 张图片 时间：soon 到 later 模式：B
台词：这看起来像分镜，但标题格式坏了。 / This looks storyboard-ish.
"""

    with pytest.raises(ValueError, match="No parseable shot blocks"):
        parse_storyboard_text(text)


def test_adjacent_shots_without_divider_parse_as_separate_blocks():
    text = """
第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）
台词：第一句。 / First line.
--- 提示词 ---
Scene: First shot only.
第 2 张图片 ▏时间：0:02 — 0:04 ▏模式：B（全新构图）
台词：第二句。 / Second line.
--- 提示词 ---
Scene: Second shot only.
"""

    parsed = parse_storyboard_text(text)

    assert [shot.shot_id for shot in parsed.shots] == [1, 2]
    assert "First shot only" in parsed.shots[0].image_prompt
    assert "第 2 张图片" not in parsed.shots[0].image_prompt
    assert "Second shot only" in parsed.shots[1].image_prompt
