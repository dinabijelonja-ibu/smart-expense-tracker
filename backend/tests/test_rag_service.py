import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.config import settings
from app.rag import service as rag_service


def test_request_embedding_without_api_key_raises(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_api_key", None)

    with pytest.raises(rag_service.RAGError):
        rag_service._request_embedding("hello")


def test_request_embedding_success(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    captured: dict[str, object] = {}

    def fake_post(url, json, headers, timeout):
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeResponse()

    monkeypatch.setattr(rag_service.httpx, "post", fake_post)

    vector = rag_service._request_embedding("hello")

    assert vector == [0.1, 0.2, 0.3]
    assert captured["json"] == {"model": settings.embedding_model, "input": "hello"}
    assert captured["headers"] == {"Authorization": "Bearer test-key"}


def test_request_embedding_no_data_raises(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {"data": []}

    monkeypatch.setattr(rag_service.httpx, "post", lambda *a, **k: FakeResponse())

    with pytest.raises(rag_service.RAGError):
        rag_service._request_embedding("hello")


def test_build_expense_text_includes_amount_category_description_and_id() -> None:
    expense = SimpleNamespace(id=7, amount=Decimal("12.50"), date=date(2026, 3, 2), description="lunch")

    text = rag_service.build_expense_text(expense, "food")

    assert "12.50" in text
    assert "food" in text
    assert "lunch" in text
    assert "#7" in text
    assert "2026-03-02" in text


def test_build_expense_text_omits_description_when_absent() -> None:
    expense = SimpleNamespace(id=8, amount=Decimal("4.00"), date=date(2026, 3, 2), description=None)

    text = rag_service.build_expense_text(expense, "transport")

    assert text == "On 2026-03-02 you spent 4.00 on transport (expense #8)."


def test_sync_expense_related_embeddings_swallows_rag_errors(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise rag_service.RAGError("embeddings API unavailable")

    monkeypatch.setattr(rag_service, "sync_expense_embedding", boom)
    monkeypatch.setattr(rag_service, "rebuild_daily_embedding", boom)
    monkeypatch.setattr(rag_service, "rebuild_monthly_embedding", boom)

    expense = SimpleNamespace(id=1, user_id=uuid.uuid4(), amount=Decimal("5"), date=date(2026, 1, 1), description=None)

    # Should not raise, even though every sync call fails.
    rag_service.sync_expense_related_embeddings(db=object(), expense=expense, category_name="food")


def test_sync_expense_deletion_swallows_rag_errors(monkeypatch) -> None:
    def boom(*args, **kwargs):
        raise rag_service.RAGError("embeddings API unavailable")

    monkeypatch.setattr(rag_service, "delete_expense_embedding", boom)
    monkeypatch.setattr(rag_service, "rebuild_daily_embedding", boom)
    monkeypatch.setattr(rag_service, "rebuild_monthly_embedding", boom)

    # Should not raise.
    rag_service.sync_expense_deletion(
        db=object(), user_id=uuid.uuid4(), expense_id=1, expense_date=date(2026, 1, 1)
    )
