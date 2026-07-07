import urllib.request
import urllib.error
import logging
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/scheduler", tags=["Scheduler (Manual Trigger)"])

log = logging.getLogger("scheduler_trigger")


@router.post("/run")
def trigger_pipeline():
    """
    Manually trigger the Layer 2→3→4→5 pipeline.
    Calls the dedicated scheduler Cloud Run service via HTTP.
    """
    from app.config import get_settings
    settings = get_settings()
    start = datetime.now()

    try:
        url = f"{settings.SCHEDULER_SERVICE_URL.rstrip('/')}/run"
        req = urllib.request.Request(url, data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode()
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "status": "triggered",
            "message": f"Scheduler service acknowledged in {elapsed:.1f}s. Pipeline is running in the background.",
            "scheduler_response": body,
        }
    except urllib.error.URLError as e:
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "status": "error",
            "error": f"Could not reach scheduler service: {e.reason}",
            "scheduler_url": settings.SCHEDULER_SERVICE_URL,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@router.get("/status")
def scheduler_status():
    """Check if the scheduler service is reachable."""
    from app.config import get_settings
    settings = get_settings()
    try:
        req = urllib.request.Request(settings.SCHEDULER_SERVICE_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return {"status": "online", "scheduler_url": settings.SCHEDULER_SERVICE_URL, "response": resp.read().decode()}
    except Exception as e:
        return {"status": "offline", "error": str(e)}
