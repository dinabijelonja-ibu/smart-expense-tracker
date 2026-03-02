from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.api.v1 import auth as auth_routes
from app.api.v1 import expenses as expense_routes
from app.db.session import get_db
from app.main import app


def test_register_success(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_register_user(db, *, email: str, password: str) -> str:
        captured["db"] = db
        captured["email"] = email
        captured["password"] = password
        return "token-abc"

    monkeypatch.setattr(auth_routes, "register_user", fake_register_user)

    sentinel_db = object()

    def override_get_db():
        yield sentinel_db

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/register",
                json={"email": "new.user@example.com", "password": "password123"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json() == {"access_token": "token-abc", "token_type": "bearer"}
    assert captured == {
        "db": sentinel_db,
        "email": "new.user@example.com",
        "password": "password123",
    }


def test_login_invalid_credentials_returns_401(monkeypatch) -> None:
    def fake_login_user(db, *, email: str, password: str) -> str:
        raise ValueError("Invalid credentials")

    monkeypatch.setattr(auth_routes, "login_user", fake_login_user)

    def override_get_db():
        yield object()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/auth/login",
                json={"email": "new.user@example.com", "password": "wrong-password"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_create_expense_success(monkeypatch) -> None:
    test_user = SimpleNamespace(id=uuid4())
    sentinel_db = object()

    def override_get_db():
        yield sentinel_db

    def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    captured: dict[str, object] = {}

    def fake_create_expense(db, *, user_id, amount, category_name, description, expense_date):
        captured["db"] = db
        captured["user_id"] = user_id
        captured["amount"] = amount
        captured["category_name"] = category_name
        captured["description"] = description
        captured["expense_date"] = expense_date
        return SimpleNamespace(id=101, category_id=7)

    def fake_get_expense_category_map(db, expenses):
        return {7: "food"}

    def fake_serialize_expense(expense, category_name: str):
        return {
            "id": expense.id,
            "amount": 11.0,
            "category": category_name,
            "description": "tea",
            "date": date(2026, 3, 2),
            "created_at": datetime(2026, 3, 2, 12, 0, 0, tzinfo=timezone.utc),
        }

    monkeypatch.setattr(expense_routes, "create_expense", fake_create_expense)
    monkeypatch.setattr(expense_routes, "get_expense_category_map", fake_get_expense_category_map)
    monkeypatch.setattr(expense_routes, "serialize_expense", fake_serialize_expense)

    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/expenses",
                json={"amount": 11, "category": "food", "description": "tea", "date": "2026-03-02"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 101
    assert data["category"] == "food"
    assert data["amount"] == 11.0
    assert captured == {
        "db": sentinel_db,
        "user_id": test_user.id,
        "amount": 11.0,
        "category_name": "food",
        "description": "tea",
        "expense_date": date(2026, 3, 2),
    }


def test_delete_expense_success(monkeypatch) -> None:
    test_user = SimpleNamespace(id=uuid4())

    def override_get_db():
        yield object()

    def override_current_user():
        return test_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    def fake_delete_expense(db, *, user_id, expense_id):
        return user_id == test_user.id and expense_id == 101

    monkeypatch.setattr(expense_routes, "delete_expense", fake_delete_expense)

    try:
        with TestClient(app) as client:
            response = client.delete("/api/v1/expenses/101")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 204
    assert response.content == b""


def test_delete_expense_not_found_returns_404(monkeypatch) -> None:
    def override_get_db():
        yield object()

    def override_current_user():
        return SimpleNamespace(id=uuid4())

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    def fake_delete_expense(db, *, user_id, expense_id):
        return False

    monkeypatch.setattr(expense_routes, "delete_expense", fake_delete_expense)

    try:
        with TestClient(app) as client:
            response = client.delete("/api/v1/expenses/999")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "Expense not found"