"""Reconcile migrated case files with the legacy manifest and shared storage."""

from __future__ import annotations

import argparse
import asyncio
import json
import mimetypes
import re
import shutil
import ssl
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote

from sqlalchemy import delete, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.main import UPLOAD_ROOT
from app.models import BusinessRecord, FileAttachment, LegacyCaseFile, WorkflowEvent


LEGACY_BASE_URL = "https://sh.021ipr.com/CaseFiles/CaseFiles"
LEGACY_ID_PATTERN = re.compile(r"旧系统附件ID:(\d+)")
PLACEHOLDER_REMARK = "8091旧系统样本文件元数据"
PLACEHOLDER_REMARKS = {
    PLACEHOLDER_REMARK,
    PLACEHOLDER_REMARK.encode("gbk").decode("latin1"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--upload-root", type=Path, default=UPLOAD_ROOT)
    parser.add_argument("--source-root", type=Path)
    return parser.parse_args()


def legacy_id(attachment: FileAttachment) -> int | None:
    match = LEGACY_ID_PATTERN.search(attachment.remark or "")
    return int(match.group(1)) if match else None


def category(item: dict) -> str:
    return str(item.get("file_type_name") or "").strip() or "旧系统未分类"


def legacy_url(item: dict) -> str:
    return f"{LEGACY_BASE_URL}/{quote(str(item['case_no']), safe='')}/{quote(str(item['file_name']), safe='')}"


def copy_or_download(item: dict, target: Path, source: Path | None) -> None:
    partial = target.with_suffix(target.suffix + ".part")
    partial.unlink(missing_ok=True)
    try:
        if source:
            shutil.copy2(source, partial)
        else:
            request = urllib.request.Request(
                legacy_url(item), headers={"User-Agent": "Sunhold-Legacy-Migration/1.0"}
            )
            with urllib.request.urlopen(request, timeout=180, context=ssl.create_default_context()) as response:
                with partial.open("wb") as output:
                    shutil.copyfileobj(response, output, length=1024 * 1024)
        expected = int(item.get("actual_size") or item.get("file_size") or 0)
        if partial.stat().st_size != expected:
            raise RuntimeError(
                f"size mismatch for legacy file {item['file_id']}: "
                f"expected {expected}, got {partial.stat().st_size}"
            )
        partial.replace(target)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


async def run(
    manifest_path: Path,
    apply: bool,
    upload_root: Path,
    source_root: Path | None = None,
) -> dict:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = list(manifest.get("files") or [])
    if not items:
        raise RuntimeError("manifest contains no files")

    upload_root = upload_root.expanduser().resolve()
    upload_root.mkdir(parents=True, exist_ok=True)
    source_root = source_root.expanduser().resolve() if source_root else None
    created_paths: list[Path] = []
    report = {
        "mode": "apply" if apply else "dry-run",
        "manifest_files": len(items),
        "manifest_cases": len({str(item["case_no"]) for item in items}),
        "shared_storage_migrations": 0,
        "existing_legacy_files": 0,
        "new_legacy_files": 0,
        "category_updates": 0,
        "placeholder_deletes": 0,
        "projection_duplicate_deletes": 0,
        "missing_cases": [],
    }

    try:
        async with SessionLocal() as db:
            attachments = list((await db.scalars(select(FileAttachment).order_by(FileAttachment.id))).all())

            # Every physical attachment uses the stable root, not a release worktree.
            for attachment in attachments:
                source = Path(attachment.path)
                if not source.is_file() or upload_root in source.resolve().parents:
                    continue
                target = upload_root / attachment.stored_name
                if target.exists() and target.stat().st_size != source.stat().st_size:
                    raise RuntimeError(f"shared storage collision: {target}")
                if apply and not target.exists():
                    shutil.copy2(source, target)
                    created_paths.append(target)
                attachment.path = str(target)
                report["shared_storage_migrations"] += 1

            cases = list((await db.scalars(select(BusinessRecord).where(
                BusinessRecord.module == "case"
            ))).all())
            case_by_no = {case.serial_no: case for case in cases}
            attachments_by_legacy_id = {
                value: attachment
                for attachment in attachments
                if (value := legacy_id(attachment)) is not None
            }

            if apply:
                semaphore = asyncio.Semaphore(8)

                async def prefetch(item: dict) -> Path | None:
                    file_id = int(item["file_id"])
                    if file_id in attachments_by_legacy_id or str(item["case_no"]).strip() not in case_by_no:
                        return None
                    suffix = Path(str(item["file_name"])).suffix.lower()
                    target = upload_root / f"legacy-{file_id}{suffix}"
                    if target.is_file():
                        expected = int(item.get("actual_size") or item.get("file_size") or 0)
                        if target.stat().st_size != expected:
                            raise RuntimeError(f"prefetched legacy file size mismatch: {file_id}")
                        return None
                    async with semaphore:
                        source = source_root / str(item["case_no"]) / str(item["file_name"]) if source_root else None
                        await asyncio.to_thread(
                            copy_or_download,
                            item,
                            target,
                            source if source and source.is_file() else None,
                        )
                    return target

                prefetched = await asyncio.gather(*(prefetch(item) for item in items))
                created_paths.extend(path for path in prefetched if path is not None)

            for item in items:
                file_id = int(item["file_id"])
                case_no = str(item["case_no"]).strip()
                case = case_by_no.get(case_no)
                if not case:
                    report["missing_cases"].append(case_no)
                    continue

                attachment = attachments_by_legacy_id.get(file_id)
                expected_size = int(item.get("actual_size") or item.get("file_size") or 0)
                suffix = Path(str(item["file_name"])).suffix.lower()
                if attachment:
                    report["existing_legacy_files"] += 1
                    source = Path(attachment.path)
                    target = upload_root / attachment.stored_name
                    if source.is_file() and source.stat().st_size != expected_size:
                        raise RuntimeError(f"existing legacy file size mismatch: {file_id}")
                    if not target.is_file() and apply:
                        await asyncio.to_thread(copy_or_download, item, target, source if source.is_file() else None)
                        created_paths.append(target)
                    attachment.path = str(target)
                    attachment.size = expected_size
                    attachment.file_type_code = str(item.get("case_file_type_id") or "")
                    next_category = category(item)
                    if attachment.category != next_category:
                        attachment.category = next_category
                        report["category_updates"] += 1
                else:
                    report["new_legacy_files"] += 1
                    stored_name = f"legacy-{file_id}{suffix}"
                    target = upload_root / stored_name
                    if apply and not target.is_file():
                        source = source_root / case_no / str(item["file_name"]) if source_root else None
                        await asyncio.to_thread(
                            copy_or_download,
                            item,
                            target,
                            source if source and source.is_file() else None,
                        )
                        created_paths.append(target)
                    attachment = FileAttachment(
                        record_id=case.id,
                        category=category(item),
                        file_type_code=str(item.get("case_file_type_id") or ""),
                        original_name=Path(str(item["file_name"])).name,
                        stored_name=stored_name,
                        content_type=mimetypes.guess_type(str(item["file_name"]))[0] or "application/octet-stream",
                        size=expected_size,
                        path=str(target),
                        uploader="legacy-import",
                        remark=(
                            f"旧系统附件ID:{file_id};旧系统文件GUID:{item.get('file_guid') or ''};"
                            f"旧系统上传人:{item.get('uploading_user') or ''}"
                        ),
                    )
                    db.add(attachment)
                    await db.flush()
                    attachments.append(attachment)
                    attachments_by_legacy_id[file_id] = attachment
                    db.add(WorkflowEvent(
                        record_id=case.id,
                        action="迁移旧系统案件附件",
                        from_status=case.status,
                        to_status=case.status,
                        operator="legacy-import",
                        comment=f"{attachment.category}：{attachment.original_name}（旧系统附件ID {file_id}）",
                    ))

                placeholders = [
                    candidate for candidate in attachments
                    if candidate.id != attachment.id
                    and candidate.record_id == case.id
                    and candidate.remark in PLACEHOLDER_REMARKS
                    and candidate.original_name == attachment.original_name
                    and candidate.size == attachment.size
                    and not Path(candidate.path).is_file()
                ]
                for placeholder in placeholders:
                    await db.execute(delete(LegacyCaseFile).where(LegacyCaseFile.FileId == -placeholder.id))
                    await db.delete(placeholder)
                    attachments.remove(placeholder)
                    report["placeholder_deletes"] += 1
                    report["projection_duplicate_deletes"] += 1

                generated_projection = await db.get(LegacyCaseFile, -attachment.id)
                original_projection = await db.get(LegacyCaseFile, file_id)
                if generated_projection and original_projection:
                    await db.delete(generated_projection)
                    report["projection_duplicate_deletes"] += 1

            report["missing_cases"] = sorted(set(report["missing_cases"]))
            if apply:
                await db.commit()
            else:
                await db.rollback()
    except Exception:
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise

    return report


if __name__ == "__main__":
    args = parse_args()
    print(json.dumps(
        asyncio.run(run(args.manifest, args.apply, args.upload_root, args.source_root)),
        ensure_ascii=False,
        indent=2,
    ))
