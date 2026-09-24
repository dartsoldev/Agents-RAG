"""Hash passwords, issue revocable sessions and enforce server-side staff roles."""

import hashlib
import hmac
import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import LoginSession, User, now
from database.session import get_db


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return f"{salt}${value}"


def verify_password(password: str, stored: str) -> bool:
    salt, expected = stored.split("$")
    actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(actual, expected)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("arav_session", "")
    session = db.scalar(
        select(LoginSession).where(
            LoginSession.token_hash == token_digest(token),
            LoginSession.expires_at > now(),
        )
    )
    user = db.get(User, session.user_id) if session else None
    if not user or not user.active:
        raise HTTPException(401, "Please sign in")
    return user


def require_reviewer(user: User):
    if user.role not in {"admin", "attorney"}:
        raise HTTPException(403, "Attorney or administrator approval required")


def require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(403, "Administrator access required")
