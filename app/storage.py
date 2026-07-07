"""
GCS upload utility.
Falls back to local filesystem when GCS_BUCKET is not set (local dev).
"""
import os
import logging

log = logging.getLogger("storage")


def upload_file(content: bytes, blob_name: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a file to GCS and return its public URL.
    Falls back to saving locally when GCS_BUCKET env var is not configured.
    """
    from app.config import get_settings
    settings = get_settings()

    if settings.GCS_BUCKET:
        from google.cloud import storage as gcs
        client = gcs.Client()
        bucket = client.bucket(settings.GCS_BUCKET)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(content, content_type=content_type)
        log.info(f"Uploaded to GCS: gs://{settings.GCS_BUCKET}/{blob_name}")
        return f"https://storage.googleapis.com/{settings.GCS_BUCKET}/{blob_name}"

    # Local fallback (dev only)
    local_path = os.path.join(settings.UPLOAD_DIR, blob_name)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(content)
    log.info(f"Saved locally: {local_path}")
    return f"/uploads/{blob_name}"
