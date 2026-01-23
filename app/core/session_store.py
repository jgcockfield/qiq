"""Session Store - Identity Management

Manages user sessions with name/email capture.
Sessions persist across QIQ interactions and link to EDRs.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any


# Storage directory
SESSIONS_DIR = Path("data/sessions")


def _ensure_sessions_dir():
    """Ensure sessions directory exists."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


def create_session(full_name: str, email: str) -> str:
    """Create a new session with user identity.
    
    Args:
        full_name: User's full name
        email: User's email address
        
    Returns:
        session_id (UUID string)
    """
    _ensure_sessions_dir()
    
    # Generate session ID
    session_id = str(uuid.uuid4())
    
    # Create session record
    session = {
        "session_id": session_id,
        "full_name": full_name,
        "email": email,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_accessed": datetime.now(timezone.utc).isoformat(),
    }
    
    # Save to file
    filepath = SESSIONS_DIR / f"{session_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)
    
    return session_id


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Get session by ID.
    
    Args:
        session_id: UUID of the session
        
    Returns:
        Session dict or None if not found
    """
    filepath = SESSIONS_DIR / f"{session_id}.json"
    
    if not filepath.exists():
        return None
    
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading session {session_id}: {e}")
        return None


def touch_session(session_id: str) -> None:
    """Update last_accessed timestamp for a session.
    
    Args:
        session_id: UUID of the session
    """
    session = get_session(session_id)
    if not session:
        return
    
    session["last_accessed"] = datetime.now(timezone.utc).isoformat()
    
    filepath = SESSIONS_DIR / f"{session_id}.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(session, f, indent=2, ensure_ascii=False)