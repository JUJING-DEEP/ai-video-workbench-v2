# AI Video Production Workbench MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Phase 1 local workbench MVP for importing AI Studio storyboard text, managing shot assets, validating audio/video/subtitle alignment, and exporting render-ready artifacts.

**Architecture:** Add a separate video-workbench domain to the existing FastAPI backend and Vue frontend. The backend owns parsing, project persistence, validation, subtitle generation, and render-plan generation; the frontend provides the local workbench UI for importing storyboard batches, reviewing shots, binding assets, and triggering validation/render preparation.

**Tech Stack:** Python 3, FastAPI, SQLite, pytest, Vue 3, Vue Router, Vitest, FFmpeg/ffprobe via subprocess wrappers.

---

## Scope

This plan implements Phase 1 only:

- Project creation.
- Storyboard parsing.
- Shot database.
- Timeline UI.
- Prompt package export.
- Asset import and matching.
- Validation reports.
- Subtitle generation.
- Audio, video, and subtitle aligned render-plan generation.

This plan does not implement browser automation for Google AI Studio, Nano banana, or Jimeng. Those agents should be planned separately after the local workbench MVP is usable.

## File Structure

Create backend domain files:

- `backend/app/video_workbench/__init__.py` exports the package.
- `backend/app/video_workbench/models.py` defines dataclasses/enums used by parser, repository, validator, and renderer.
- `backend/app/video_workbench/timecode.py` parses and formats storyboard timecodes.
- `backend/app/video_workbench/parser.py` parses AI Studio planning, batch, and shot text.
- `backend/app/video_workbench/repository.py` owns SQLite schema and CRUD for video projects and shots.
- `backend/app/video_workbench/storage.py` owns project directory creation, prompt exports, and asset path rules.
- `backend/app/video_workbench/validator.py` checks gaps, overlaps, duplicate shots, dependencies, missing assets, and alignment readiness.
- `backend/app/video_workbench/subtitles.py` generates SRT and ASS subtitle files.
- `backend/app/video_workbench/render_plan.py` builds a render plan from shots, assets, subtitles, and audio duration.
- `backend/app/video_workbench/media_probe.py` wraps ffprobe and audio/video duration probing.
- `backend/app/video_workbench/api.py` exposes FastAPI routes under `/api/video-workbench`.

Create backend tests:

- `backend/tests/video_workbench/test_timecode.py`
- `backend/tests/video_workbench/test_parser.py`
- `backend/tests/video_workbench/test_repository.py`
- `backend/tests/video_workbench/test_storage.py`
- `backend/tests/video_workbench/test_validator.py`
- `backend/tests/video_workbench/test_subtitles.py`
- `backend/tests/video_workbench/test_render_plan.py`
- `backend/tests/video_workbench/test_api.py`

Modify backend files:

- `backend/requirements.txt` adds runtime and test dependencies.
- `backend/app/main.py` includes the video-workbench router.

Create frontend files:

- `frontend/src/services/videoWorkbenchApi.js` wraps workbench API calls.
- `frontend/src/views/VideoWorkbench.vue` is the main local workbench screen.
- `frontend/src/components/video-workbench/ProjectSetupPanel.vue`
- `frontend/src/components/video-workbench/StoryboardImportPanel.vue`
- `frontend/src/components/video-workbench/ShotTimeline.vue`
- `frontend/src/components/video-workbench/ShotDetailPanel.vue`
- `frontend/src/components/video-workbench/ValidationPanel.vue`
- `frontend/src/components/video-workbench/AssetImportPanel.vue`
- `frontend/src/components/video-workbench/RenderPanel.vue`
- `frontend/src/components/video-workbench/__tests__/ShotTimeline.spec.js`
- `frontend/src/components/video-workbench/__tests__/ValidationPanel.spec.js`

Modify frontend files:

- `frontend/src/router/index.js` adds `/video-workbench`.
- `frontend/src/style.css` or `frontend/src/styles/theme.css` adds workbench layout styles only if existing component-scoped styles are insufficient.

---

### Task 1: Backend Test Harness And Dependencies

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/video_workbench/__init__.py`

- [ ] **Step 1: Add backend dependencies**

Replace `backend/requirements.txt` with:

```text
fastapi==0.115.6
uvicorn==0.32.1
pydantic==2.10.3
python-multipart==0.0.19
pytest==8.3.4
httpx==0.28.1
```

- [ ] **Step 2: Create pytest fixtures**

Create `backend/tests/conftest.py`:

```python
import os
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def temp_db_path(tmp_path):
    return tmp_path / "video_workbench_test.db"


@pytest.fixture()
def temp_projects_root(tmp_path):
    root = tmp_path / "video_projects"
    root.mkdir()
    return root


