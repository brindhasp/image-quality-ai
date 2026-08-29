from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from .core.config import settings
from .core.database import init_db
from .api.endpoints import router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-powered image quality assessment and defect detection"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
async def root():
    return {
        "message": "Image Quality AI API",
        "version": settings.APP_VERSION,
        "docs": "/docs"
    }