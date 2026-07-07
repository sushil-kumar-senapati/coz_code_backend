from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import get_settings
from app.routes import auth, submissions, citizen, mp, scheduler

settings = get_settings()

app = FastAPI(
    title="People's Priorities AI — API",
    description="Layer 1 (Data Intake) + Layer 6 (Dashboard & Approval) API service",
    version="1.0.0",
)

# CORS — origins loaded from CORS_ORIGINS env var (space-separated)
# allow_origin_regex also permits any Cloud Run URL as a safety net
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(),
    allow_origin_regex=r"https://.*\.run\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files (hackathon — production uses S3)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Register routes
app.include_router(auth.router)
app.include_router(submissions.router)
app.include_router(citizen.router)
app.include_router(mp.router)
app.include_router(scheduler.router)


@app.get("/")
def root():
    return {
        "service": "People's Priorities AI — API",
        "version": "1.0.0",
        "layers": "Layer 1 (Data Intake) + Layer 6 (Dashboard & Approval)",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    from app.database import get_pool
    try:
        conn = get_pool().get_connection()
        conn.ping(reconnect=True)
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
