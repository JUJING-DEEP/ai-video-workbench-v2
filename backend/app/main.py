import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .video_workbench.api import router as video_workbench_router


app = FastAPI(title="AI Video Workbench API", version="0.1.0")

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
    return {"message": "AI Video Workbench API is running", "version": "0.1.0"}


@app.get("/health")
async def health():
    return {"status": "ok"}
