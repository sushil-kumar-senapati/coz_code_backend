from fastapi import APIRouter, Depends
from app.database import get_db, fetch_one, fetch_all
from app.auth import get_current_user

router = APIRouter(prefix="/citizen", tags=["Citizen Dashboard (Layer 6)"])


@router.get("/dashboard")
def citizen_dashboard(user=Depends(get_current_user), conn=Depends(get_db)):
    """Citizen's full dashboard — rich KPIs, area stats, category breakdown, trends."""
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
            SUM(status IN ('scored','categorized','clustered','enriched')) AS pending,
            SUM(status = 'rejected') AS rejected,
            SUM(unique_users) AS total_people,
            COUNT(DISTINCT district) AS districts_covered
        FROM demand_clusters WHERE constituency = %s
    """, (constituency,))

    # Category distribution in my area
    category_stats = fetch_all(conn, """
        SELECT mplads_category_code AS category, COUNT(*) AS count,
               SUM(unique_users) AS people,
               ROUND(AVG(priority_score), 1) AS avg_score,
               SUM(status = 'closed' AND id IN (SELECT cluster_id FROM mp_decisions WHERE decision='approved')) AS approved_count
        FROM demand_clusters
        WHERE constituency = %s AND mplads_category_code IS NOT NULL
        GROUP BY mplads_category_code
        ORDER BY people DESC
    """, (constituency,))

    # My submissions with cluster info (similar count, category, score)
    my_submissions_enriched = fetch_all(conn, """
        SELECT rs.id, rs.tracking_id, rs.input_type, rs.raw_text, rs.status, rs.created_at,
               rs.sub_city, rs.sub_district, rs.submission_pin_code,
               ps.translated_text_en,
               dc.mplads_category_code AS category, dc.unique_users AS similar_count,
               dc.priority_score, dc.`rank` AS cluster_rank
        FROM raw_submissions rs
        LEFT JOIN processed_submissions ps ON ps.raw_submission_id = rs.id
        LEFT JOIN cluster_submissions csub ON csub.raw_submission_id = rs.id
        LEFT JOIN demand_clusters dc ON csub.cluster_id = dc.id
        WHERE rs.user_id = %s
        ORDER BY rs.created_at DESC
    """, (uid,))

    # Top localities with most issues in my constituency
    locality_stats = fetch_all(conn, """
        SELECT rs.sub_city AS locality, rs.submission_pin_code AS pin_code,
               COUNT(*) AS issue_count, COUNT(DISTINCT rs.user_id) AS people
        FROM raw_submissions rs
        WHERE rs.sub_constituency = %s
        GROUP BY rs.sub_city, rs.submission_pin_code
        ORDER BY issue_count DESC LIMIT 10
    """, (constituency,))

    # Submission trend (last 30 days grouped by date)
    submission_trend = fetch_all(conn, """
        SELECT DATE(created_at) AS date, COUNT(*) AS count
        FROM raw_submissions
        WHERE sub_constituency = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date
    """, (constituency,))

    # Unread notification count
    unread_count = fetch_one(conn, """
        SELECT COUNT(*) AS count FROM notifications
        WHERE user_id = %s AND is_read = FALSE
    """, (uid,))

    # Budget info for my constituency
    budget = fetch_one(conn, """
        SELECT total_budget, total_allocated, remaining, approved_count, rejected_count, pending_count
        FROM budget_tracker
        WHERE constituency = %s ORDER BY financial_year DESC LIMIT 1
    """, (constituency,))

    # Top scored issues in my area (what's being prioritized)
    top_issues = fetch_all(conn, """
        SELECT representative_text, mplads_category_code AS category,
               priority_score, `rank`, unique_users, status, estimated_cost
        FROM demand_clusters
        WHERE constituency = %s AND priority_score IS NOT NULL
        ORDER BY `rank` ASC LIMIT 5
    """, (constituency,))

    return {
        "user": {k: v for k, v in user.items() if k != "password_hash"},
        "my_stats": my_stats,
        "area_stats": area_stats,
        "category_stats": category_stats,
        "my_submissions": my_submissions_enriched,
        "locality_stats": locality_stats,
        "submission_trend": submission_trend,
        "unread_notifications": unread_count.get("count", 0) if unread_count else 0,
        "budget": budget,
        "top_issues": top_issues,
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
