from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from app.database import get_db, fetch_one, fetch_all, execute, execute_returning_id
from app.auth import require_role

router = APIRouter(prefix="/mp", tags=["MP Dashboard (Layer 6)"])


# ── Request Models ───────────────────────────────────────────────────────────

class DecisionRequest(BaseModel):
    decision: str = Field(..., pattern="^(approved|rejected)$")
    reason: str = Field(..., min_length=10)
    allocated_amount: float | None = None
    financial_year: str | None = None

    def get_financial_year(self) -> str:
        if self.financial_year:
            return self.financial_year
        from app.config import get_current_financial_year
        return get_current_financial_year()


# ── MP Dashboard KPIs ────────────────────────────────────────────────────────

@router.get("/dashboard")
def mp_dashboard(user=Depends(require_role("mp")), conn=Depends(get_db)):
    constituency = user.get("home_constituency", "")

    # Cluster KPIs
    cluster_kpis = fetch_one(conn, """
        SELECT
            COUNT(*) AS total_clusters,
            SUM(status IN ('scored','enriched','categorized')) AS pending_review,
            SUM(status = 'under_review') AS under_review,
            SUM(status = 'closed' AND id IN (SELECT cluster_id FROM mp_decisions WHERE decision='approved')) AS approved,
            SUM(status = 'closed' AND id IN (SELECT cluster_id FROM mp_decisions WHERE decision='rejected')) AS rejected,
            SUM(unique_users) AS total_citizens,
            COUNT(DISTINCT district) AS districts_covered,
            ROUND(AVG(priority_score), 1) AS avg_score
        FROM demand_clusters WHERE constituency = %s
    """, (constituency,))

    # Total unique citizens who submitted
    citizen_count = fetch_one(conn, """
        SELECT COUNT(DISTINCT user_id) AS count FROM raw_submissions WHERE sub_constituency = %s
    """, (constituency,))

    # Total submissions
    submission_stats = fetch_one(conn, """
        SELECT COUNT(*) AS total, SUM(input_type = 'text') AS text_count,
               SUM(input_type = 'audio') AS audio_count, SUM(input_type = 'image') AS image_count,
               SUM(input_type IN ('text_audio','text_image','audio_image','text_audio_image')) AS multi_count
        FROM raw_submissions WHERE sub_constituency = %s
    """, (constituency,))

    # Budget
    budget = fetch_one(conn, """
        SELECT * FROM budget_tracker
        WHERE constituency = %s
        ORDER BY financial_year DESC LIMIT 1
    """, (constituency,))

    # Category distribution with approval rate & avg score
    category_stats = fetch_all(conn, """
        SELECT mplads_category_code AS category, COUNT(*) AS count,
               SUM(unique_users) AS people,
               ROUND(AVG(priority_score), 1) AS avg_score,
               SUM(status = 'closed' AND id IN (SELECT cluster_id FROM mp_decisions WHERE decision='approved')) AS approved_count,
               SUM(status = 'closed' AND id IN (SELECT cluster_id FROM mp_decisions WHERE decision='rejected')) AS rejected_count,
               SUM(CASE WHEN estimated_cost IS NOT NULL THEN estimated_cost ELSE 0 END) AS total_estimated_cost
        FROM demand_clusters
        WHERE constituency = %s AND mplads_category_code IS NOT NULL
        GROUP BY mplads_category_code ORDER BY people DESC
    """, (constituency,))

    # Top localities / PIN codes with most issues
    locality_stats = fetch_all(conn, """
        SELECT rs.sub_city AS locality, rs.submission_pin_code AS pin_code,
               rs.sub_district AS district,
               COUNT(*) AS issue_count, COUNT(DISTINCT rs.user_id) AS people
        FROM raw_submissions rs
        WHERE rs.sub_constituency = %s
        GROUP BY rs.sub_city, rs.submission_pin_code, rs.sub_district
        ORDER BY issue_count DESC LIMIT 15
    """, (constituency,))

    # Top active citizens (most submissions)
    top_submitters = fetch_all(conn, """
        SELECT u.name, u.phone, u.home_city, u.total_submissions,
               COUNT(rs.id) AS constituency_submissions
        FROM users u
        JOIN raw_submissions rs ON rs.user_id = u.id
        WHERE rs.sub_constituency = %s AND u.role = 'user'
        GROUP BY u.id, u.name, u.phone, u.home_city, u.total_submissions
        ORDER BY constituency_submissions DESC LIMIT 10
    """, (constituency,))

    # Submission trend (last 30 days)
    submission_trend = fetch_all(conn, """
        SELECT DATE(created_at) AS date, COUNT(*) AS count
        FROM raw_submissions
        WHERE sub_constituency = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        GROUP BY DATE(created_at) ORDER BY date
    """, (constituency,))

    # Score distribution (how many clusters in each score range)
    score_distribution = fetch_all(conn, """
        SELECT
            CASE
                WHEN priority_score >= 8 THEN '8-10 (Critical)'
                WHEN priority_score >= 6 THEN '6-8 (High)'
                WHEN priority_score >= 4 THEN '4-6 (Medium)'
                WHEN priority_score >= 2 THEN '2-4 (Low)'
                ELSE '0-2 (Minimal)'
            END AS score_range,
            COUNT(*) AS count
        FROM demand_clusters
        WHERE constituency = %s AND priority_score IS NOT NULL
        GROUP BY score_range
        ORDER BY MIN(priority_score) DESC
    """, (constituency,))

    # Budget utilization by category (approved amounts)
    budget_by_category = fetch_all(conn, """
        SELECT dc.mplads_category_code AS category,
               SUM(md.allocated_amount) AS allocated,
               COUNT(md.id) AS works_count
        FROM mp_decisions md
        JOIN demand_clusters dc ON md.cluster_id = dc.id
        WHERE md.constituency = %s AND md.decision = 'approved'
        GROUP BY dc.mplads_category_code ORDER BY allocated DESC
    """, (constituency,))

    # Financial year trends
    yearly_trends = fetch_all(conn, """
        SELECT financial_year,
               SUM(amount_sanctioned) AS allocated,
               SUM(amount_spent) AS spent,
               SUM(works_count) AS works,
               SUM(works_completed) AS completed
        FROM mplads_fund_history
        WHERE constituency = %s
        GROUP BY financial_year ORDER BY financial_year
    """, (constituency,))

    # SC/ST compliance (22.5% mandate)
    sc_st_data = fetch_one(conn, """
        SELECT
            SUM(CASE WHEN ds.data_json IS NOT NULL THEN 1 ELSE 0 END) AS data_available,
            COUNT(*) AS total_clusters
        FROM demand_clusters dc
        LEFT JOIN data_sources ds ON ds.source_type = 'census_village' AND ds.district = dc.district
        WHERE dc.constituency = %s
    """, (constituency,))

    # Input type distribution
    input_type_stats = fetch_all(conn, """
        SELECT input_type, COUNT(*) AS count
        FROM raw_submissions WHERE sub_constituency = %s
        GROUP BY input_type ORDER BY count DESC
    """, (constituency,))

    # Unique PIN codes
    pin_count = fetch_one(conn, """
        SELECT COUNT(DISTINCT submission_pin_code) AS count
        FROM raw_submissions WHERE sub_constituency = %s
    """, (constituency,))

    return {
        "constituency": constituency,
        "mp_name": user.get("name", ""),
        "cluster_kpis": cluster_kpis,
        "citizen_count": citizen_count.get("count", 0) if citizen_count else 0,
        "submission_stats": submission_stats,
        "budget": budget,
        "category_stats": category_stats,
        "locality_stats": locality_stats,
        "top_submitters": top_submitters,
        "submission_trend": submission_trend,
        "score_distribution": score_distribution,
        "budget_by_category": budget_by_category,
        "yearly_trends": yearly_trends,
        "input_type_stats": input_type_stats,
        "pin_count": pin_count.get("count", 0) if pin_count else 0,
    }


