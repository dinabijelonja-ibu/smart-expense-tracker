import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if not subject:
            raise credentials_exception
        user_id = uuid.UUID(subject)
    except (JWTError, ValueError, TypeError):
        raise credentials_exception from None

    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise credentials_exception
    return user
