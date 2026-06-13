from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .video_workbench.api import router as video_workbench_router


app = FastAPI(title="AI Video Workbench API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