# ── Ranked Priorities (what MP reviews) ──────────────────────────────────────

@router.get("/clusters")
def get_ranked_clusters(
    status: str = None,
    category: str = None,
    user=Depends(require_role("mp")),
    conn=Depends(get_db),
):
    constituency = user.get("home_constituency", "")
    query = """
        SELECT dc.*, cs.priority_score_10, cs.score_explanation,
               cs.normalized_demand, cs.normalized_severity, cs.normalized_vulnerability,
               cs.normalized_infra_gap, cs.normalized_feasibility, cs.normalized_recency,
               cs.normalized_hist_bias
        FROM demand_clusters dc
        LEFT JOIN cluster_scores cs ON cs.cluster_id = dc.id
        WHERE dc.constituency = %s
    """
    params = [constituency]

    if status:
        query += " AND dc.status = %s"
        params.append(status)
    if category:
        query += " AND dc.mplads_category_code = %s"
        params.append(category)

    query += " ORDER BY dc.`rank` ASC, dc.priority_score DESC"
    return fetch_all(conn, query, tuple(params))


# ── Single Cluster Detail ───────────────────────────────────────────────────

@router.get("/clusters/{cluster_id}")
def get_cluster_detail(cluster_id: str, user=Depends(require_role("mp")), conn=Depends(get_db)):
    cluster = fetch_one(conn, "SELECT * FROM demand_clusters WHERE id = %s", (cluster_id,))
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    # Score breakdown
    score = fetch_one(conn, "SELECT * FROM cluster_scores WHERE cluster_id = %s", (cluster_id,))

    # All submissions in this cluster with media files
    submissions = fetch_all(conn, """
        SELECT csub.similarity_score, csub.is_representative,
               rs.id AS submission_id, rs.tracking_id, rs.input_type,
               rs.raw_text, rs.raw_language,
               rs.submission_pin_code, rs.sub_city, rs.sub_district,
               rs.sub_constituency, rs.created_at,
               ps.translated_text_en, ps.original_text, ps.processing_method,
               u.name AS user_name, u.phone AS user_phone
        FROM cluster_submissions csub
        JOIN raw_submissions rs ON csub.raw_submission_id = rs.id
        JOIN users u ON csub.user_id = u.id
        LEFT JOIN processed_submissions ps ON ps.raw_submission_id = rs.id
        WHERE csub.cluster_id = %s
        ORDER BY rs.created_at DESC
    """, (cluster_id,))

    # Get media files for each submission
    for sub in submissions:
        media = fetch_all(conn, """
            SELECT media_type, file_url, file_name, file_size_bytes, mime_type, duration_sec
            FROM submission_media WHERE raw_submission_id = %s
        """, (sub["submission_id"],))
        sub["media"] = media

    # Existing decisions
    decisions = fetch_all(conn, """
        SELECT * FROM mp_decisions WHERE cluster_id = %s ORDER BY decided_at DESC
    """, (cluster_id,))

    return {**cluster, "score": score, "submissions": submissions, "decisions": decisions}


