import pytest

from app.video_workbench.timecode import format_seconds, parse_timecode


def test_parse_minute_second_timecode():
    assert parse_timecode("3:44") == 224.0
    assert parse_timecode("8:58") == 538.0


def test_parse_hour_minute_second_timecode():
    assert parse_timecode("1:02:03") == 3723.0


def test_parse_timecode_rejects_invalid_text():
    with pytest.raises(ValueError, match="Invalid timecode"):
        parse_timecode("soon")


def test_parse_timecode_rejects_out_of_range_seconds():
    with pytest.raises(ValueError, match="Invalid timecode"):
        parse_timecode("1:99")


def test_parse_timecode_rejects_out_of_range_hour_minutes():
    with pytest.raises(ValueError, match="Invalid timecode"):
        parse_timecode("1:99:00")


def test_format_seconds_outputs_minute_second_text():
    assert format_seconds(224) == "3:44"
    assert format_seconds(538.2) == "8:58"
