from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from .parser import parse_storyboard_text
from .repository import VideoWorkbenchRepository

router = APIRouter(prefix="/api/video-workbench", tags=["video-workbench"])


class ParseRequest(BaseModel):
    text: str


class CreateProjectRequest(BaseModel):
    title: str
    role_card: str = ""
    audio_path: str = ""
    audio_duration_seconds: Optional[float] = None


class ImportStoryboardRequest(BaseModel):
    text: str


class BindAssetRequest(BaseModel):
    asset_type: str
    path: str


class CreateAssetRequest(BaseModel):
    asset_type: str
    name: str
    path: str


def get_repository() -> VideoWorkbenchRepository:
    db_path = Path(os.getenv("VIDEO_WORKBENCH_DB_PATH", "video_workbench.db"))
    projects_root = Path(os.getenv("VIDEO_WORKBENCH_PROJECTS_ROOT", "video_projects"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    projects_root.mkdir(parents=True, exist_ok=True)

    repository = VideoWorkbenchRepository(db_path=db_path, projects_root=projects_root)
    repository.init_schema()
    return repository


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/parse")
async def parse_storyboard(data: ParseRequest):
    try:
        parsed = parse_storyboard_text(data.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return jsonable_encoder(
        {
            "planning": asdict(parsed.planning),
            "shots": [asdict(shot) for shot in parsed.shots],
        }
    )


@router.get("/projects")
async def list_projects(repository: VideoWorkbenchRepository = Depends(get_repository)):
    return jsonable_encoder({"projects": repository.list_projects()})


@router.post("/projects")
async def create_project(
    data: CreateProjectRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    title = data.title.strip()
    if not title:
        raise HTTPException(status_code=400, detail="Project title is required.")

    project = repository.create_project(
        title=title,
        role_card=data.role_card,
        audio_path=data.audio_path,
        audio_duration_seconds=data.audio_duration_seconds,
    )
    return jsonable_encoder({"project": project})


@router.get("/projects/{project_id}/shots")
async def get_project_shots(
    project_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        repository.get_project(project_id)
        shots = repository.get_project_shots(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder({"shots": [asdict(shot) for shot in shots]})


@router.post("/projects/{project_id}/storyboard")
async def import_storyboard_to_project(
    project_id: int,
    data: ImportStoryboardRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        parsed = parse_storyboard_text(data.text)
        repository.replace_project_shots(project_id, parsed.shots)
        project = repository.get_project(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder(
        {
            "project": project,
            "planning": asdict(parsed.planning),
            "shots": [asdict(shot) for shot in parsed.shots],
        }
    )


@router.post("/projects/{project_id}/shots/{shot_id}/assets")
async def bind_shot_asset(
    project_id: int,
    shot_id: int,
    data: BindAssetRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    asset_type = data.asset_type.strip()
    path = data.path.strip()

    if asset_type not in {"image", "keyframe", "video"}:
        raise HTTPException(
            status_code=400,
            detail="asset_type must be one of: image, keyframe, video.",
        )
    if not path:
        raise HTTPException(status_code=400, detail="Asset path is required.")

    try:
        repository.bind_asset(project_id, shot_id, asset_type, path)
        shot = next(
            shot for shot in repository.get_project_shots(project_id) if shot.shot_id == shot_id
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Shot not found: {project_id}/{shot_id}") from exc

    return jsonable_encoder({"shot": asdict(shot)})


@router.get("/projects/{project_id}/assets")
async def list_project_assets(
    project_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        assets = repository.list_assets(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder({"assets": assets})


@router.post("/projects/{project_id}/assets")
async def create_project_asset(
    project_id: int,
    data: CreateAssetRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    asset_type = data.asset_type.strip()
    name = data.name.strip()
    path = data.path.strip()

    if asset_type not in {"image", "keyframe", "video"}:
        raise HTTPException(
            status_code=400,
            detail="asset_type must be one of: image, keyframe, video.",
        )
    if not name:
        raise HTTPException(status_code=400, detail="Asset name is required.")
    if not path:
        raise HTTPException(status_code=400, detail="Asset path is required.")

    try:
        asset = repository.create_asset(project_id, asset_type, name, path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder({"asset": asset})
