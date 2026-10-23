"""把已存在服务器本机的法院收文文件（法院送达文书、官方收文）迁到 OSS“法院收文/”目录并打标记。

默认只预览；加 --apply 才上传并改附件路径。本机原文件保留不删；
每次执行写一份回退清单（附件 ID、原路径、原 stored_name、新路径），按清单改回 path/stored_name 即可回退。
"""

import argparse
import asyncio
import csv
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.court_intake_storage import RECEIVED_DIR, SOURCE_DIR, object_key, oss_enabled, store  # noqa: E402
from app.core.storage import _attachment_storage_path  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.models import BusinessRecord, FileAttachment  # noqa: E402

CATEGORIES = ("法院送达文书", "官方收文")


async def plan(db) -> list[dict]:
    items = (await db.scalars(select(FileAttachment).where(
        FileAttachment.category.in_(CATEGORIES), ~FileAttachment.path.like("oss://%")).order_by(FileAttachment.id))).all()
    rows = []
    for item in items:
        path = _attachment_storage_path(item)
        if path is None:
            rows.append({"item": item, "error": "本机文件不可读"})
            continue
        content = path.read_bytes()
        if item.category == "官方收文":
            case = await db.get(BusinessRecord, item.record_id) if item.record_id else None
            receipt = await db.scalar(select(BusinessRecord).where(BusinessRecord.module == "document",
                                                                   BusinessRecord.data["attachment_id"].as_string() == str(item.id)))
            court_no = str(((receipt.data if receipt else None) or {}).get("court_no") or (case.data or {}).get("court_case_no") or "无法院案号") if case else "无法院案号"
            serial = case.serial_no if case else "未关联案件"
            key = object_key(RECEIVED_DIR, serial, court_no, item.original_name)
            metadata = {"case-id": item.record_id or "", "case-no": serial, "court-case-no": court_no, "migrated-from": "local"}
            tags = {"status": "received", "status-cn": "已入库", "case": serial}
        else:
            marker = re.match(r"法院送达:([^:]+):(.*)$", item.remark or "")
            sdbh, wsbh = (marker.group(1), marker.group(2)) if marker else ("未知送达编号", "")
            month = (item.created_at or datetime.now()).strftime("%Y-%m")
            key = object_key(SOURCE_DIR, month, sdbh, f"{wsbh or hashlib.sha256(content).hexdigest()[:12]}_{item.original_name}")
            metadata = {"source": "zxfw.court.gov.cn", "sdbh": sdbh, "wsbh": wsbh, "migrated-from": "local"}
            tags = {"source": "zxfw", "status": "pending", "status-cn": "待入库"}
        metadata.update({"uploader": item.uploader, "sha256": hashlib.sha256(content).hexdigest()})
        rows.append({"item": item, "content": content, "key": key, "metadata": metadata, "tags": tags})
    return rows


async def main(apply: bool, rollback_dir: Path) -> int:
    if not oss_enabled():
        print("OSS 未配置，停止")
        return 1
    async with SessionLocal() as db:
        rows = await plan(db)
        for row in rows:
            item = row["item"]
            print(item.id, item.category, item.original_name, "→", row.get("key") or row["error"])
        if not apply or not rows:
            print(f"共 {len(rows)} 个；预览模式未改动" if not apply else "没有需要迁移的文件")
            return 0
        rollback_dir.mkdir(parents=True, exist_ok=True)
        rollback = rollback_dir / f"court-intake-oss-migration-{datetime.now():%Y%m%d%H%M%S}.tsv"
        with rollback.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerow(["attachment_id", "old_path", "old_stored_name", "new_path", "new_stored_name"])
            for row in rows:
                if "error" in row:
                    continue
                item = row["item"]
                new_path, new_stored = await store(row["content"], key=row["key"], filename=item.original_name,
                                                   content_type=item.content_type or "application/octet-stream",
                                                   metadata=row["metadata"], tags=row["tags"])
                writer.writerow([item.id, item.path, item.stored_name, new_path, new_stored])
                handle.flush()
                item.path, item.stored_name = new_path, new_stored
                await db.commit()
                print("已迁移", item.id, new_path)
        print("回退清单：", rollback)
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="实际上传并改附件路径")
    parser.add_argument("--rollback-dir", type=Path, default=Path("/opt/sunhold-oa/backups/court-intake-oss"))
    options = parser.parse_args()
    sys.exit(asyncio.run(main(options.apply, options.rollback_dir)))
