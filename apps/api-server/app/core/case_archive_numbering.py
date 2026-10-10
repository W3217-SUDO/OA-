"""案件归档流水取号，与审核共用事务，不在此提交。"""
import re

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BusinessRecord, LegacyCase, SystemConfig


async def allocate_archive_file_no(
    record: BusinessRecord, db: AsyncSession, *, year: int, operator: str,
) -> str:
    file_no = str((record.data or {}).get("file_no") or "").strip()
    legacy_file_no = str(await db.scalar(select(LegacyCase.FileNo).where(
        LegacyCase.CaseNo == record.serial_no[:20],
    )) or "").strip()
    if file_no and legacy_file_no and file_no != legacy_file_no:
        raise HTTPException(status_code=409, detail="案件归档流水号与历史记录不一致，请核实后再审核")
    if file_no or legacy_file_no:
        return file_no or legacy_file_no

    dialect = (await db.connection()).dialect.name
    if dialect == "postgresql":
        insert = postgres_insert
    elif dialect == "sqlite":
        insert = sqlite_insert
    else:
        raise RuntimeError(f"Unsupported archive sequence database: {dialect}")

    sequence_key = "case_archive_file_sequence"
    statement = insert(SystemConfig).values(
        key=sequence_key, label="案件归档流水", group="运行配置",
        value={"last_sequence": 0}, updated_by=operator,
        description="FileNo 跨年连续流水，与纸质档案号分别保存",
    )
    # 唯一键冲突更新先取得事务写锁，首次建计数器和后续取号使用同一锁。
    await db.execute(statement.on_conflict_do_update(
        index_elements=[SystemConfig.key], set_={"key": statement.excluded.key},
    ))
    sequence = await db.scalar(select(SystemConfig).where(
        SystemConfig.key == sequence_key,
    ).with_for_update().execution_options(populate_existing=True))
    last_sequence = sequence.value.get("last_sequence") if isinstance(sequence.value, dict) else None
    if type(last_sequence) is not int or last_sequence < 0:
        raise HTTPException(status_code=409, detail="归档流水计数配置无效，请核实后再审核")

    numbers = list((await db.scalars(select(LegacyCase.FileNo).where(
        LegacyCase.FileNo.like("D%"),
    ))).all())
    modern_file_no = BusinessRecord.data["file_no"].as_string()
    numbers.extend((await db.scalars(select(modern_file_no).where(
        BusinessRecord.module == "case", modern_file_no.like("D%"),
    ))).all())
    for number in numbers:
        match = re.fullmatch(r"D[0-9]{4}([0-9]+)", str(number or "").strip())
        if match:
            last_sequence = max(last_sequence, int(match.group(1)))
    if not last_sequence:
        raise HTTPException(status_code=409, detail="缺少可接续的归档流水，请先核实初始序号配置")
    next_sequence = last_sequence + 1
    file_no = f"D{year}{next_sequence}"
    if len(file_no) > 20:
        raise HTTPException(status_code=409, detail="归档流水号已超出现有字段长度，请核实后再审核")
    sequence.value = {"last_sequence": next_sequence}
    sequence.updated_by = operator
    await db.flush()
    return file_no
