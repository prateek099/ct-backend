"""Tests for foundation helpers — require_admin + get_owned_or_404."""
import pytest

from app.api.deps import get_owned_or_404
from app.core.exceptions import NotFoundError
from app.models.user import User


def test_require_admin_rejects_non_admin(client, auth_headers):
    # /users/ list is guarded by require_admin.
    res = client.get("/api/v1/users/", headers=auth_headers)
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "FORBIDDEN"


def test_require_admin_allows_admin(client, admin_auth_headers):
    res = client.get("/api/v1/users/", headers=admin_auth_headers)
    assert res.status_code == 200


def test_get_owned_or_404_returns_row_for_owner(client, auth_headers):
    from tests.conftest import TestingSession

    db = TestingSession()
    try:
        owner = db.query(User).filter(User.email == "test@example.com").one()
        # Create a second user as "not owner"
        other = User(
            name="Other",
            email="other@example.com",
            hashed_password="x",
            is_active=True,
        )
        db.add(other)
        db.commit()
        db.refresh(other)

        # Own user_id matches → returns user.
        # Prateek: we use User itself as the owned resource where user_id_attr='id'
        # to exercise the helper without introducing a real owned model yet.
        row = get_owned_or_404(db, User, owner.id, owner, user_id_attr="id")
        assert row.id == owner.id

        # Other user's id → NotFoundError, not Forbidden (don't leak existence).
        with pytest.raises(NotFoundError):
            get_owned_or_404(db, User, other.id, owner, user_id_attr="id")
    finally:
        db.close()
