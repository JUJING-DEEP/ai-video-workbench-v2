import json
from pathlib import Path

from app.video_workbench.parser import parse_storyboard_text


def test_coffee_commercial_demo_fixture_matches_current_workflow():
    fixture_path = Path(__file__).resolve().parents[3] / "demo" / "coffee-commercial.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    parsed = parse_storyboard_text(fixture["storyboard_text"])
    shot_ids = [shot.shot_id for shot in parsed.shots]

    assert fixture["project"]["title"] == "Coffee Commercial Demo"
    assert shot_ids == [1, 2, 3]
    assert [shot["shot_id"] for shot in fixture["shots"]] == shot_ids
    assert [item["shot_id"] for item in fixture["timeline"]] == shot_ids
    assert [item["shot_id"] for item in fixture["render_plan"]["items"]] == shot_ids
    assert all(item["video_path"] for item in fixture["render_plan"]["items"])
