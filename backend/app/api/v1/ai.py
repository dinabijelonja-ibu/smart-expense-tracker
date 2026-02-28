from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai.orchestrator import run_ai_chat
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ai import AIChatRequest, AIChatResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AIChatResponse)
def ai_chat_endpoint(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIChatResponse:
    response = run_ai_chat(db=db, user_id=current_user.id, user_message=payload.message)
    return AIChatResponse(response=response)