@pytest.fixture()
def sqlite_conn(temp_db_path):
    conn = sqlite3.connect(temp_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()
```

Create an empty package marker at `backend/tests/video_workbench/__init__.py`.

- [ ] **Step 3: Run pytest collection**

Run: `cd backend && python -m pytest --collect-only`

Expected: pytest runs and reports no collected tests or only existing tests. It must not fail with missing dependency or import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt backend/tests/conftest.py backend/tests/video_workbench/__init__.py
git commit -m "test: add backend test harness"
```

---

### Task 2: Domain Models And Timecode Utilities

**Files:**
- Create: `backend/app/video_workbench/__init__.py`
- Create: `backend/app/video_workbench/models.py`
- Create: `backend/app/video_workbench/timecode.py`
- Test: `backend/tests/video_workbench/test_timecode.py`

- [ ] **Step 1: Write failing timecode tests**

Create `backend/tests/video_workbench/test_timecode.py`:

```python
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


def test_format_seconds_outputs_minute_second_text():
    assert format_seconds(224) == "3:44"
    assert format_seconds(538.2) == "8:58"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_timecode.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'app.video_workbench'`.

- [ ] **Step 3: Create models**

Create `backend/app/video_workbench/__init__.py`:

```python
"""Video production workbench domain."""
```

Create `backend/app/video_workbench/models.py`:

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ShotKind(str, Enum):
    IMAGE = "image"
    KEY_NODE_VIDEO = "key_node_video"


class ShotMode(str, Enum):
    MODE_A = "A"
    MODE_B = "B"
    KEY_NODE = "KEY_NODE"


class ShotStatus(str, Enum):
    PARSED = "parsed"
    WAITING_FOR_BASE_IMAGE = "waiting_for_base_image"
    IMAGE_PENDING = "image_pending"
    IMAGE_READY = "image_ready"
    IMAGE_FAILED = "image_failed"
    KEYFRAME_PENDING = "keyframe_pending"
    KEYFRAME_READY = "keyframe_ready"
    VIDEO_PENDING = "video_pending"
    VIDEO_READY = "video_ready"
    VIDEO_FAILED = "video_failed"
    APPROVED = "approved"
    IN_RENDER_PLAN = "in_render_plan"
    RENDERED = "rendered"


@dataclass
class ProjectPlanning:
    audio_duration_seconds: Optional[float] = None
    estimated_regular_images: Optional[int] = None
    estimated_key_nodes: Optional[int] = None
    estimated_batches: Optional[int] = None
    batch_size: Optional[int] = None


@dataclass
class Shot:
    shot_id: int
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    kind: ShotKind
    mode: ShotMode
    dialogue_zh: str = ""
    dialogue_en: str = ""
    image_prompt: str = ""
    i2v_prompt: str = ""
    batch_number: Optional[int] = None
    key_node_type: str = ""
    visual_style: str = ""
    output_form: str = ""
    base_image_shot_id: Optional[int] = None
    keep_unchanged: str = ""
    add_new_element: str = ""
    status: ShotStatus = ShotStatus.PARSED
    image_path: str = ""
    keyframe_path: str = ""
    video_path: str = ""
    review_notes: str = ""
    error_message: str = ""


@dataclass
class ParsedStoryboard:
    planning: ProjectPlanning = field(default_factory=ProjectPlanning)
    shots: list[Shot] = field(default_factory=list)
    raw_batches: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Implement timecode utilities**

Create `backend/app/video_workbench/timecode.py`:

```python
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
        return float(minutes * 60 + seconds)
    hours, minutes, seconds = numbers
    return float(hours * 3600 + minutes * 60 + seconds)


def format_seconds(value: float) -> str:
    total = int(round(value))
    minutes = total // 60
    seconds = total % 60
    return f"{minutes}:{seconds:02d}"
```

- [ ] **Step 5: Run tests to verify pass**

Run: `cd backend && python -m pytest tests/video_workbench/test_timecode.py -v`

Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/video_workbench/__init__.py backend/app/video_workbench/models.py backend/app/video_workbench/timecode.py backend/tests/video_workbench/test_timecode.py
git commit -m "feat: add video workbench domain models"
```

---

### Task 3: Storyboard Parser

**Files:**
- Create: `backend/app/video_workbench/parser.py`
- Test: `backend/tests/video_workbench/test_parser.py`

- [ ] **Step 1: Write parser tests with real-format samples**

Create `backend/tests/video_workbench/test_parser.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_parser.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `parser`.

- [ ] **Step 3: Implement parser**

Create `backend/app/video_workbench/parser.py`:

```python
import re

from .models import ParsedStoryboard, ProjectPlanning, Shot, ShotKind, ShotMode
from .timecode import parse_timecode

DIVIDER_RE = re.compile(r"—{8,}")
SHOT_HEADER_RE = re.compile(r"第\s*(\d+)\s*张图片\s*▏时间：\s*([0-9:]+)\s*[—-]\s*([0-9:]+)(.*)")


def parse_storyboard_text(text: str) -> ParsedStoryboard:
    planning = _parse_planning(text)
    blocks = [block.strip() for block in DIVIDER_RE.split(text) if "第" in block and "张图片" in block]
    shots = [_parse_shot_block(block) for block in blocks]
    return ParsedStoryboard(planning=planning, shots=shots, raw_batches=[text])


def _parse_planning(text: str) -> ProjectPlanning:
    return ProjectPlanning(
        audio_duration_seconds=_first_number(text, r"音频总时长：\s*([0-9]+)\s*秒"),
        estimated_regular_images=_first_number(text, r"预计常规图片总数：\s*约?\s*([0-9]+)\s*张"),
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
    content = block.split(marker, 1)[1].strip()
    return content


def _parse_base_image(prompt: str):
    match = re.search(r"Base Image:\s*Use Image\s+([0-9]+)", prompt)
    return int(match.group(1)) if match else None


def _line_value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[：:]\s*(.+)", text)
    return match.group(1).strip() if match else ""


def _bracket_value(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}[：:]\s*\[([^\]]+)\]", text)
    return match.group(1).strip() if match else ""
```

- [ ] **Step 4: Run parser tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_parser.py -v`

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/video_workbench/parser.py backend/tests/video_workbench/test_parser.py
git commit -m "feat: parse ai studio storyboards"
```

---

### Task 4: Repository And SQLite Schema

**Files:**
- Create: `backend/app/video_workbench/repository.py`
- Test: `backend/tests/video_workbench/test_repository.py`

- [ ] **Step 1: Write repository tests**

Create `backend/tests/video_workbench/test_repository.py`:

```python
from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.repository import VideoWorkbenchRepository


def test_create_project_and_list_projects(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()
    project = repo.create_project(
        title="Sleep Video",
        role_card="Protagonist role",
        audio_path="audio/voiceover.wav",
        audio_duration_seconds=538,
    )
    projects = repo.list_projects()
    assert projects[0]["id"] == project["id"]
    assert projects[0]["title"] == "Sleep Video"
    assert projects[0]["audio_duration_seconds"] == 538


def test_replace_project_shots_and_fetch(temp_db_path, temp_projects_root):
    repo = VideoWorkbenchRepository(temp_db_path, temp_projects_root)
    repo.init_schema()
    project = repo.create_project("Sleep Video", "", "", None)
    repo.replace_project_shots(project["id"], [
        Shot(
            shot_id=1,
            start_seconds=0,
            end_seconds=2,
            duration_seconds=2,
            kind=ShotKind.IMAGE,
            mode=ShotMode.MODE_B,
            dialogue_zh="真相是，你完全被骗了...",
            image_prompt="Scene: bed",
        )
    ])
    shots = repo.get_project_shots(project["id"])
    assert len(shots) == 1
    assert shots[0].shot_id == 1
    assert shots[0].dialogue_zh == "真相是，你完全被骗了..."
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_repository.py -v`

Expected: FAIL with missing `repository`.

- [ ] **Step 3: Implement repository**

Create `backend/app/video_workbench/repository.py`:

```python
import sqlite3
from pathlib import Path

from .models import Shot, ShotKind, ShotMode, ShotStatus


class VideoWorkbenchRepository:
    def __init__(self, db_path: str | Path, projects_root: str | Path):
        self.db_path = Path(db_path)
        self.projects_root = Path(projects_root)

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_schema(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    role_card TEXT DEFAULT '',
                    audio_path TEXT DEFAULT '',
                    audio_duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS video_shots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    shot_id INTEGER NOT NULL,
                    batch_number INTEGER,
                    start_seconds REAL NOT NULL,
                    end_seconds REAL NOT NULL,
                    duration_seconds REAL NOT NULL,
                    kind TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    dialogue_zh TEXT DEFAULT '',
                    dialogue_en TEXT DEFAULT '',
                    image_prompt TEXT DEFAULT '',
                    i2v_prompt TEXT DEFAULT '',
                    base_image_shot_id INTEGER,
                    keep_unchanged TEXT DEFAULT '',
                    add_new_element TEXT DEFAULT '',
                    key_node_type TEXT DEFAULT '',
                    visual_style TEXT DEFAULT '',
                    output_form TEXT DEFAULT '',
                    status TEXT NOT NULL,
                    image_path TEXT DEFAULT '',
                    keyframe_path TEXT DEFAULT '',
                    video_path TEXT DEFAULT '',
                    review_notes TEXT DEFAULT '',
                    error_message TEXT DEFAULT '',
                    UNIQUE(project_id, shot_id)
                )
            """)

    def create_project(self, title: str, role_card: str, audio_path: str, audio_duration_seconds: float | None):
        slug = _slugify(title)
        self.projects_root.mkdir(parents=True, exist_ok=True)
        (self.projects_root / slug).mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO video_projects (title, slug, role_card, audio_path, audio_duration_seconds)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, slug, role_card, audio_path, audio_duration_seconds),
            )
            project_id = cursor.lastrowid
        return self.get_project(project_id)

    def list_projects(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM video_projects ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]

    def get_project(self, project_id: int):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM video_projects WHERE id = ?", (project_id,)).fetchone()
        if row is None:
            raise KeyError(f"Project not found: {project_id}")
        return dict(row)

    def replace_project_shots(self, project_id: int, shots: list[Shot]):
        with self._connect() as conn:
            conn.execute("DELETE FROM video_shots WHERE project_id = ?", (project_id,))
            conn.executemany(
                """
                INSERT INTO video_shots (
                    project_id, shot_id, batch_number, start_seconds, end_seconds, duration_seconds,
                    kind, mode, dialogue_zh, dialogue_en, image_prompt, i2v_prompt, base_image_shot_id,
                    keep_unchanged, add_new_element, key_node_type, visual_style, output_form, status,
                    image_path, keyframe_path, video_path, review_notes, error_message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._shot_values(project_id, shot) for shot in shots],
            )

    def get_project_shots(self, project_id: int) -> list[Shot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM video_shots WHERE project_id = ? ORDER BY shot_id",
                (project_id,),
            ).fetchall()
        return [self._row_to_shot(row) for row in rows]

    def bind_asset(self, project_id: int, shot_id: int, asset_type: str, path: str):
        column = {"image": "image_path", "keyframe": "keyframe_path", "video": "video_path"}[asset_type]
        status = {"image": ShotStatus.IMAGE_READY.value, "keyframe": ShotStatus.KEYFRAME_READY.value, "video": ShotStatus.VIDEO_READY.value}[asset_type]
        with self._connect() as conn:
            conn.execute(
                f"UPDATE video_shots SET {column} = ?, status = ? WHERE project_id = ? AND shot_id = ?",
                (path, status, project_id, shot_id),
            )

    def _shot_values(self, project_id: int, shot: Shot):
        return (
            project_id, shot.shot_id, shot.batch_number, shot.start_seconds, shot.end_seconds,
            shot.duration_seconds, shot.kind.value, shot.mode.value, shot.dialogue_zh,
            shot.dialogue_en, shot.image_prompt, shot.i2v_prompt, shot.base_image_shot_id,
            shot.keep_unchanged, shot.add_new_element, shot.key_node_type, shot.visual_style,
            shot.output_form, shot.status.value, shot.image_path, shot.keyframe_path,
            shot.video_path, shot.review_notes, shot.error_message,
        )

    def _row_to_shot(self, row) -> Shot:
        return Shot(
            shot_id=row["shot_id"],
            batch_number=row["batch_number"],
            start_seconds=row["start_seconds"],
            end_seconds=row["end_seconds"],
            duration_seconds=row["duration_seconds"],
            kind=ShotKind(row["kind"]),
            mode=ShotMode(row["mode"]),
            dialogue_zh=row["dialogue_zh"],
            dialogue_en=row["dialogue_en"],
            image_prompt=row["image_prompt"],
            i2v_prompt=row["i2v_prompt"],
            base_image_shot_id=row["base_image_shot_id"],
            keep_unchanged=row["keep_unchanged"],
            add_new_element=row["add_new_element"],
            key_node_type=row["key_node_type"],
            visual_style=row["visual_style"],
            output_form=row["output_form"],
            status=ShotStatus(row["status"]),
            image_path=row["image_path"],
            keyframe_path=row["keyframe_path"],
            video_path=row["video_path"],
            review_notes=row["review_notes"],
            error_message=row["error_message"],
        )


def _slugify(title: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in title).strip("-")
    return cleaned or "video-project"
```

- [ ] **Step 4: Run repository tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_repository.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/video_workbench/repository.py backend/tests/video_workbench/test_repository.py
git commit -m "feat: persist video workbench projects"
```

---

### Task 5: Project Storage And Prompt Package Export

**Files:**
- Create: `backend/app/video_workbench/storage.py`
- Test: `backend/tests/video_workbench/test_storage.py`

- [ ] **Step 1: Write storage tests**

Create `backend/tests/video_workbench/test_storage.py`:

```python
from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.storage import ProjectStorage


def test_create_project_directories(temp_projects_root):
    storage = ProjectStorage(temp_projects_root)
    paths = storage.ensure_project_dirs("sleep-video")
    assert paths["audio"].is_dir()
    assert paths["prompts_nano_images"].is_dir()
    assert paths["assets_videos"].is_dir()
    assert paths["renders"].is_dir()


def test_export_prompt_packages(temp_projects_root):
    storage = ProjectStorage(temp_projects_root)
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B, image_prompt="Prompt image 1"),
        Shot(2, 2, 4, 2, ShotKind.IMAGE, ShotMode.MODE_A, image_prompt="Prompt image 2", base_image_shot_id=1),
        Shot(10, 18, 21, 3, ShotKind.KEY_NODE_VIDEO, ShotMode.KEY_NODE, i2v_prompt="Prompt video 10"),
    ]
    files = storage.export_prompt_packages("sleep-video", shots)
    assert files["nano_images"].exists()
    assert files["nano_keyframes"].exists()
    assert files["jimeng_i2v"].exists()
    assert "shot_001_image.png" in files["nano_images"].read_text()
    assert "shot_010_keyframe.png" in files["nano_keyframes"].read_text()
    assert "shot_010_video.mp4" in files["jimeng_i2v"].read_text()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_storage.py -v`

Expected: FAIL with missing `storage`.

- [ ] **Step 3: Implement storage**

Create `backend/app/video_workbench/storage.py`:

```python
from pathlib import Path

