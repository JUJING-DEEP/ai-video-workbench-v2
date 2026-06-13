from __future__ import annotations

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
