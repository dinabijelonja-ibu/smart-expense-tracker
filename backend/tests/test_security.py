from app.core.security import hash_password, verify_password


def test_hash_password_and_verify_success() -> None:
    password = "password123"
    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True


def test_verify_password_failure_with_wrong_password() -> None:
    password_hash = hash_password("password123")

    assert verify_password("wrong-password", password_hash) is False