from .models import Shot, ShotKind, ShotMode


class ProjectStorage:
    def __init__(self, projects_root: str | Path):
        self.projects_root = Path(projects_root)

    def project_dir(self, slug: str) -> Path:
        return self.projects_root / slug

    def ensure_project_dirs(self, slug: str) -> dict[str, Path]:
        root = self.project_dir(slug)
        paths = {
            "root": root,
            "audio": root / "audio",
            "prompts": root / "prompts",
            "prompts_nano_images": root / "prompts" / "nano_images",
            "prompts_nano_keyframes": root / "prompts" / "nano_keyframes",
            "prompts_jimeng_i2v": root / "prompts" / "jimeng_i2v",
            "assets": root / "assets",
            "assets_images": root / "assets" / "images",
            "assets_keyframes": root / "assets" / "keyframes",
            "assets_videos": root / "assets" / "videos",
            "subtitles": root / "subtitles",
            "renders": root / "renders",
            "reports": root / "reports",
        }
        for path in paths.values():
            path.mkdir(parents=True, exist_ok=True)
        return paths

    def export_prompt_packages(self, slug: str, shots: list[Shot]) -> dict[str, Path]:
        paths = self.ensure_project_dirs(slug)
        nano_images = paths["prompts_nano_images"] / "tasks.md"
        nano_keyframes = paths["prompts_nano_keyframes"] / "tasks.md"
        jimeng_i2v = paths["prompts_jimeng_i2v"] / "tasks.md"

        nano_image_lines = []
        nano_keyframe_lines = []
        jimeng_lines = []

        for shot in shots:
            if shot.kind == ShotKind.IMAGE:
                output = f"shot_{shot.shot_id:03d}_image.png"
                dependency = f"\nBase Image: shot_{shot.base_image_shot_id:03d}_image.png" if shot.mode == ShotMode.MODE_A and shot.base_image_shot_id else ""
                nano_image_lines.append(f"## Shot {shot.shot_id:03d}\nOutput: {output}{dependency}\nDuration: {shot.duration_seconds:.2f}s\n\n{shot.image_prompt}\n")
            if shot.kind == ShotKind.KEY_NODE_VIDEO:
                keyframe = f"shot_{shot.shot_id:03d}_keyframe.png"
                video = f"shot_{shot.shot_id:03d}_video.mp4"
                nano_keyframe_lines.append(f"## Shot {shot.shot_id:03d}\nOutput: {keyframe}\nDuration: {shot.duration_seconds:.2f}s\n\n{shot.image_prompt or shot.i2v_prompt}\n")
                jimeng_lines.append(f"## Shot {shot.shot_id:03d}\nKeyframe: {keyframe}\nOutput: {video}\nDuration: {shot.duration_seconds:.2f}s\n\n{shot.i2v_prompt}\n")

        nano_images.write_text("\n".join(nano_image_lines), encoding="utf-8")
        nano_keyframes.write_text("\n".join(nano_keyframe_lines), encoding="utf-8")
        jimeng_i2v.write_text("\n".join(jimeng_lines), encoding="utf-8")

        return {"nano_images": nano_images, "nano_keyframes": nano_keyframes, "jimeng_i2v": jimeng_i2v}
