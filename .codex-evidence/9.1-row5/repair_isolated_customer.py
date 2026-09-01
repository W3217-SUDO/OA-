import asyncio
import json
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import BusinessRecord


async def main() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as db:
        case = await db.get(BusinessRecord, 47150)
        customer = (await db.execute(select(BusinessRecord).where(BusinessRecord.module == "customer", BusinessRecord.customer == "测试555"))).scalars().first()
        if customer is None:
            customer = BusinessRecord(module="customer", serial_no="KH-ROW5-RESTORED-TEST555", title="测试555", customer="测试555", status="正常", owner="admin", department="上海分所", data={})
            db.add(customer)
            await db.flush()
        data = dict(case.data or {})
        data["customer_record_id"] = customer.id
        case.data = data
        await db.commit()
        print(json.dumps({"case_id": case.id, "customer_record_id": customer.id}, ensure_ascii=False))
    await engine.dispose()


asyncio.run(main())
