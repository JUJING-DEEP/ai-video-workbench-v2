from __future__ import annotations

import json
import os
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel

from .nano_banana import NanoBananaClient, NanoBananaError
from .parser import parse_storyboard_text
from .providers.jimeng_rest_provider import JimengRestProvider
from .repository import VideoWorkbenchRepository
from .video_provider import VideoProviderError, VideoProviderTimeoutError
from .video_provider_registry import get_video_provider

ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    502: "provider_error",
    504: "provider_timeout",
}


def success_response(data):
    return {"success": True, "data": data}


def error_response(status_code: int, message: str, code: str | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code or ERROR_CODES.get(status_code, "request_error"),
                "message": message,
            },
        },
    )


def _response_headers(response: Response):
    return {
        key: value
        for key, value in response.headers.items()
        if key.lower() not in {"content-length", "content-type"}
    }


class StandardResponseRoute(APIRoute):
    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                response = await original_route_handler(request)
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else json.dumps(exc.detail)
                return error_response(exc.status_code, detail)
            except RequestValidationError as exc:
                return error_response(422, json.dumps(exc.errors()), "validation_error")

            if response.status_code >= 400 or response.media_type != "application/json":
                return response

            body = getattr(response, "body", b"")
            data = json.loads(body.decode("utf-8")) if body else None
            if isinstance(data, dict) and set(data.keys()) == {"success", "data"}:
                return response
            return JSONResponse(
                status_code=response.status_code,
                content=success_response(data),
                headers=_response_headers(response),
            )

        return custom_route_handler


router = APIRouter(
    prefix="/api/video-workbench",
    tags=["video-workbench"],
    route_class=StandardResponseRoute,
)

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
ALLOWED_UPLOADS = {
    "image": {
        "extensions": {".png", ".jpg", ".jpeg", ".webp"},
        "content_types": {"image/png", "image/jpeg", "image/webp"},
    },
    "keyframe": {
        "extensions": {".png", ".jpg", ".jpeg", ".webp"},
        "content_types": {"image/png", "image/jpeg", "image/webp"},
    },
    "video": {
        "extensions": {".mp4", ".mov", ".webm"},
        "content_types": {"video/mp4", "video/quicktime", "video/webm"},
    },
}


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
    api_key: str = ""
    base_url: str = ""
    enabled: bool = True
    nano_banana_api_key: str = ""
    nano_banana_base_url: str = ""


class JimengSettingsRequest(BaseModel):
    api_key: str = ""
    base_url: str = ""
    access_key: str = ""
    secret_key: str = ""
    region: str = ""
    endpoint: str = ""
    model: str = ""
    enabled: bool = True


class GenerateImageRequest(BaseModel):
    prompt: str


class GenerateVideoRequest(BaseModel):
    provider: str = "mock"


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


def get_jimeng_rest_provider() -> JimengRestProvider:
    return JimengRestProvider()


def _fail_video_generation_job(repository, job_id: int, message: str):
    return repository.update_video_generation_job(
        job_id,
        status="failed",
        error_message=message,
    )


def _validate_jimeng_job_result(result):
    if result is None or not hasattr(result, "status"):
        raise VideoProviderError("Invalid provider response.")
    if result.status not in {"processing", "completed", "failed"}:
        raise VideoProviderError(f"Unknown provider state: {result.status}")
    if result.status == "completed" and not getattr(result, "result_url", "").strip():
        raise VideoProviderError("Jimeng provider completed without result_url.")


def _has_value(settings: dict, key: str) -> bool:
    return bool(str(settings.get(key, "")).strip())


def _public_provider_settings(
    provider: str,
    settings: dict,
    credential_fields: tuple[str, ...],
    extra_fields: tuple[str, ...] = (),
):
    credentials = {field: _has_value(settings, field) for field in credential_fields}
    configured = any(credentials.values())
    payload = {
        "provider": provider,
        "configured": configured,
        "enabled": bool(settings.get("enabled", True)) if configured else False,
        "credentials": credentials,
        "updated_at": settings.get("updated_at", ""),
    }
    for field in extra_fields:
        payload[field] = settings.get(field, "")
    return payload


def _validate_http_url(value: str, label: str):
    if not value:
        return
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status_code=400, detail=f"{label} must be a valid http(s) URL.")