```

- [ ] **Step 4: Run storage tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_storage.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/video_workbench/storage.py backend/tests/video_workbench/test_storage.py
git commit -m "feat: export video prompt packages"
```

---

### Task 6: Validation Reports

**Files:**
- Create: `backend/app/video_workbench/validator.py`
- Test: `backend/tests/video_workbench/test_validator.py`

- [ ] **Step 1: Write validator tests**

Create `backend/tests/video_workbench/test_validator.py`:

```python
from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.validator import validate_project


def test_validator_detects_time_gap_and_missing_asset():
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B),
        Shot(2, 3, 4, 1, ShotKind.IMAGE, ShotMode.MODE_B),
    ]
    report = validate_project(shots, audio_duration_seconds=4)
    codes = {issue["code"] for issue in report["issues"]}
    assert "time_gap" in codes
    assert "missing_image" in codes
    assert report["render_ready"] is False


def test_validator_accepts_complete_image_timeline():
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B, image_path="assets/images/shot_001_image.png"),
        Shot(2, 2, 4, 2, ShotKind.IMAGE, ShotMode.MODE_B, image_path="assets/images/shot_002_image.png"),
    ]
    report = validate_project(shots, audio_duration_seconds=4)
    assert report["issues"] == []
    assert report["render_ready"] is True


def test_validator_detects_mode_a_missing_base_image():
    shots = [
        Shot(2, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_A, base_image_shot_id=1, image_path="assets/images/shot_002_image.png"),
    ]
    report = validate_project(shots, audio_duration_seconds=2)
    assert report["issues"][0]["code"] == "missing_base_image"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_validator.py -v`