# ── MP Approve / Reject ──────────────────────────────────────────────────────

@router.post("/clusters/{cluster_id}/decide")
def decide_cluster(
    cluster_id: str,
    req: DecisionRequest,
    user=Depends(require_role("mp")),
    conn=Depends(get_db),
):
    cluster = fetch_one(conn, "SELECT * FROM demand_clusters WHERE id = %s", (cluster_id,))
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    constituency = user.get("home_constituency", "")

    # Insert decision
    fy = req.get_financial_year()
    execute_returning_id(
        conn,
        """INSERT INTO mp_decisions (id, cluster_id, mp_user_id, decision, reason, allocated_amount, financial_year, constituency)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (cluster_id, user["id"], req.decision, req.reason, req.allocated_amount, fy, constituency),
    )

    # Update cluster status
    new_status = "closed"
    execute(conn, "UPDATE demand_clusters SET status = %s WHERE id = %s", (new_status, cluster_id))

    # Update budget tracker if approved
    if req.decision == "approved" and req.allocated_amount:
        execute(conn, """
            UPDATE budget_tracker
            SET total_allocated = total_allocated + %s,
                remaining = total_budget - (total_allocated + %s),
                approved_count = approved_count + 1,
                pending_count = GREATEST(pending_count - 1, 0)
            WHERE constituency = %s AND financial_year = %s
        """, (req.allocated_amount, req.allocated_amount, constituency, fy))
    elif req.decision == "rejected":
        execute(conn, """
            UPDATE budget_tracker
            SET rejected_count = rejected_count + 1,
                pending_count = GREATEST(pending_count - 1, 0)
            WHERE constituency = %s AND financial_year = %s
        """, (constituency, fy))

    # Update all submissions in this cluster
    execute(conn, """
        UPDATE raw_submissions rs
        JOIN cluster_submissions csub ON csub.raw_submission_id = rs.id
        SET rs.status = %s
        WHERE csub.cluster_id = %s
    """, (req.decision, cluster_id))

    # Notify all citizens in this cluster
    citizens = fetch_all(conn, """
        SELECT DISTINCT csub.user_id, rs.tracking_id
        FROM cluster_submissions csub
        JOIN raw_submissions rs ON csub.raw_submission_id = rs.id
        WHERE csub.cluster_id = %s
    """, (cluster_id,))

    notif_type = "cluster_approved" if req.decision == "approved" else "cluster_rejected"
    title = f"Issue {'Approved' if req.decision == 'approved' else 'Rejected'}!"
    for c in citizens:
        execute_returning_id(
            conn,
            """INSERT INTO notifications (id, user_id, cluster_id, notification_type, title, message)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (c["user_id"], cluster_id, notif_type, title,
             f"Your issue ({c['tracking_id']}) has been {req.decision} by the MP. Reason: {req.reason}"),
        )

    return {"message": f"Cluster {req.decision}", "cluster_id": cluster_id}


# ── Recent Decisions ─────────────────────────────────────────────────────────

@router.get("/decisions")
def get_recent_decisions(user=Depends(require_role("mp")), conn=Depends(get_db)):
    constituency = user.get("home_constituency", "")
    return fetch_all(conn, """
        SELECT md.*, dc.representative_text, dc.mplads_category_code, dc.unique_users
        FROM mp_decisions md
        JOIN demand_clusters dc ON md.cluster_id = dc.id
        WHERE md.constituency = %s
        ORDER BY md.decided_at DESC LIMIT 20
    """, (constituency,))


# ── Budget Overview ──────────────────────────────────────────────────────────

@router.get("/budget")
def get_budget(user=Depends(require_role("mp")), conn=Depends(get_db)):
    constituency = user.get("home_constituency", "")
    current = fetch_one(conn, """
        SELECT * FROM budget_tracker WHERE constituency = %s ORDER BY financial_year DESC LIMIT 1
    """, (constituency,))
    history = fetch_all(conn, """
        SELECT financial_year, SUM(amount_sanctioned) AS allocated, SUM(amount_spent) AS spent,
               SUM(works_count) AS works, SUM(works_completed) AS completed
        FROM mplads_fund_history WHERE constituency = %s
        GROUP BY financial_year ORDER BY financial_year
    """, (constituency,))
    return {"current": current, "history": history}
