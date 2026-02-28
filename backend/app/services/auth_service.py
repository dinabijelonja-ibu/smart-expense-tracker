from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User


def register_user(db: Session, *, email: str, password: str) -> str:
    existing_user = db.scalar(select(User).where(User.email == email.lower()))
    if existing_user:
        raise ValueError("Email is already registered")

    user = User(email=email.lower(), password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    return create_access_token(str(user.id))


def login_user(db: Session, *, email: str, password: str) -> str:
    user = db.scalar(select(User).where(User.email == email.lower()))
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("Invalid email or password")

    return create_access_token(str(user.id))