Expected: FAIL with missing `validator`.

- [ ] **Step 3: Implement validator**

Create `backend/app/video_workbench/validator.py`:

```python
from .models import Shot, ShotKind, ShotMode


def validate_project(shots: list[Shot], audio_duration_seconds: float | None, tolerance: float = 0.25) -> dict:
    issues = []
    sorted_shots = sorted(shots, key=lambda shot: shot.shot_id)
    by_id = {shot.shot_id: shot for shot in sorted_shots}

    _check_duplicate_ids(sorted_shots, issues)
    _check_time_continuity(sorted_shots, issues, tolerance)
    _check_assets(sorted_shots, by_id, issues)
    _check_audio_end(sorted_shots, audio_duration_seconds, issues, tolerance)

    return {"render_ready": len(issues) == 0, "issues": issues}


def _check_duplicate_ids(shots: list[Shot], issues: list[dict]):
    seen = set()
    for shot in shots:
        if shot.shot_id in seen:
            issues.append({"code": "duplicate_shot_id", "shot_id": shot.shot_id, "message": f"Duplicate shot id {shot.shot_id}"})
        seen.add(shot.shot_id)


def _check_time_continuity(shots: list[Shot], issues: list[dict], tolerance: float):
    for previous, current in zip(shots, shots[1:]):
        if current.start_seconds > previous.end_seconds + tolerance:
            issues.append({"code": "time_gap", "shot_id": current.shot_id, "message": f"Gap before shot {current.shot_id}"})
        if current.start_seconds < previous.end_seconds - tolerance:
            issues.append({"code": "time_overlap", "shot_id": current.shot_id, "message": f"Overlap before shot {current.shot_id}"})


def _check_assets(shots: list[Shot], by_id: dict[int, Shot], issues: list[dict]):
    for shot in shots:
        if shot.kind == ShotKind.IMAGE and not shot.image_path:
            issues.append({"code": "missing_image", "shot_id": shot.shot_id, "message": f"Shot {shot.shot_id} needs an image"})
        if shot.kind == ShotKind.KEY_NODE_VIDEO:
            if not shot.keyframe_path:
                issues.append({"code": "missing_keyframe", "shot_id": shot.shot_id, "message": f"Shot {shot.shot_id} needs a keyframe"})
            if not shot.video_path:
                issues.append({"code": "missing_video", "shot_id": shot.shot_id, "message": f"Shot {shot.shot_id} needs a video"})
        if shot.mode == ShotMode.MODE_A:
            base = by_id.get(shot.base_image_shot_id or -1)
            if base is None or not base.image_path:
                issues.append({"code": "missing_base_image", "shot_id": shot.shot_id, "message": f"Shot {shot.shot_id} needs base image {shot.base_image_shot_id}"})


def _check_audio_end(shots: list[Shot], audio_duration_seconds: float | None, issues: list[dict], tolerance: float):
    if audio_duration_seconds is None or not shots:
        return
    final_end = max(shot.end_seconds for shot in shots)
    if abs(final_end - audio_duration_seconds) > tolerance:
        issues.append({"code": "audio_timeline_mismatch", "shot_id": None, "message": f"Timeline ends at {final_end:.2f}s but audio is {audio_duration_seconds:.2f}s"})
```

- [ ] **Step 4: Run validator tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_validator.py -v`

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/video_workbench/validator.py backend/tests/video_workbench/test_validator.py
git commit -m "feat: validate video workbench timelines"
```

---

### Task 7: Subtitle Generation

**Files:**
- Create: `backend/app/video_workbench/subtitles.py`
- Test: `backend/tests/video_workbench/test_subtitles.py`

- [ ] **Step 1: Write subtitle tests**

Create `backend/tests/video_workbench/test_subtitles.py`:

```python
from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.subtitles import generate_ass, generate_srt


def test_generate_chinese_srt():
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B, dialogue_zh="真相是，你完全被骗了..."),
        Shot(2, 2, 4, 2, ShotKind.IMAGE, ShotMode.MODE_B, dialogue_zh="无法放下手机。"),
    ]
    srt = generate_srt(shots, language="zh")
    assert "00:00:00,000 --> 00:00:02,000" in srt
    assert "真相是，你完全被骗了..." in srt
    assert "无法放下手机。" in srt


def test_generate_bilingual_ass():
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B, dialogue_zh="真相是，你完全被骗了...", dialogue_en="You have been lied to.")
    ]
    ass = generate_ass(shots)
    assert "[V4+ Styles]" in ass
    assert "真相是，你完全被骗了...\\\\NYou have been lied to." in ass
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_subtitles.py -v`

Expected: FAIL with missing `subtitles`.

- [ ] **Step 3: Implement subtitle generation**

Create `backend/app/video_workbench/subtitles.py`:

```python
from .models import Shot


def generate_srt(shots: list[Shot], language: str = "zh") -> str:
    lines = []
    index = 1
    for shot in sorted(shots, key=lambda item: item.start_seconds):
        text = shot.dialogue_zh if language == "zh" else shot.dialogue_en
        if not text:
            continue
        lines.extend([
            str(index),
            f"{_srt_time(shot.start_seconds)} --> {_srt_time(shot.end_seconds)}",
            text,
            "",
        ])
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
    for shot in sorted(shots, key=lambda item: item.start_seconds):
        text = _bilingual_text(shot)
        if not text:
            continue
        events.append(f"Dialogue: 0,{_ass_time(shot.start_seconds)},{_ass_time(shot.end_seconds)},Default,,0,0,0,,{text}")
    return header + "\n".join(events) + "\n"


def _bilingual_text(shot: Shot) -> str:
    if shot.dialogue_zh and shot.dialogue_en:
        return f"{shot.dialogue_zh}\\\\N{shot.dialogue_en}"
    return shot.dialogue_zh or shot.dialogue_en


def _srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours = milliseconds // 3_600_000
    milliseconds %= 3_600_000
    minutes = milliseconds // 60_000
    milliseconds %= 60_000
    secs = milliseconds // 1000
    millis = milliseconds % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _ass_time(seconds: float) -> str:
    centiseconds = int(round(seconds * 100))
    hours = centiseconds // 360_000
    centiseconds %= 360_000
    minutes = centiseconds // 6_000
    centiseconds %= 6_000
    secs = centiseconds // 100
    cents = centiseconds % 100
    return f"{hours}:{minutes:02d}:{secs:02d}.{cents:02d}"
```

- [ ] **Step 4: Run subtitle tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_subtitles.py -v`

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/video_workbench/subtitles.py backend/tests/video_workbench/test_subtitles.py
git commit -m "feat: generate video workbench subtitles"
```

---

### Task 8: Media Probe And Render Plan

**Files:**
- Create: `backend/app/video_workbench/media_probe.py`
- Create: `backend/app/video_workbench/render_plan.py`
- Test: `backend/tests/video_workbench/test_render_plan.py`

- [ ] **Step 1: Write render plan tests**

Create `backend/tests/video_workbench/test_render_plan.py`:

```python
from app.video_workbench.models import Shot, ShotKind, ShotMode
from app.video_workbench.render_plan import build_render_plan


def test_build_render_plan_for_images_and_video():
    shots = [
        Shot(1, 0, 2, 2, ShotKind.IMAGE, ShotMode.MODE_B, image_path="assets/images/shot_001_image.png"),
        Shot(10, 2, 5, 3, ShotKind.KEY_NODE_VIDEO, ShotMode.KEY_NODE, keyframe_path="assets/keyframes/shot_010_keyframe.png", video_path="assets/videos/shot_010_video.mp4"),
    ]
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
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_render_plan.py -v`

Expected: FAIL with missing `render_plan`.

- [ ] **Step 3: Implement media probe wrapper**

Create `backend/app/video_workbench/media_probe.py`:

```python
import json
import subprocess


def probe_duration_seconds(path: str) -> float:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return float(payload["format"]["duration"])
```

- [ ] **Step 4: Implement render plan builder**

Create `backend/app/video_workbench/render_plan.py`:

```python
from .models import Shot, ShotKind


def build_render_plan(
    project_slug: str,
    shots: list[Shot],
    audio_path: str,
    audio_duration_seconds: float,
    subtitles_path: str,
) -> dict:
    segments = []
    for shot in sorted(shots, key=lambda item: item.start_seconds):
        if shot.kind == ShotKind.IMAGE:
            segments.append({
                "shot_id": shot.shot_id,
                "operation": "image_to_video",
                "input": shot.image_path,
                "start_seconds": shot.start_seconds,
                "duration_seconds": shot.duration_seconds,
                "output": f"renders/segments/shot_{shot.shot_id:03d}.mp4",
            })
        else:
            segments.append({
                "shot_id": shot.shot_id,
                "operation": "normalize_video",
                "input": shot.video_path,
                "keyframe": shot.keyframe_path,
                "start_seconds": shot.start_seconds,
                "duration_seconds": shot.duration_seconds,
                "output": f"renders/segments/shot_{shot.shot_id:03d}.mp4",
            })
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
```

- [ ] **Step 5: Run render plan tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_render_plan.py -v`

Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/video_workbench/media_probe.py backend/app/video_workbench/render_plan.py backend/tests/video_workbench/test_render_plan.py
git commit -m "feat: build aligned render plans"
```

---

### Task 9: FastAPI Routes

**Files:**
- Create: `backend/app/video_workbench/api.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/video_workbench/test_api.py`

- [ ] **Step 1: Write API tests**

Create `backend/tests/video_workbench/test_api.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_video_workbench_health():
    client = TestClient(app)
    response = client.get("/api/video-workbench/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_parse_storyboard_endpoint():
    client = TestClient(app)
    response = client.post("/api/video-workbench/parse", json={
        "text": "第 1 张图片 ▏时间：0:00 — 0:02 ▏模式：B（全新构图）\n台词：你好 / Hello\n--- 提示词 ---\nScene: Test"
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["shots"][0]["shot_id"] == 1
    assert payload["shots"][0]["dialogue_zh"] == "你好"
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd backend && python -m pytest tests/video_workbench/test_api.py -v`

Expected: FAIL with 404 for `/api/video-workbench/health`.

- [ ] **Step 3: Implement API routes**

Create `backend/app/video_workbench/api.py`:

```python
from dataclasses import asdict

from fastapi import APIRouter
from pydantic import BaseModel

from .parser import parse_storyboard_text

router = APIRouter(prefix="/api/video-workbench", tags=["video-workbench"])


class ParseRequest(BaseModel):
    text: str


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/parse")
async def parse_storyboard(data: ParseRequest):
    parsed = parse_storyboard_text(data.text)
    return {
        "planning": asdict(parsed.planning),
        "shots": [asdict(shot) for shot in parsed.shots],
    }
```

Modify `backend/app/main.py` by adding the import near existing imports:

```python
from .video_workbench.api import router as video_workbench_router
```

Then add this after middleware setup:

```python
app.include_router(video_workbench_router)
```

- [ ] **Step 4: Run API tests**

Run: `cd backend && python -m pytest tests/video_workbench/test_api.py -v`

