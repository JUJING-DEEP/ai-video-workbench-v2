from __future__ import annotations

import json
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
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_schema(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    slug TEXT NOT NULL UNIQUE,
                    role_card TEXT DEFAULT '',
                    audio_path TEXT DEFAULT '',
                    audio_duration_seconds REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
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
                    timeline_order INTEGER,
                    UNIQUE(project_id, shot_id),
                    FOREIGN KEY(project_id) REFERENCES video_projects(id) ON DELETE CASCADE
                )
                """
            )
            self._ensure_column(conn, "video_shots", "timeline_order", "INTEGER")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_assets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    asset_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    path TEXT NOT NULL,
                    source TEXT DEFAULT 'manual',
                    prompt TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES video_projects(id) ON DELETE CASCADE
                )
                """
            )
            self._ensure_column(conn, "video_assets", "source", "TEXT DEFAULT 'manual'")
            self._ensure_column(conn, "video_assets", "prompt", "TEXT DEFAULT ''")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS provider_settings (
                    provider TEXT PRIMARY KEY,
                    api_key TEXT DEFAULT '',
                    base_url TEXT DEFAULT '',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS render_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES video_projects(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS render_plan_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    render_plan_id INTEGER NOT NULL,
                    shot_id INTEGER NOT NULL,
                    item_order INTEGER NOT NULL,
                    video_path TEXT NOT NULL,
                    duration_seconds REAL NOT NULL,
                    FOREIGN KEY(render_plan_id) REFERENCES render_plans(id) ON DELETE CASCADE
                )
                """
            )

    def create_project(
        self,
        title: str,
        role_card: str,
        audio_path: str,
        audio_duration_seconds: float | None,
    ):
        slug = self._unique_slug(title)
        self.projects_root.mkdir(parents=True, exist_ok=True)
        (self.projects_root / slug).mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO video_projects (
                    title, slug, role_card, audio_path, audio_duration_seconds
                )
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
            row = conn.execute(
                "SELECT * FROM video_projects WHERE id = ?",
                (project_id,),
            ).fetchone()

        if row is None:
            raise KeyError(f"Project not found: {project_id}")

        return dict(row)

    def replace_project_shots(self, project_id: int, shots: list[Shot]):
        self.get_project(project_id)

        with self._connect() as conn:
            conn.execute("DELETE FROM video_shots WHERE project_id = ?", (project_id,))
            conn.executemany(
                """
                INSERT INTO video_shots (
                    project_id, shot_id, batch_number, start_seconds,
                    end_seconds, duration_seconds, kind, mode, dialogue_zh,
                    dialogue_en, image_prompt, i2v_prompt, base_image_shot_id,
                    keep_unchanged, add_new_element, key_node_type,
                    visual_style, output_form, status, image_path,
                    keyframe_path, video_path, review_notes, error_message,
                    timeline_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [self._shot_values(project_id, shot) for shot in shots],
            )

    def get_project_shots(self, project_id: int) -> list[Shot]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM video_shots WHERE project_id = ? ORDER BY COALESCE(timeline_order, shot_id), shot_id",
                (project_id,),
            ).fetchall()
        return [self._row_to_shot(row) for row in rows]

    def bind_asset(self, project_id: int, shot_id: int, asset_type: str, path: str):
        column = {
            "image": "image_path",
            "keyframe": "keyframe_path",
            "video": "video_path",
        }[asset_type]
        status = {
            "image": ShotStatus.IMAGE_READY.value,
            "keyframe": ShotStatus.KEYFRAME_READY.value,
            "video": ShotStatus.VIDEO_READY.value,
        }[asset_type]

        with self._connect() as conn:
            cursor = conn.execute(
                f"""
                UPDATE video_shots
                SET {column} = ?, status = ?
                WHERE project_id = ? AND shot_id = ?
                """,
                (path, status, project_id, shot_id),
            )

            if cursor.rowcount == 0:
                raise KeyError(f"Shot not found: {project_id}/{shot_id}")

    def create_asset(
        self,
        project_id: int,
        asset_type: str,
        name: str,
        path: str,
        source: str = "manual",
        prompt: str = "",
    ):
        self.get_project(project_id)

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO video_assets (project_id, asset_type, name, path, source, prompt)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (project_id, asset_type, name, path, source, prompt),
            )
            asset_id = cursor.lastrowid
            row = conn.execute(
                "SELECT * FROM video_assets WHERE id = ?",
                (asset_id,),
            ).fetchone()

        return dict(row)

    def list_assets(self, project_id: int):
        self.get_project(project_id)

        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM video_assets
                WHERE project_id = ?
                ORDER BY id
                """,
                (project_id,),
            ).fetchall()

        return [dict(row) for row in rows]

    def save_provider_settings(self, provider: str, api_key: str, base_url: str):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO provider_settings (provider, api_key, base_url, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(provider) DO UPDATE SET
                    api_key = excluded.api_key,
                    base_url = excluded.base_url,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (provider, api_key, base_url),
            )

        return self.get_provider_settings(provider)

    def get_provider_settings(self, provider: str):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM provider_settings WHERE provider = ?",
                (provider,),
            ).fetchone()

        if row is None:
            return {
                "provider": provider,
                "api_key": "",
                "base_url": "",
                "updated_at": "",
            }

        return dict(row)

    def create_render_plan(self, project_id: int):
        self.get_project(project_id)
        shots = [shot for shot in self.get_project_shots(project_id) if shot.video_path]

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT id FROM render_plans WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            if existing is not None:
                conn.execute("DELETE FROM render_plan_items WHERE render_plan_id = ?", (existing["id"],))
                conn.execute("DELETE FROM render_plans WHERE id = ?", (existing["id"],))

            cursor = conn.execute(
                """
                INSERT INTO render_plans (project_id, created_at, updated_at)
                VALUES (?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """,
                (project_id,),
            )
            render_plan_id = cursor.lastrowid

            conn.executemany(
                """
                INSERT INTO render_plan_items (
                    render_plan_id, shot_id, item_order, video_path, duration_seconds
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        render_plan_id,
                        shot.shot_id,
                        index,
                        shot.video_path,
                        shot.duration_seconds,
                    )
                    for index, shot in enumerate(sorted(shots, key=lambda item: item.shot_id), start=1)
                ],
            )

        return self.get_render_plan(project_id)

    def get_render_plan(self, project_id: int):
        self.get_project(project_id)

        with self._connect() as conn:
            plan = conn.execute(
                "SELECT * FROM render_plans WHERE project_id = ?",
                (project_id,),
            ).fetchone()

            if plan is None:
                return {
                    "id": None,
                    "project_id": project_id,
                    "created_at": "",
                    "updated_at": "",
                    "items": [],
                }

            items = conn.execute(
                """
                SELECT shot_id, item_order, video_path, duration_seconds
                FROM render_plan_items
                WHERE render_plan_id = ?
                ORDER BY item_order
                """,
                (plan["id"],),
            ).fetchall()

        return {
            "id": plan["id"],
            "project_id": plan["project_id"],
            "created_at": plan["created_at"],
            "updated_at": plan["updated_at"],
            "items": [
                {
                    "shot_id": item["shot_id"],
                    "order": item["item_order"],
                    "video_path": item["video_path"],
                    "duration_seconds": item["duration_seconds"],
                }
                for item in items
            ],
        }

    def export_render_plan(self, project_id: int):
        plan = self.get_render_plan(project_id)
        export_data = {
            "project_id": project_id,
            "shots": [
                {
                    "shot_id": item["shot_id"],
                    "video_path": item["video_path"],
                    "duration_seconds": item["duration_seconds"],
                }
                for item in plan["items"]
            ],
        }
        export_dir = Path("data") / "exports" / str(project_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / "render-plan.json"
        export_path.write_text(json.dumps(export_data, ensure_ascii=False, indent=2))
        return {
            "path": export_path.as_posix(),
            "render_plan": export_data,
        }

    def reorder_shots(self, project_id: int, shot_ids: list[int]):
        self.get_project(project_id)
        existing_ids = {shot.shot_id for shot in self.get_project_shots(project_id)}
        requested_ids = set(shot_ids)
        if requested_ids != existing_ids:
            missing = sorted(requested_ids - existing_ids)
            omitted = sorted(existing_ids - requested_ids)
            raise ValueError(f"Invalid shot order. Missing: {missing}. Omitted: {omitted}.")

        with self._connect() as conn:
            for index, shot_id in enumerate(shot_ids, start=1):
                conn.execute(
                    """
                    UPDATE video_shots
                    SET timeline_order = ?
                    WHERE project_id = ? AND shot_id = ?
                    """,
                    (index, project_id, shot_id),
                )

        return {"project_id": project_id, "shot_ids": shot_ids}

    def get_timeline(self, project_id: int):
        self.get_project(project_id)
        shots = self.get_project_shots(project_id)
        return {
            "project_id": project_id,
            "shots": [
                {
                    "shot_id": shot.shot_id,
                    "order": index,
                    "title": shot.dialogue_zh or shot.dialogue_en or f"Shot {shot.shot_id}",
                    "video_path": shot.video_path,
                    "duration_seconds": shot.duration_seconds,
                }
                for index, shot in enumerate(shots, start=1)
            ],
        }

    def _ensure_column(self, conn, table: str, column: str, definition: str):
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        existing_columns = {row["name"] for row in rows}
        if column not in existing_columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _unique_slug(self, title: str) -> str:
        base_slug = _slugify(title)

        with self._connect() as conn:
            rows = conn.execute(
                "SELECT slug FROM video_projects WHERE slug = ? OR slug LIKE ?",
                (base_slug, f"{base_slug}-%"),
            ).fetchall()

        existing_slugs = {row["slug"] for row in rows}
        if base_slug not in existing_slugs:
            return base_slug

        suffix = 2
        while f"{base_slug}-{suffix}" in existing_slugs:
            suffix += 1
        return f"{base_slug}-{suffix}"

    def _shot_values(self, project_id: int, shot: Shot):
        return (
            project_id,
            shot.shot_id,
            shot.batch_number,
            shot.start_seconds,
            shot.end_seconds,
            shot.duration_seconds,
            shot.kind.value,
            shot.mode.value,
            shot.dialogue_zh,
            shot.dialogue_en,
            shot.image_prompt,
            shot.i2v_prompt,
            shot.base_image_shot_id,
            shot.keep_unchanged,
            shot.add_new_element,
            shot.key_node_type,
            shot.visual_style,
            shot.output_form,
            shot.status.value,
            shot.image_path,
            shot.keyframe_path,
            shot.video_path,
            shot.review_notes,
            shot.error_message,
            shot.shot_id,
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
