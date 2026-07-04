import subprocess
import os
import logging
import json
from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/scheduler", tags=["Scheduler (Manual Trigger)"])

log = logging.getLogger("scheduler_trigger")

SCHEDULER_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "backend-scheduler"))


@router.post("/run")
def trigger_pipeline():
    """
    Manually trigger the Layer 2→3→4→5 pipeline.
    Runs the scheduler as a subprocess so there's no import conflict.
    """
    start = datetime.now()

    try:
        result = subprocess.run(
            ["python", "-c", """
import sys, os
sys.path.insert(0, '.')
from pipeline.db import get_connection
from pipeline.layer2_processing import process_submissions
from pipeline.layer3_clustering import cluster_and_categorize, _categorize_clusters
from pipeline.layer4_enrichment import enrich_clusters
from pipeline.layer5_scoring import score_and_rank

conn = get_connection()
l2 = process_submissions(conn)
l3 = cluster_and_categorize(conn)
# Also re-categorize any stuck clusters
_categorize_clusters(conn)
l4 = enrich_clusters(conn)
l5 = score_and_rank(conn)
print(f"RESULT:{l2},{l3},{l4},{l5}")
conn.close()
"""],
            cwd=SCHEDULER_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )

        elapsed = (datetime.now() - start).total_seconds()

        # Parse output for layer counts
        output = result.stdout + result.stderr
        layers = {}
        for line in output.split("\n"):
            if line.startswith("RESULT:"):
                parts = line.replace("RESULT:", "").split(",")
                if len(parts) == 4:
                    layers = {"layer2_processed": int(parts[0]), "layer3_clustered": int(parts[1]),
                              "layer4_enriched": int(parts[2]), "layer5_scored": int(parts[3])}
            elif "Layer 2:" in line:
                layers.setdefault("layer2_processed", _extract_count(line))
            elif "Layer 3:" in line and "Clustered" in line:
                layers.setdefault("layer3_clustered", _extract_count(line))
            elif "Layer 4:" in line and "Enriched" in line:
                layers.setdefault("layer4_enriched", _extract_count(line))
            elif "Layer 5:" in line and "Scored" in line:
                layers.setdefault("layer5_scored", _extract_count(line))

        return {
            "status": "success" if result.returncode == 0 else "error",
            "layers": layers,
            "elapsed_seconds": round(elapsed, 2),
            "message": f"Pipeline complete in {elapsed:.1f}s",
            "output": output[-1500:] if output else "",
            "errors": result.stderr[-500:] if result.stderr else "",
        }

    except subprocess.TimeoutExpired:
        return {"status": "error", "error": "Pipeline timed out (120s limit)"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _extract_count(line: str) -> int:
    """Extract number from lines like 'Layer 2: Processed 3/3 submissions'."""
    import re
    m = re.search(r'(\d+)', line.split(":")[-1])
    return int(m.group(1)) if m else 0