Expected: 2 passed.

- [ ] **Step 5: Run all backend workbench tests**

Run: `cd backend && python -m pytest tests/video_workbench -v`

Expected: all workbench tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/video_workbench/api.py backend/app/main.py backend/tests/video_workbench/test_api.py
git commit -m "feat: expose video workbench api"
```

---

### Task 10: Frontend API Client And Route

**Files:**
- Create: `frontend/src/services/videoWorkbenchApi.js`
- Create: `frontend/src/views/VideoWorkbench.vue`
- Modify: `frontend/src/router/index.js`

- [ ] **Step 1: Create API client**

Create `frontend/src/services/videoWorkbenchApi.js`:

```javascript
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed: ${response.status}`)
  }
  return response.json()
}

export function parseStoryboard(text) {
  return request('/api/video-workbench/parse', {
    method: 'POST',
    body: JSON.stringify({ text })
  })
}
```

- [ ] **Step 2: Create initial workbench view**

Create `frontend/src/views/VideoWorkbench.vue`:

```vue
<template>
  <main class="video-workbench">
    <aside class="video-workbench__sidebar">
      <h1>短视频生产工作台</h1>
      <p>导入分镜、管理素材、校验对齐并导出成片。</p>
    </aside>
    <section class="video-workbench__main">
      <h2>分镜导入</h2>
      <textarea v-model="storyboardText" aria-label="粘贴 Google AI Studio 分镜文本"></textarea>
      <button type="button" @click="handleParse">解析分镜</button>
      <p v-if="error" class="video-workbench__error">{{ error }}</p>
      <pre v-if="parsed">{{ parsed }}</pre>
    </section>
  </main>
</template>

<script setup>
import { ref } from 'vue'
import { parseStoryboard } from '../services/videoWorkbenchApi'

const storyboardText = ref('')
const parsed = ref(null)
const error = ref('')

async function handleParse() {
  error.value = ''
  parsed.value = null
  try {
    parsed.value = await parseStoryboard(storyboardText.value)
  } catch (err) {
    error.value = err.message
  }
}
</script>

<style scoped>
.video-workbench {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 280px 1fr;
  background: #f6f7f9;
  color: #1f2933;
}
.video-workbench__sidebar {
  padding: 24px;
  background: #111827;
  color: #f9fafb;
}
.video-workbench__main {
  padding: 24px;
}
textarea {
  width: 100%;
  min-height: 220px;
  margin: 12px 0;
  padding: 12px;
  resize: vertical;
}
button {
  padding: 10px 14px;
}
.video-workbench__error {
  color: #b42318;
}
pre {
  max-height: 420px;
  overflow: auto;
  background: white;
  padding: 16px;
}
</style>
```

- [ ] **Step 3: Add route**

Modify `frontend/src/router/index.js` and add this route before the dynamic `/scene/:id` route:

```javascript
{ path: '/video-workbench', name: 'video-workbench', component: () => import('../views/VideoWorkbench.vue') },
```

- [ ] **Step 4: Run frontend build**

Run: `cd frontend && npm run build`

Expected: Vite build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/videoWorkbenchApi.js frontend/src/views/VideoWorkbench.vue frontend/src/router/index.js
git commit -m "feat: add video workbench route"
```

---

### Task 11: Frontend Timeline And Validation Components

**Files:**
- Create: `frontend/src/components/video-workbench/ShotTimeline.vue`
- Create: `frontend/src/components/video-workbench/ValidationPanel.vue`
- Create: `frontend/src/components/video-workbench/__tests__/ShotTimeline.spec.js`
- Create: `frontend/src/components/video-workbench/__tests__/ValidationPanel.spec.js`
- Modify: `frontend/src/views/VideoWorkbench.vue`

- [ ] **Step 1: Write ShotTimeline test**

Create `frontend/src/components/video-workbench/__tests__/ShotTimeline.spec.js`:

```javascript
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ShotTimeline from '../ShotTimeline.vue'

describe('ShotTimeline', () => {
  it('renders shot cards and emits selection', async () => {
    const wrapper = mount(ShotTimeline, {
      props: {
        shots: [
          { shot_id: 1, mode: 'B', kind: 'image', start_seconds: 0, end_seconds: 2, status: 'parsed' },
          { shot_id: 10, mode: 'KEY_NODE', kind: 'key_node_video', start_seconds: 18, end_seconds: 21, status: 'video_pending' }
        ]
      }
    })
    expect(wrapper.text()).toContain('#001')
    expect(wrapper.text()).toContain('KEY_NODE')
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('select-shot')[0][0].shot_id).toBe(1)
  })
})
```

- [ ] **Step 2: Write ValidationPanel test**

Create `frontend/src/components/video-workbench/__tests__/ValidationPanel.spec.js`:

```javascript
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ValidationPanel from '../ValidationPanel.vue'

describe('ValidationPanel', () => {
  it('shows render ready state', () => {
    const wrapper = mount(ValidationPanel, {
      props: { report: { render_ready: true, issues: [] } }
    })
    expect(wrapper.text()).toContain('可以渲染')
  })

  it('shows validation issues', () => {
    const wrapper = mount(ValidationPanel, {
      props: { report: { render_ready: false, issues: [{ code: 'missing_image', shot_id: 1, message: 'Shot 1 needs an image' }] } }
    })
    expect(wrapper.text()).toContain('missing_image')
    expect(wrapper.text()).toContain('Shot 1 needs an image')
  })
})
```

- [ ] **Step 3: Run tests to verify failure**

Run: `cd frontend && npm run test -- ShotTimeline.spec.js ValidationPanel.spec.js`

Expected: FAIL because components do not exist.

- [ ] **Step 4: Implement ShotTimeline**

Create `frontend/src/components/video-workbench/ShotTimeline.vue`:

```vue
<template>
  <section class="shot-timeline">
    <button
      v-for="shot in shots"
      :key="shot.shot_id"
      class="shot-card"
      type="button"
      @click="$emit('select-shot', shot)"
    >
      <strong>#{{ String(shot.shot_id).padStart(3, '0') }}</strong>
      <span>{{ shot.mode }}</span>
      <span>{{ formatTime(shot.start_seconds) }} - {{ formatTime(shot.end_seconds) }}</span>
      <small>{{ shot.status }}</small>
    </button>
  </section>
