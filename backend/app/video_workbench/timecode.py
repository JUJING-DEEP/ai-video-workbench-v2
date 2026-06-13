def parse_timecode(value: str) -> float:
    text = value.strip()
    parts = text.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"Invalid timecode: {value}")
    if not all(part.isdigit() for part in parts):
        raise ValueError(f"Invalid timecode: {value}")
    numbers = [int(part) for part in parts]
    if len(numbers) == 2:
        minutes, seconds = numbers
        if seconds >= 60:
            raise ValueError(f"Invalid timecode: {value}")
        return float(minutes * 60 + seconds)
    hours, minutes, seconds = numbers
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Invalid timecode: {value}")
    return float(hours * 3600 + minutes * 60 + seconds)


def format_seconds(value: float) -> str:
    total = int(round(value))
    minutes = total // 60
    seconds = total % 60
    return f"{minutes}:{seconds:02d}"
