from fastapi import APIRouter, Depends
from app.database import get_db, fetch_one, fetch_all
from app.auth import get_current_user

router = APIRouter(prefix="/citizen", tags=["Citizen Dashboard (Layer 6)"])


@router.get("/dashboard")
def citizen_dashboard(user=Depends(get_current_user), conn=Depends(get_db)):
    """Citizen's main dashboard — all KPIs, area stats, category breakdown."""
    uid = user["id"]
    constituency = user.get("home_constituency", "")

    # My submission counts by status
    my_stats = fetch_one(conn, """
        SELECT
            COUNT(*) AS total,
            SUM(status IN ('processing','processed','clustered','categorized','scored')) AS in_progress,
            SUM(status = 'approved') AS approved,
            SUM(status = 'rejected') AS rejected
        FROM raw_submissions WHERE user_id = %s
    """, (uid,))

    # Area stats — how many issues in my constituency
    area_stats = fetch_one(conn, """
        SELECT
            COUNT(*) AS total_issues,
            SUM(status = 'approved') AS approved,
            SUM(status IN ('scored','categorized','clustered')) AS pending,
            SUM(status = 'rejected') AS rejected,
            SUM(status = 'approved' AND mplads_category_code IS NOT NULL) AS completed
        FROM demand_clusters WHERE constituency = %s
    """, (constituency,))

    # Category distribution in my area
    category_stats = fetch_all(conn, """
        SELECT mplads_category_code AS category, COUNT(*) AS count, SUM(unique_users) AS people
        FROM demand_clusters
        WHERE constituency = %s AND mplads_category_code IS NOT NULL
        GROUP BY mplads_category_code
        ORDER BY count DESC
    """, (constituency,))

    return {
        "user": {k: v for k, v in user.items() if k != "password_hash"},
        "my_stats": my_stats,
        "area_stats": area_stats,
        "category_stats": category_stats,
    }


@router.get("/notifications")
def get_notifications(user=Depends(get_current_user), conn=Depends(get_db)):
    """Get citizen's notifications (latest 50)."""
    rows = fetch_all(conn, """
        SELECT * FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC LIMIT 50
    """, (user["id"],))
    return rows


@router.put("/notifications/{notif_id}/read")
def mark_notification_read(notif_id: str, user=Depends(get_current_user), conn=Depends(get_db)):
    from app.database import execute
    execute(conn, """
        UPDATE notifications SET is_read = TRUE, read_at = CURRENT_TIMESTAMP
        WHERE id = %s AND user_id = %s
    """, (notif_id, user["id"]))
    return {"message": "Marked as read"}
