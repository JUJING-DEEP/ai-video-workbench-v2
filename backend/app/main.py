import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .video_workbench.api import router as video_workbench_router
from .video_workbench.api import success_response

API_VERSION = "1.0.0-beta.1"

app = FastAPI(title="AI Video Workbench API", version=API_VERSION)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "VIDEO_WORKBENCH_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video_workbench_router)


@app.get("/")
async def root():
    return success_response(
        {"message": "AI Video Workbench API is running", "version": API_VERSION}
    )


@app.get("/health")
async def health():
    return success_response({"status": "ok"})
