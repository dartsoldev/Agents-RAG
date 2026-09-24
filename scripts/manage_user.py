"""Create staff, reset passwords or deactivate accounts with direct server administrator access."""

import argparse
import getpass

from sqlalchemy import delete, select

from backend.security import hash_password
from database.models import LoginSession, User
from database.session import SessionLocal
from sub_agents.common import audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["create", "reset-password", "deactivate", "activate"])
    parser.add_argument("email")
    parser.add_argument("--name", default="Staff member")
    parser.add_argument("--role", choices=["admin", "attorney", "paralegal"], default="paralegal")
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == args.email.lower()))
        if args.action == "create" and user:
            raise SystemExit("Account already exists")
        if args.action != "create" and not user:
            raise SystemExit("Account not found")
        if args.action in {"create", "reset-password"}:
            password = getpass.getpass("New password (minimum 16 characters): ")
            confirm = getpass.getpass("Confirm password: ")
            if len(password) < 16 or password != confirm:
                raise SystemExit("Passwords must match and contain at least 16 characters")
            if not user:
                user = User(
                    email=args.email.lower(),
                    name=args.name,
                    role=args.role,
                    password_hash="",
                )
                db.add(user)
                db.flush()
            user.password_hash = hash_password(password)
        else:
            user.active = args.action == "activate"
        db.execute(delete(LoginSession).where(LoginSession.user_id == user.id))
        audit(db, None, "server administrator", f"User {args.action}", user.email)
        db.commit()
    print("Account updated. Existing sessions revoked.")


if __name__ == "__main__":
    main()