</template>

<script setup>
defineProps({
  shots: { type: Array, required: true }
})

defineEmits(['select-shot'])

function formatTime(value) {
  const total = Math.round(value)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}
</script>

<style scoped>
.shot-timeline {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 10px;
}
.shot-card {
  display: grid;
  gap: 6px;
  text-align: left;
  padding: 12px;
  border: 1px solid #d0d5dd;
  background: #fff;
  border-radius: 8px;
}
</style>
```

- [ ] **Step 5: Implement ValidationPanel**

Create `frontend/src/components/video-workbench/ValidationPanel.vue`:

```vue
<template>
  <section class="validation-panel">
    <h2>校验结果</h2>
    <p v-if="report?.render_ready" class="validation-panel__ready">可以渲染</p>
    <p v-else class="validation-panel__blocked">暂不可渲染</p>
    <ul v-if="report?.issues?.length">
      <li v-for="issue in report.issues" :key="`${issue.code}-${issue.shot_id}`">
        <strong>{{ issue.code }}</strong>
        <span>{{ issue.message }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
defineProps({
  report: { type: Object, default: () => ({ render_ready: false, issues: [] }) }
})
</script>

<style scoped>
.validation-panel {
  background: #fff;
  border: 1px solid #d0d5dd;
  border-radius: 8px;
  padding: 16px;
}
.validation-panel__ready {
  color: #067647;
}
.validation-panel__blocked {
  color: #b42318;
}
li {
  display: grid;
  gap: 4px;
  margin-top: 8px;
}
</style>
```

- [ ] **Step 6: Wire components into view**

Modify `frontend/src/views/VideoWorkbench.vue` so the script imports `ShotTimeline` and `ValidationPanel`, stores `shots`, `selectedShot`, and a local initial validation report after parsing:

```javascript
import ShotTimeline from '../components/video-workbench/ShotTimeline.vue'
import ValidationPanel from '../components/video-workbench/ValidationPanel.vue'

const shots = ref([])
const selectedShot = ref(null)
const validationReport = ref({ render_ready: false, issues: [] })

async function handleParse() {
  error.value = ''
  parsed.value = null
  shots.value = []
  selectedShot.value = null
  try {
    parsed.value = await parseStoryboard(storyboardText.value)
    shots.value = parsed.value.shots
    validationReport.value = { render_ready: false, issues: [{ code: 'assets_not_imported', message: '分镜已解析，请导入素材后校验。' }] }
  } catch (err) {
    error.value = err.message
  }
}
```

Update the template to render:

```vue
<ShotTimeline v-if="shots.length" :shots="shots" @select-shot="selectedShot = $event" />
<ValidationPanel :report="validationReport" />
<aside v-if="selectedShot">
  <h2>#{{ String(selectedShot.shot_id).padStart(3, '0') }}</h2>
  <p>{{ selectedShot.dialogue_zh }}</p>
  <pre>{{ selectedShot.image_prompt || selectedShot.i2v_prompt }}</pre>
</aside>
```

- [ ] **Step 7: Run component tests**

Run: `cd frontend && npm run test -- ShotTimeline.spec.js ValidationPanel.spec.js`

Expected: tests pass.

- [ ] **Step 8: Run frontend build**

Run: `cd frontend && npm run build`

Expected: Vite build succeeds.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/video-workbench frontend/src/views/VideoWorkbench.vue
git commit -m "feat: show video workbench timeline"
```

---

### Task 12: End-To-End MVP Verification

**Files:**
- Modify only files needed to fix defects found by verification.

- [ ] **Step 1: Run backend tests**

Run: `cd backend && python -m pytest tests/video_workbench -v`

Expected: all video workbench backend tests pass.

- [ ] **Step 2: Run frontend tests**

Run: `cd frontend && npm run test`

Expected: all frontend tests pass.

- [ ] **Step 3: Run frontend build**

Run: `cd frontend && npm run build`

Expected: Vite build succeeds.

- [ ] **Step 4: Start backend server**

Run: `cd backend && uvicorn app.main:app --reload --port 8000`

Expected: server starts and `/api/video-workbench/health` returns `{"status":"ok"}`.

- [ ] **Step 5: Start frontend dev server**

Run: `cd frontend && npm run dev -- --host 127.0.0.1`

Expected: Vite prints a local URL. Open `/video-workbench`.

- [ ] **Step 6: Manual smoke test**

Use a real storyboard sample containing:

- One Mode B shot.
- One Mode A shot.
- One key node I2V shot.
- Planning metadata with audio duration.

Expected:

- The text parses without crashing.
- Shot cards appear in order.
- Selecting a shot shows dialogue and prompt text.
- Validation panel shows that assets are not imported yet.

- [ ] **Step 7: Commit final fixes**

If verification required fixes:

```bash
git add backend frontend
git commit -m "fix: stabilize video workbench mvp"
```

If no fixes were needed, do not create an empty commit.

---

## Follow-Up Plans

Create separate implementation plans after this MVP lands:

- AI Studio browser Agent for continuing and collecting storyboard batches.
- Nano banana browser Agent for Mode A, Mode B, and keyframe generation.
- Jimeng browser Agent for I2V generation and video download.
- Full FFmpeg execution pipeline that creates `final_clean.mp4` and `final_with_subtitles.mp4` from the render plan.

## Self-Review Notes

- Spec coverage: Phase 1 MVP requirements are covered by Tasks 1-12. Browser agents are intentionally separated into follow-up plans because they are independent execution plugins.
- Completion marker scan: This plan contains no unfinished markers or unspecified implementation steps.
- Type consistency: Backend model names are `Shot`, `ShotKind`, `ShotMode`, `ShotStatus`, and those names are used consistently by parser, repository, storage, validator, subtitles, and render-plan tasks.
