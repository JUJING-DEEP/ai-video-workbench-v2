from __future__ import annotations

from pathlib import Path

from .models import Shot, ShotKind, ShotMode


class ProjectStorage:
    def __init__(self, projects_root: str | Path):
        self.projects_root = Path(projects_root)

    def project_dir(self, slug: str) -> Path:
        slug_path = Path(slug)
        if (
            not slug
            or slug_path.is_absolute()
            or len(slug_path.parts) != 1
            or slug in {".", ".."}
        ):
            raise ValueError("Invalid project slug")

        root = self.projects_root.resolve()
        path = (root / slug).resolve()
        if root != path and root not in path.parents:
            raise ValueError("Invalid project slug")
        return path

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
                dependency = (
                    f"\nBase Image: shot_{shot.base_image_shot_id:03d}_image.png"
                    if shot.mode == ShotMode.MODE_A and shot.base_image_shot_id
                    else ""
                )
                nano_image_lines.append(
                    f"## Shot {shot.shot_id:03d}\n"
                    f"Output: {output}{dependency}\n"
                    f"Duration: {shot.duration_seconds:.2f}s\n\n"
                    f"{shot.image_prompt}\n"
                )
            if shot.kind == ShotKind.KEY_NODE_VIDEO:
                keyframe = f"shot_{shot.shot_id:03d}_keyframe.png"
                video = f"shot_{shot.shot_id:03d}_video.mp4"
                nano_keyframe_lines.append(
                    f"## Shot {shot.shot_id:03d}\n"
                    f"Output: {keyframe}\n"
                    f"Duration: {shot.duration_seconds:.2f}s\n\n"
                    f"{shot.image_prompt or shot.i2v_prompt}\n"
                )
                jimeng_lines.append(
                    f"## Shot {shot.shot_id:03d}\n"
                    f"Keyframe: {keyframe}\n"
                    f"Output: {video}\n"
                    f"Duration: {shot.duration_seconds:.2f}s\n\n"
                    f"{shot.i2v_prompt}\n"
                )

        nano_images.write_text("\n".join(nano_image_lines), encoding="utf-8")
        nano_keyframes.write_text("\n".join(nano_keyframe_lines), encoding="utf-8")
        jimeng_i2v.write_text("\n".join(jimeng_lines), encoding="utf-8")

        return {
            "nano_images": nano_images,
            "nano_keyframes": nano_keyframes,
            "jimeng_i2v": jimeng_i2v,
        }
