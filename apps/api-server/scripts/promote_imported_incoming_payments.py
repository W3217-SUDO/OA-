"""晋升已归档的指定HZ源库回款；须有同源BAS_Case_FeeType字典，默认预检不提交。"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv


async def promote(*, source_database, apply):
    from app.core.imported_incoming_payments import promote_imported_incoming_payments
    from app.database import SessionLocal

    async with SessionLocal() as db:
        try:
            report = await promote_imported_incoming_payments(
                db, source_database=source_database, write=apply,
            )
            if apply:
                await db.commit()
            else:
                await db.rollback()
            return {"mode": "apply" if apply else "dry-run", "source_database": source_database,
                    "committed": apply, **report}
        except Exception:
            await db.rollback()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-database", required=True, help="manifest中确证的源库名称，不按编号猜测")
    parser.add_argument("--env-file", type=Path, help="项目数据库环境文件")
    parser.add_argument("--apply", action="store_true", help="整批预检通过后提交；缺省仅预检")
    args = parser.parse_args()
    if args.env_file:
        load_dotenv(args.env_file, override=True)
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        report = asyncio.run(promote(source_database=args.source_database, apply=args.apply))
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1) from exc
    print(json.dumps({"ok": True, **report}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
