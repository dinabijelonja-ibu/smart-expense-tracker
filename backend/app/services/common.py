from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category


def normalize_category_name(name: str) -> str:
    return name.strip().lower()


def get_or_create_category(db: Session, *, user_id, category_name: str) -> Category:
    normalized = normalize_category_name(category_name)
    category = db.scalar(select(Category).where(Category.user_id == user_id, Category.name == normalized))
    if category:
        return category

    category = Category(user_id=user_id, name=normalized)
    db.add(category)
    db.flush()
    return category