def _validate_asset_path(path: str):
    parsed = urlparse(path)
    if parsed.scheme:
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Asset path must be a local path or http(s) URL.")
        path_parts = Path(parsed.path).parts
    else:
        path_parts = Path(path).parts
    if ".." in path_parts:
        raise HTTPException(status_code=400, detail="Asset path must not contain path traversal.")


def _validate_upload_filename(filename: str):
    if not filename or filename != Path(filename).name or "\\" in filename:
        raise HTTPException(status_code=400, detail="Upload filename is invalid.")


def _validate_upload_type(asset_type: str, filename: str, content_type: str):
    rules = ALLOWED_UPLOADS[asset_type]
    extension = Path(filename).suffix.lower()
    if extension not in rules["extensions"] or content_type not in rules["content_types"]:
        raise HTTPException(status_code=400, detail="Upload file type is not allowed for asset_type.")


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
    _validate_asset_path(path)

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
    _validate_asset_path(path)

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
            "settings": _public_provider_settings(
                "nano_banana",
                settings,
                ("api_key",),
                ("base_url",),
            )
        }
    )


@router.put("/provider-settings/nano-banana")
async def save_nano_banana_provider_settings(
    data: ProviderSettingsRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    api_key = (data.api_key or data.nano_banana_api_key).strip()
    base_url = (data.base_url or data.nano_banana_base_url).strip()
    _validate_http_url(base_url, "Nano Banana base URL")
    settings = repository.save_provider_settings(
        "nano_banana",
        api_key,
        base_url,
        data.enabled,
    )
    return jsonable_encoder(
        {
            "settings": _public_provider_settings(
                "nano_banana",
                settings,
                ("api_key",),
                ("base_url",),
            )
        }
    )


@router.get("/provider-settings/jimeng")
async def get_jimeng_provider_settings(
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    settings = repository.get_provider_settings("jimeng")
    return jsonable_encoder(
        {
            "settings": _public_provider_settings(
                "jimeng",
                settings,
                ("api_key", "access_key", "secret_key"),
                ("base_url", "region", "endpoint", "model"),
            )
        }
    )


@router.put("/provider-settings/jimeng")
async def save_jimeng_provider_settings(
    data: JimengSettingsRequest,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    base_url = data.base_url.strip()
    endpoint = data.endpoint.strip()
    _validate_http_url(base_url, "Jimeng base URL")
    _validate_http_url(endpoint, "Jimeng endpoint URL")
    settings = repository.save_provider_settings(
        "jimeng",
        data.api_key.strip(),
        base_url,
        data.enabled,
        data.access_key.strip(),
        data.secret_key.strip(),
        data.region.strip(),
        endpoint,
        data.model.strip(),
    )
    return jsonable_encoder(
        {
            "settings": _public_provider_settings(
                "jimeng",
                settings,
                ("api_key", "access_key", "secret_key"),
                ("base_url", "region", "endpoint", "model"),
            )
        }
    )


@router.post("/projects/{project_id}/shots/{shot_id}/video-jobs")
async def create_video_generation_job(
    project_id: int,
    shot_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
    provider: JimengRestProvider = Depends(get_jimeng_rest_provider),
):
    try:
        repository.get_project(project_id)
        shots = repository.get_project_shots(project_id)
        shot = next(shot for shot in shots if shot.shot_id == shot_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except StopIteration as exc:
        raise HTTPException(status_code=404, detail=f"Shot not found: {project_id}/{shot_id}") from exc

    if not shot.keyframe_path.strip():
        raise HTTPException(status_code=400, detail="Shot must have a keyframe before video generation.")

    settings = repository.get_provider_settings("jimeng")
    _validate_jimeng_rest_settings(settings)

    job = repository.create_video_generation_job(project_id, shot_id, "jimeng")
    try:
        submit_id = provider.submit_video_generation_job(job["id"], shot, settings)
    except VideoProviderTimeoutError as exc:
        repository.update_video_generation_job(job["id"], status="timeout", error_message=str(exc))
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except VideoProviderError as exc:
        repository.update_video_generation_job(job["id"], status="failed", error_message=str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    job = repository.update_video_generation_job(job["id"], status="submitted", submit_id=submit_id)
    return jsonable_encoder({"job": job})


@router.get("/video-jobs/{job_id}")
async def get_video_generation_job(
    job_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
):
    try:
        job = repository.get_video_generation_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return jsonable_encoder({"job": job})


@router.post("/video-jobs/{job_id}/poll")
async def poll_video_generation_job(
    job_id: int,
    repository: VideoWorkbenchRepository = Depends(get_repository),
    provider: JimengRestProvider = Depends(get_jimeng_rest_provider),
):
    try:
        job = repository.get_video_generation_job(job_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if job["status"] in {"completed", "failed", "timeout"}:
        raise HTTPException(status_code=409, detail="Cannot poll a terminal video job.")
    if not job["submit_id"]:
        raise HTTPException(status_code=409, detail="Cannot poll a video job without submit_id.")
    if job["status"] not in {"submitted", "processing"}:
        raise HTTPException(status_code=409, detail=f"Unexpected video job status: {job['status']}")

    settings = repository.get_provider_settings("jimeng")
    _validate_jimeng_rest_settings(settings)

    try:
        result = provider.poll_video_generation_job(job["submit_id"], settings)
        _validate_jimeng_job_result(result)
    except VideoProviderTimeoutError as exc:
        job = repository.update_video_generation_job(job_id, status="timeout", error_message=str(exc))
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except VideoProviderError as exc:
        job = _fail_video_generation_job(repository, job_id, str(exc))
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if result.status == "processing":
        job = repository.update_video_generation_job(job_id, status="processing")
        return jsonable_encoder({"job": job})

    if result.status == "failed":
        job = repository.update_video_generation_job(
            job_id,
            status="failed",
            result_url=result.result_url,
            error_message=result.error_message,
        )
        return jsonable_encoder({"job": job})

    video_url = result.result_url
    filename = f"jimeng-rest-job-{job_id}.mp4"

    try:
        repository.bind_asset(job["project_id"], job["shot_id"], "video", video_url)
        asset = repository.create_asset(
            job["project_id"],
            asset_type="video",
            name=filename,
            path=video_url,
            source="jimeng",
        )
    except KeyError as exc:
        job = _fail_video_generation_job(repository, job_id, f"Jimeng bind failed: {exc}")
        raise HTTPException(status_code=502, detail=job["error_message"]) from exc
    job = repository.update_video_generation_job(
        job_id,
        status="completed",
        result_url=result.result_url,
        output_path=asset["path"],
        error_message="",
    )
    return jsonable_encoder({"job": job})


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
):
    provider = (data.provider.strip() or "mock").lower()
    try:
        video_provider = get_video_provider(provider)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

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
    if provider == "jimeng" and not settings.get("enabled", True):
        raise HTTPException(status_code=403, detail="Jimeng provider is disabled.")
    if provider == "jimeng" and (not api_key or not base_url):
        raise HTTPException(status_code=400, detail="Jimeng provider settings are required.")

    try:
        video_bytes = video_provider.generate_video(keyframe_path, api_key, base_url)
    except VideoProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    generated_dir = Path("data") / "uploads" / str(project_id) / "generated" / "videos"
    generated_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{provider}-video-{shot_id}.mp4"
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

    original_filename = file.filename or ""
    _validate_upload_filename(original_filename)
    filename = Path(original_filename).name
    _validate_upload_type(normalized_type, filename, file.content_type or "")
    upload_dir = Path("data") / "uploads" / str(project_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    output_path = upload_dir / filename
    if output_path.exists():
        raise HTTPException(status_code=409, detail="Upload filename already exists.")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Upload file is too large.")
    output_path.write_bytes(content)

    return jsonable_encoder(
        {
            "name": filename,
            "path": output_path.as_posix(),
            "asset_type": normalized_type,
        }
    )


def _validate_jimeng_rest_settings(settings):
    if not settings.get("enabled", True):
        raise HTTPException(status_code=403, detail="Jimeng provider is disabled.")
    if not settings.get("access_key") or not settings.get("secret_key"):
        raise HTTPException(status_code=400, detail="Jimeng REST credentials are required.")
    if not settings.get("endpoint") or not settings.get("model"):
        raise HTTPException(status_code=400, detail="Jimeng REST endpoint and model are required.")
