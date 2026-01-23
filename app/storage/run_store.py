"""Run Store - Completed Eligibility Evaluations

Manages completed eligibility runs.
One run = one completed evaluation with all results.
Links to session for name/email identity.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List


# Storage directory
RUNS_DIR = Path("data/runs")


def _ensure_runs_dir():
    """Ensure runs directory exists."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def save_run(run: Dict[str, Any]) -> str:
    """Save a completed run.
    
    Args:
        run: Run data dict containing:
            - session_id (required)
            - eligibility_status (required)
            - summary
            - primary_reason
            - answers_log
            - pdf_url (nullable)
            - edr_id (nullable)
            
    Returns:
        run_id (UUID string)
    """
    _ensure_runs_dir()
    
    # Generate run ID if not provided
    run_id = run.get("run_id") or str(uuid.uuid4())
    
    # Add metadata
    run_data = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **run,
    }
    
    # Save to file
    filepath = RUNS_DIR / f"{run_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(run_data, f, indent=2, ensure_ascii=False)
    
    return run_id


def get_run(run_id: str) -> Optional[Dict[str, Any]]:
    """Get run by ID.
    
    Args:
        run_id: UUID of the run
        
    Returns:
        Run dict or None if not found
    """
    filepath = RUNS_DIR / f"{run_id}.json"
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading run {run_id}: {e}")
        return None


def list_runs(
    limit: int = 50,
    offset: int = 0,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """List runs with pagination and filtering.
    
    Args:
        limit: Max number of runs to return
        offset: Number of runs to skip
        filters: Optional filters (e.g., {"eligibility_status": "not_eligible"})
        
    Returns:
        List of run dicts, sorted by created_at descending
    """
    _ensure_runs_dir()
    
    runs = []
    
    # Load all runs
    for filepath in RUNS_DIR.glob("*.json"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                run = json.load(f)
                
                # Apply filters if provided
                if filters:
                    match = True
                    for key, value in filters.items():
                        if run.get(key) != value:
                            match = False
                            break
                    if not match:
                        continue
                
                runs.append(run)
                
        except Exception as e:
            print(f"Error reading run file {filepath}: {e}")
            continue
    
    # Sort by created_at descending (most recent first)
    runs.sort(
        key=lambda x: x.get("created_at", ""),
        reverse=True
    )
    
    # Apply pagination
    return runs[offset:offset + limit]