"""Backfill stable HR job-role codes without guessing historic assignments.

Run without --apply first. Only a single active role matched by explicit legacy
profile values is updated; ambiguous or missing values remain untouched.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

# Permit direct invocation from the scripts directory without changing data.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal, engine
from app.main import _system_user_role_ids, _upgrade_schema
from app.models import JobRole, User


def _role_candidates(profile: dict) -> set[str]:
    return {
        str(profile.get(key) or "").strip().casefold()
        for key in ("permission_role_code", "permission_role", "staff_role", "position")
        if str(profile.get(key) or "").strip()
    }


async def run(apply: bool) -> dict:
    async with engine.begin() as connection:
        await connection.run_sync(_upgrade_schema)
    async with SessionLocal() as db:
        roles = list((await db.scalars(select(JobRole).where(JobRole.is_active.is_(True)))).all())
        by_reference: dict[str, JobRole] = {}
        for role in roles:
            by_reference[role.code.casefold()] = role
            by_reference[role.name.casefold()] = role
        report = {"updated": [], "unchanged": [], "unmatched": [], "ambiguous": [], "skipped_admin": []}
        users = list((await db.scalars(select(User).order_by(User.id))).all())
        for user in users:
            if "admin" in _system_user_role_ids(user):
                report["skipped_admin"].append(user.username)
                continue
            profile = dict(user.profile or {})
            matches = {by_reference[value].id for value in _role_candidates(profile) if value in by_reference}
            if not matches:
                report["unmatched"].append(user.username)
                continue
            if len(matches) != 1:
                report["ambiguous"].append(user.username)
                continue
            role = next(role for role in roles if role.id in matches)
            if profile.get("permission_role_code") == role.code and profile.get("permission_role") == role.name:
                report["unchanged"].append(user.username)
                continue
            report["updated"].append(user.username)
            if apply:
                user.profile = {**profile, "permission_role_code": role.code, "permission_role": role.name, "staff_role": role.name}
        if apply:
            await db.commit()
        return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="persist only unique, explicit role matches")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.apply)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
