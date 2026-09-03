"""Restore the configured administrator credential after legacy HR import."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings
from app.database import SessionLocal
from app.models import User
from app.security import hash_password


async def repair(*, apply: bool) -> dict[str, object]:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.username == settings.initial_admin_username))
        if user is None:
            raise RuntimeError("Configured administrator account does not exist")
        role_ids = set(user.role_ids or [])
        if user.role != "admin" and "admin" not in role_ids:
            raise RuntimeError("Configured administrator username is not an administrator account")
        if not settings.initial_admin_password:
            raise RuntimeError("INITIAL_ADMIN_PASSWORD is not configured")

        profile = user.profile or {}
        legacy_imported = bool(profile.get("migration_source"))
        result = {
            "username": user.username,
            "legacy_imported": legacy_imported,
            "was_active": bool(user.is_active),
            "failed_login_attempts": int(user.failed_login_attempts or 0),
            "was_locked": user.locked_until is not None,
            "applied": False,
        }
        if apply:
            user.password_hash = hash_password(settings.initial_admin_password)
            user.is_active = True
            user.failed_login_attempts = 0
            user.locked_until = None
            user.must_change_password = False
            await db.commit()
            result["applied"] = True
        return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(repair(apply=args.apply)), ensure_ascii=False))


if __name__ == "__main__":
    main()
