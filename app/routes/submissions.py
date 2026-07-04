import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from app.database import get_db, fetch_one, fetch_all, execute_returning_id, execute
from app.auth import get_current_user
from app.config import get_settings
from app.pin_resolver import resolve_pin

router = APIRouter(prefix="/submissions", tags=["Submissions (Layer 1)"])


# ── Submit Issue ─────────────────────────────────────────────────────────────

@router.post("/", status_code=201)
async def submit_issue(
    submission_pin_code: str = Form(...),
    input_type: str = Form(...),
    raw_text: str = Form(None),
    raw_language: str = Form("en"),
    audio_file: UploadFile = File(None),
    image_file: UploadFile = File(None),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    """Submit a new development issue. Accepts text, audio, image, or combinations."""

    # Validate PIN code (real India Post API + cache)
    pin_data = resolve_pin(conn, submission_pin_code)
    if not pin_data:
        raise HTTPException(status_code=400, detail="Invalid PIN code — not found in India Post directory")

    # Generate tracking ID
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT COUNT(*) AS cnt FROM raw_submissions WHERE YEAR(created_at) = YEAR(CURRENT_TIMESTAMP)")
    count_row = cursor.fetchone()
    cursor.close()
    seq = (count_row["cnt"] or 0) + 1
    tracking_id = f"PP-2026-{seq:05d}"

    # Insert raw_submission
    sub_id = execute_returning_id(
        conn,
        """INSERT INTO raw_submissions
            (id, tracking_id, user_id, submission_pin_code,
             sub_postal_name, sub_locality, sub_city, sub_district, sub_state, sub_constituency,
             input_type, raw_text, raw_language, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'submitted')""",
        (
            tracking_id, user["id"], submission_pin_code,
            pin_data["postal_name"], pin_data["locality"], pin_data["city"],
            pin_data["district"], pin_data["state"], pin_data["mp_constituency"],
            input_type, raw_text, raw_language,
        ),
    )

    # Save files locally (hackathon — production would use S3)
    settings = get_settings()
    upload_dir = os.path.join(settings.UPLOAD_DIR, sub_id)
    os.makedirs(upload_dir, exist_ok=True)

    async def save_media(file: UploadFile, media_type: str):
        if not file:
            return
        ext = os.path.splitext(file.filename)[1] if file.filename else ""
        file_name = f"{media_type}_{uuid.uuid4().hex[:8]}{ext}"
        file_path = os.path.join(upload_dir, file_name)
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        file_url = f"/uploads/{sub_id}/{file_name}"
        execute_returning_id(
            conn,
            """INSERT INTO submission_media
                (id, raw_submission_id, media_type, file_url, file_name, file_size_bytes, mime_type)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (sub_id, media_type, file_url, file.filename, len(content), file.content_type),
        )

    await save_media(audio_file, "audio")
    await save_media(image_file, "image")

    # Increment user submission count
    execute(conn, "UPDATE users SET total_submissions = total_submissions + 1 WHERE id = %s", (user["id"],))

    # Insert status log
    execute_returning_id(
        conn,
        """INSERT INTO submission_status_log (id, raw_submission_id, user_id, old_status, new_status, changed_by, change_reason)
           VALUES (%s, %s, %s, NULL, 'submitted', 'system', 'New submission received')""",
        (sub_id, user["id"]),
    )

    return {
        "id": sub_id,
        "tracking_id": tracking_id,
        "status": "submitted",
        "message": "Issue submitted successfully. You will be notified as it is processed.",
    }


# ── Get My Submissions ───────────────────────────────────────────────────────

@router.get("/my")
def get_my_submissions(user=Depends(get_current_user), conn=Depends(get_db)):
    """Get all submissions by the current citizen."""
    rows = fetch_all(
        conn,
        """SELECT
                rs.id, rs.tracking_id, rs.input_type, rs.raw_text,
                rs.submission_pin_code, rs.sub_city, rs.sub_district, rs.sub_constituency,
                rs.status, rs.created_at,
                ps.translated_text_en, ps.is_spam,
                dc.id AS cluster_id, dc.representative_text AS cluster_issue,
                dc.submission_count AS similar_count, dc.unique_users,
                dc.mplads_category_code AS category, dc.priority_score, dc.`rank`,
                dc.status AS cluster_status,
                md.decision AS mp_decision, md.reason AS mp_reason,
                md.allocated_amount, md.decided_at
           FROM raw_submissions rs
           LEFT JOIN processed_submissions ps ON ps.raw_submission_id = rs.id
           LEFT JOIN cluster_submissions csub ON csub.raw_submission_id = rs.id
           LEFT JOIN demand_clusters dc ON csub.cluster_id = dc.id
           LEFT JOIN mp_decisions md ON md.cluster_id = dc.id
           WHERE rs.user_id = %s
           ORDER BY rs.created_at DESC""",
        (user["id"],),
    )
    return rows


# ── Get Single Submission Detail ─────────────────────────────────────────────

@router.get("/{submission_id}")
def get_submission(submission_id: str, user=Depends(get_current_user), conn=Depends(get_db)):
    row = fetch_one(
        conn,
        """SELECT rs.*, ps.translated_text_en, ps.is_spam, ps.processing_method
           FROM raw_submissions rs
           LEFT JOIN processed_submissions ps ON ps.raw_submission_id = rs.id
           WHERE rs.id = %s AND rs.user_id = %s""",
        (submission_id, user["id"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")

    # Get media files
    media = fetch_all(conn, "SELECT * FROM submission_media WHERE raw_submission_id = %s", (submission_id,))

    # Get status history
    history = fetch_all(
        conn,
        "SELECT * FROM submission_status_log WHERE raw_submission_id = %s ORDER BY created_at",
        (submission_id,),
    )

    return {**row, "media": media, "status_history": history}


# ── Edit Submission (same-day only, before 11:30 PM) ────────────────────────

@router.put("/{submission_id}")
def edit_submission(
    submission_id: str,
    raw_text: str = Form(None),
    user=Depends(get_current_user),
    conn=Depends(get_db),
):
    """Edit a submission — only allowed on the same day before the nightly scheduler runs."""
    row = fetch_one(
        conn,
        "SELECT * FROM raw_submissions WHERE id = %s AND user_id = %s",
        (submission_id, user["id"]),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")

    if row["status"] != "submitted":
        raise HTTPException(status_code=400, detail="Cannot edit — submission already processed")

    # Check if same day (before 11:30 PM cutoff)
    from datetime import datetime, time
    now = datetime.now()
    created = row["created_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    cutoff = datetime.combine(created.date(), time(23, 30))
    if now > cutoff:
        raise HTTPException(status_code=400, detail="Edit window closed — submissions lock after 11:30 PM on submission day")

    if raw_text is not None:
        execute(conn, "UPDATE raw_submissions SET raw_text = %s WHERE id = %s", (raw_text, submission_id))

    return {"message": "Submission updated", "id": submission_id}
