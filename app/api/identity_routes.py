"""Identity Routes - Gravity Forms Integration

Handles identity capture from Gravity Forms webhook.
Creates session and returns session_id for chatbot redirect.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.core.session_store import create_session


router = APIRouter(prefix="/identity", tags=["identity"])


class IdentityIntakeRequest(BaseModel):
    """Request from Gravity Forms webhook."""
    full_name: str
    email: EmailStr


class IdentityIntakeResponse(BaseModel):
    """Response with session ID and redirect URL."""
    session_id: str
    redirect_url: str


@router.post("/intake", response_model=IdentityIntakeResponse)
async def identity_intake(request: IdentityIntakeRequest):
    """Capture identity from Gravity Forms and create session.
    
    Gravity Forms webhook should POST to this endpoint with:
    - full_name
    - email
    
    Returns session_id and redirect_url for chatbot.
    """
    
    # Validate inputs
    if not request.full_name or not request.full_name.strip():
        raise HTTPException(status_code=400, detail="full_name is required")
    
    if not request.email:
        raise HTTPException(status_code=400, detail="email is required")
    
    # Create session
    session_id = create_session(
        full_name=request.full_name.strip(),
        email=request.email
    )
    
    # Build redirect URL (update domain for production)
    # For local dev: http://127.0.0.1:8000/chat?sid={session_id}
    # For production: https://qiq.gonimbleai.com/chat?sid={session_id}
    redirect_url = f"https://qiq.gonimbleai.com/chat?sid={session_id}"
    
    return IdentityIntakeResponse(
        session_id=session_id,
        redirect_url=redirect_url
    )
