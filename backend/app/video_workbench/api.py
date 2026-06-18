from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel

from .nano_banana import NanoBananaClient, NanoBananaError
from .parser import parse_storyboard_text
from .repository import VideoWorkbenchRepository
from .video_provider import MockVideoProvider, VideoGenerationProvider, VideoProviderError

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
    source: str = "manual"
    prompt: str = ""


class ProviderSettingsRequest(BaseModel):
    nano_banana_api_key: str = ""
    nano_banana_base_url: str = ""


class JimengSettingsRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""


class GenerateImageRequest(BaseModel):
    prompt: str


class GenerateVideoRequest(BaseModel):
    provider: str = "jimeng"


class ReorderShotsRequest(BaseModel):
    shot_ids: List[int]


def get_repository() -> VideoWorkbenchRepository:
    db_path = Path(os.getenv("VIDEO_WORKBENCH_DB_PATH", "video_workbench.db"))
    projects_root = Path(os.getenv("VIDEO_WORKBENCH_PROJECTS_ROOT", "video_projects"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    projects_root.mkdir(parents=True, exist_ok=True)

    repository = VideoWorkbenchRepository(db_path=db_path, projects_root=projects_root)
    repository.init_schema()
    return repository


def get_nano_banana_client() -> NanoBananaClient:
    return NanoBananaClient()


def get_video_provider() -> VideoGenerationProvider:
    return MockVideoProvider()


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
    source = data.source.strip() or "manual"
    prompt = data.prompt.strip()

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
        asset = repository.create_asset(project_id, asset_type, name, path, source, prompt)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder({"asset": asset})


@router.get("/provider-settings/nano-banana")
async def get_nano_banana_provider_settings(
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    settings = repository.get_provider_settings("nano_banana")
    return jsonable_encoder(
        {
            "settings": {
                "provider": "nano_banana",
                "nano_banana_api_key": settings["api_key"],
                "nano_banana_base_url": settings["base_url"],
                "updated_at": settings["updated_at"],
            }
        }
    )


@router.put("/provider-settings/nano-banana")
async def save_nano_banana_provider_settings(
    data: ProviderSettingsRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    settings = repository.save_provider_settings(
        "nano_banana",
        data.nano_banana_api_key.strip(),
        data.nano_banana_base_url.strip(),
    )
    return jsonable_encoder(
        {
            "settings": {
                "provider": "nano_banana",
                "nano_banana_api_key": settings["api_key"],
                "nano_banana_base_url": settings["base_url"],
                "updated_at": settings["updated_at"],
            }
        }
    )


@router.get("/provider-settings/jimeng")
async def get_jimeng_provider_settings(
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    settings = repository.get_provider_settings("jimeng")
    return jsonable_encoder(
        {
            "settings": {
                "provider": "jimeng",
                "api_key": settings["api_key"],
                "base_url": settings["base_url"],
                "updated_at": settings["updated_at"],
            }
        }
    )


@router.put("/provider-settings/jimeng")
async def save_jimeng_provider_settings(
    data: JimengSettingsRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    settings = repository.save_provider_settings(
        "jimeng",
        data.api_key.strip(),
        data.base_url.strip(),
    )
    return jsonable_encoder(
        {
            "settings": {
                "provider": "jimeng",
                "api_key": settings["api_key"],
                "base_url": settings["base_url"],
                "updated_at": settings["updated_at"],
            }
        }
    )


@router.post("/projects/{project_id}/generate-image")
async def generate_project_image(
    project_id: int,
    data: GenerateImageRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
    nano_banana_client: NanoBananaClient = Depends(get_nano_banana_client),
):
    prompt = data.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    try:
        repository.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    settings = repository.get_provider_settings("nano_banana")
    api_key = settings["api_key"].strip()
    base_url = settings["base_url"].strip()
    if not api_key or not base_url:
        raise HTTPException(status_code=400, detail="Nano Banana provider settings are required.")

    try:
        image_bytes = nano_banana_client.generate_image(prompt, api_key, base_url)
    except NanoBananaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    generated_dir = Path("data") / "uploads" / str(project_id) / "generated"
    generated_dir.mkdir(parents=True, exist_ok=True)
    filename = f"nano-banana-{abs(hash(prompt))}.png"
    image_path = generated_dir / filename
    image_path.write_bytes(image_bytes)

    asset = repository.create_asset(
        project_id,
        asset_type="image",
        name=filename,
        path=image_path.as_posix(),
        source="nano_banana",
        prompt=prompt,
    )

    return jsonable_encoder(
        {
            "asset_id": asset["id"],
            "image_path": asset["path"],
            "asset_type": "image",
        }
    )


@router.post("/projects/{project_id}/shots/{shot_id}/generate-video")
async def generate_shot_video(
    project_id: int,
    shot_id: int,
    data: GenerateVideoRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
    video_provider: VideoGenerationProvider = Depends(get_video_provider),
):
    provider = data.provider.strip() or "jimeng"
    if provider != "jimeng":
        raise HTTPException(status_code=400, detail="provider must be jimeng.")

    try:
        repository.get_project(project_id)
        shots = repository.get_project_shots(project_id)
        shot = next(shot for shot in shots if shot.shot_id == shot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Shot not found: {project_id}/{shot_id}") from exc

    keyframe_path = shot.keyframe_path.strip()
    if not keyframe_path:
        raise HTTPException(status_code=400, detail="Shot must have a keyframe before video generation.")

    settings = repository.get_provider_settings(provider)
    api_key = settings["api_key"].strip()
    base_url = settings["base_url"].strip()
    if not api_key or not base_url:
        raise HTTPException(status_code=400, detail="Jimeng provider settings are required.")

    try:
        video_bytes = video_provider.generate_video(keyframe_path, api_key, base_url)
    except VideoProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    generated_dir = Path("data") / "uploads" / str(project_id) / "generated" / "videos"
    generated_dir.mkdir(parents=True, exist_ok=True)
    filename = f"jimeng-video-{shot_id}.mp4"
    video_path = generated_dir / filename
    video_path.write_bytes(video_bytes)

    asset = repository.create_asset(
        project_id,
        asset_type="video",
        name=filename,
        path=video_path.as_posix(),
        source=provider,
    )
    repository.bind_asset(project_id, shot_id, "video", asset["path"])

    return jsonable_encoder(
        {
            "asset_id": asset["id"],
            "shot_id": shot_id,
            "video_path": asset["path"],
            "asset_type": "video",
        }
    )


@router.post("/projects/{project_id}/render-plan")
async def create_project_render_plan(
    project_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        render_plan = repository.create_render_plan(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder(render_plan)


@router.get("/projects/{project_id}/render-plan")
async def get_project_render_plan(
    project_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        render_plan = repository.get_render_plan(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder(render_plan)


@router.post("/projects/{project_id}/render-plan/export")
async def export_project_render_plan(
    project_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        exported = repository.export_render_plan(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder(exported)


@router.put("/projects/{project_id}/shots/reorder")
async def reorder_project_shots(
    project_id: int,
    data: ReorderShotsRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        result = repository.reorder_shots(project_id, data.shot_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return jsonable_encoder(result)


@router.get("/projects/{project_id}/timeline")
async def get_project_timeline(
    project_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        timeline = repository.get_timeline(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder(timeline)


@router.post("/projects/{project_id}/shots/{shot_id}/generate-keyframe")
async def generate_shot_keyframe(
    project_id: int,
    shot_id: int,
    data: GenerateImageRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
    nano_banana_client: NanoBananaClient = Depends(get_nano_banana_client),
):
    prompt = data.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    try:
        repository.get_project(project_id)
        shots = repository.get_project_shots(project_id)
        next(shot for shot in shots if shot.shot_id == shot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Shot not found: {project_id}/{shot_id}") from exc

    settings = repository.get_provider_settings("nano_banana")
    api_key = settings["api_key"].strip()
    base_url = settings["base_url"].strip()
    if not api_key or not base_url:
        raise HTTPException(status_code=400, detail="Nano Banana provider settings are required.")

    try:
        image_bytes = nano_banana_client.generate_image(prompt, api_key, base_url)
    except NanoBananaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    generated_dir = Path("data") / "uploads" / str(project_id) / "generated" / "keyframes"
    generated_dir.mkdir(parents=True, exist_ok=True)
    filename = f"nano-banana-keyframe-{abs(hash(prompt))}.png"
    image_path = generated_dir / filename
    image_path.write_bytes(image_bytes)

    asset = repository.create_asset(
        project_id,
        asset_type="keyframe",
        name=filename,
        path=image_path.as_posix(),
        source="nano_banana",
        prompt=prompt,
    )
    repository.bind_asset(project_id, shot_id, "keyframe", asset["path"])

    return jsonable_encoder(
        {
            "asset_id": asset["id"],
            "shot_id": shot_id,
            "path": asset["path"],
            "asset_type": "keyframe",
        }
    )


@router.post("/projects/{project_id}/upload")
async def upload_project_asset(
    project_id: int,
    asset_type: str = Form(...),
    file: UploadFile = File(...),
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    normalized_type = asset_type.strip()
    if normalized_type not in {"image", "keyframe", "video"}:
        raise HTTPException(
            status_code=400,
            detail="asset_type must be one of: image, keyframe, video.",
        )

    try:
        repository.get_project(project_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    filename = Path(file.filename or "upload").name
    upload_dir = Path("data") / "uploads" / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_path = upload_dir / filename
    output_path.write_bytes(await file.read())

    return jsonable_encoder(
        {
            "name": filename,
            "path": output_path.as_posix(),
            "asset_type": normalized_type,
        }
    )
