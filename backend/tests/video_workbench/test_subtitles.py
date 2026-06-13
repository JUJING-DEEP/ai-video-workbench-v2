from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.subtitles import generate_ass, generate_srt


def test_generate_chinese_srt():
    shots = [
        Shot(
            1,
            0,
            2,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="真相是，你完全被骗了...",
        ),
        Shot(
            2,
            2,
            4,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="无法放下手机。",
        ),
    ]

    srt = generate_srt(shots, language="zh")

    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "真相是，你完全被骗了..." in srt
    assert "无法放下手机。" in srt


def test_generate_bilingual_ass():
    shots = [
        Shot(
            1,
            0,
            2,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="真相是，你完全被骗了...",
            dialogue_en="You have been lied to.",
        )
    ]

    ass = generate_ass(shots)

    assert "[V4+ Styles]" in ass
    assert "真相是，你完全被骗了...\\NYou have been lied to." in ass


def test_generate_ass_escapes_dialogue_text():
    shots = [
        Shot(
            1,
            0,
            2,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="包含 {tag} 和 literal\\N\n换行",
            dialogue_en="English {tag} literal\\N",
        )
    ]

    ass = generate_ass(shots)
    dialogue_lines = [
        line for line in ass.splitlines() if line.startswith("Dialogue:")
    ]

    assert len(dialogue_lines) == 1
    assert "{tag}" not in dialogue_lines[0]
    assert "literal\\N" not in dialogue_lines[0]
    assert "包含" in dialogue_lines[0]
    assert "换行" in dialogue_lines[0]
    assert dialogue_lines[0].count("\\N") == 1


def test_generate_srt_uses_half_up_millisecond_rounding():
    shots = [
        Shot(
            1,
            0,
            1.2345,
            1.2345,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="中点进位",
        )
    ]

    srt = generate_srt(shots, language="zh")

    assert "00:00:00,000 --> 00:00:01,235" in srt


def test_generate_srt_orders_same_start_by_shot_id():
    shots = [
        Shot(
            2,
            0,
            2,
            2,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="第二条",
        ),
        Shot(
            1,
            0,
            1,
            1,
            ShotKind.IMAGE,
            ShotMode.MODE_B,
            dialogue_zh="第一条",
        ),
    ]

    srt = generate_srt(shots, language="zh")

    assert srt.index("第一条") < srt.index("第二条")
