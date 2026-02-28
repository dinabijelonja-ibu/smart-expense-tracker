from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.orchestrator import run_ai_chat
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.rag.service import RAGError, rebuild_monthly_embedding
from app.schemas.ai import AIChatRequest, AIChatResponse, RebuildEmbeddingsRequest, RebuildEmbeddingsResponse

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/chat", response_model=AIChatResponse)
def ai_chat_endpoint(
    payload: AIChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIChatResponse:
    response = run_ai_chat(db=db, user_id=current_user.id, user_message=payload.message)
    return AIChatResponse(response=response)


@router.post("/embeddings/rebuild", response_model=RebuildEmbeddingsResponse)
def rebuild_embeddings_endpoint(
    payload: RebuildEmbeddingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RebuildEmbeddingsResponse:
    target: date | None = None
    if payload.month:
        try:
            year, month = payload.month.split("-")
            target = date(int(year), int(month), 1)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="month must be in YYYY-MM format",
            ) from None

    try:
        result = rebuild_monthly_embedding(db, user_id=current_user.id, target=target)
    except RAGError:
        return RebuildEmbeddingsResponse(id=0, status="error", content="Embedding generation is unavailable")

    return RebuildEmbeddingsResponse(**result)
