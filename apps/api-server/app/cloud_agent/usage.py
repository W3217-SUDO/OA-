"""云端智能体调用记账（陶威 11-03：智能体中心要看到每个人调用的情况和收费）。

每轮对话结束后按火山返回的实际用量记一行：模型 token（区分高峰/空闲、命中缓存）、运行时长、OA 工具次数、
专业数据集/豆包搜索次数，并按单价估算费用。按月存在服务器私有目录 cloud/usage/YYYY-MM.jsonl，只追加不改。
费用是按公开单价的估算，实际以火山账单为准；不含模型赠送的免费额度。
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

BEIJING = timezone(timedelta(hours=8))
RUNTIME_YUAN_PER_HOUR = 0.5
AFP_YUAN = 0.002  # Agent Plan Max：1000 元 = 50 万 AFP
# 元/百万 token：(输入, 命中缓存, 输出)；有高峰/空闲两档的按 (空闲, 高峰) 给出。来源：方舟“模型价格”在线推理（常规），2026-11-03。
PRICES = {
    "deepseek-v4-1-flash-economy": ((0.80, 0.016, 3.20), (1.60, 0.032, 6.40)),
    "deepseek-v4-1-flash": ((1.00, 0.02, 4.00), (2.00, 0.04, 8.00)),
    "doubao-seed-2-1-pro": ((6.00, 1.20, 30.00),) * 2,
    "doubao-seed-2-1-lite": ((0.80, 0.16, 2.70),) * 2,
    "deepseek-v4-pro": ((9.00, 0.30, 27.00),) * 2,
    "deepseek-v4-flash": ((3.00, 0.10, 9.00),) * 2,
}
# 专业数据集按数据类型扣 AFP（套餐内）；豆包搜索 5 AFP/次（每月前 500 次免费，这里不扣减免费额度）。
DATAPRO_AFP = {"legal_regulation": 60, "legal_case": 48, "legal_hallucination": 240, "academic": 24}
DATAPRO_DEFAULT_AFP = 12
SEARCH_AFP = 5


def _price(model: str):
    for prefix, value in PRICES.items():
        if model.startswith(prefix):
            return value
    return None


def peak(moment: datetime) -> bool:
    """高峰：北京时间周一至周五 09:00–12:00、14:00–18:00。"""
    local = moment.astimezone(BEIJING)
    minutes = local.hour * 60 + local.minute
    return local.weekday() < 5 and (540 <= minutes < 720 or 840 <= minutes < 1080)


def parse_time(value) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


class TurnUsage:
    """一轮对话里累计：模型请求按完成时间分高峰/空闲，运行时长取 session.usage 累计值的差。"""

    def __init__(self):
        self.tokens = {"offpeak": [0, 0, 0], "peak": [0, 0, 0]}  # 未缓存输入、命中缓存、输出
        self.requests = 0
        self.active_seconds = None
        self.active_total = None  # 本会话累计运行秒数（火山 session.usage），存回会话文件供下一轮做差
        self.oa_tools = 0
        self.datapro: dict[str, int] = defaultdict(int)
        self.searches = 0

    def model_request(self, event: dict) -> None:
        usage = event.get("model_usage") or {}
        bucket = self.tokens["peak" if peak(parse_time(event.get("processed_at"))) else "offpeak"]
        bucket[0] += int(usage.get("input_tokens") or 0)
        bucket[1] += int(usage.get("cache_read_input_tokens") or 0)
        bucket[2] += int(usage.get("output_tokens") or 0)
        self.requests += 1

    def session_usage(self, event: dict, previous: float) -> float:
        total = float((event.get("usage") or {}).get("active_seconds") or 0)
        self.active_seconds = max(0.0, total - previous)
        return total

    def tool(self, name: str, result) -> None:
        if name == "volc_professional_data":
            kind = "other"
            if isinstance(result, dict):
                try:
                    kind = json.loads(result.get("result") or "{}").get("dataset_type") or "other"
                except (ValueError, AttributeError):
                    pass
            self.datapro[kind] += 1
        elif name == "doubao_search":
            self.searches += 1
        else:
            self.oa_tools += 1

    def record(self, *, username: str, display_name: str, workspace: str, conversation: str, model: str, ok: bool) -> dict:
        price = _price(model)
        model_yuan = None
        if price:
            model_yuan = sum(count * unit / 1_000_000 for slot, prices in (("offpeak", price[0]), ("peak", price[1]))
                             for count, unit in zip(self.tokens[slot], prices))
        runtime_yuan = (self.active_seconds or 0) / 3600 * RUNTIME_YUAN_PER_HOUR
        afp = sum(DATAPRO_AFP.get(kind, DATAPRO_DEFAULT_AFP) * count for kind, count in self.datapro.items()) + SEARCH_AFP * self.searches
        return {
            "time": datetime.now(BEIJING).isoformat(timespec="seconds"), "username": username, "display_name": display_name,
            "workspace": workspace, "conversation": conversation, "model": model, "ok": ok, "requests": self.requests,
            "input_tokens": self.tokens["offpeak"][0] + self.tokens["peak"][0],
            "cache_tokens": self.tokens["offpeak"][1] + self.tokens["peak"][1],
            "output_tokens": self.tokens["offpeak"][2] + self.tokens["peak"][2],
            "peak_tokens": sum(self.tokens["peak"]), "active_seconds": round(self.active_seconds or 0, 3),
            "oa_tools": self.oa_tools, "datapro": dict(self.datapro), "searches": self.searches, "harness_afp": afp,
            "model_yuan": None if model_yuan is None else round(model_yuan, 6), "runtime_yuan": round(runtime_yuan, 6),
            "harness_yuan": round(afp * AFP_YUAN, 6),
        }


NOTE = ("费用按火山公开单价估算：模型按 token（区分高峰/空闲、命中缓存），运行时 0.5 元/小时，专业数据集和豆包搜索按套餐 AFP 折算"
        "（1 AFP≈0.002 元）。不含赠送的免费额度，实际以火山账单为准。")


def parse_month(value: str | None) -> str:
    from fastapi import HTTPException

    month = value or datetime.now(BEIJING).strftime("%Y-%m")
    if len(month) != 7 or month[4] != "-" or not (month[:4] + month[5:]).isdigit():
        raise HTTPException(422, "月份格式应为 YYYY-MM")
    return month


def person_view(username: str, month: str, directory: Path | None = None) -> dict:
    """某一个人自己的月度汇总和每轮明细（个人页和管理员页共用同一套算法）。"""
    rows = [row for row in read_month(month, directory) if row.get("username") == username]
    people = summarize(rows)["people"]
    return {"month": month, "summary": people[0] if people else None, "records": list(reversed(rows))[:300],
            "total_records": len(rows), "note": NOTE}


def _directory() -> Path:
    from app.harness_agent.runtime import storage_root

    directory = storage_root() / "cloud" / "usage"
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    return directory


def append(record: dict, directory: Path | None = None) -> None:
    """一行一条、O_APPEND 追加（小于 4KB 的单次写入在多个 API 进程间不会交错）。"""
    directory = directory or _directory()
    line = (json.dumps(record, ensure_ascii=False) + "\n").encode()
    descriptor = os.open(directory / (record["time"][:7] + ".jsonl"), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(descriptor, line)
    finally:
        os.close(descriptor)


def read_month(month: str, directory: Path | None = None) -> list[dict]:
    path = (directory or _directory()) / (month + ".jsonl")
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def summarize(rows: list[dict]) -> dict:
    people: dict[str, dict] = {}
    days: dict[str, dict] = defaultdict(lambda: {"turns": 0, "yuan": 0.0})
    for row in rows:
        person = people.setdefault(row["username"], {
            "username": row["username"], "display_name": row.get("display_name") or row["username"], "turns": 0, "failed": 0,
            "personal_turns": 0, "case_turns": 0, "input_tokens": 0, "cache_tokens": 0, "output_tokens": 0, "active_seconds": 0.0,
            "oa_tools": 0, "datapro": 0, "searches": 0, "harness_afp": 0, "model_yuan": 0.0, "runtime_yuan": 0.0,
            "harness_yuan": 0.0, "last_time": ""})
        person["display_name"] = row.get("display_name") or person["display_name"]
        person["turns"] += 1
        person["failed"] += 0 if row.get("ok", True) else 1
        person["case_turns" if str(row.get("workspace", "")).startswith("case:") else "personal_turns"] += 1
        for key in ("input_tokens", "cache_tokens", "output_tokens", "active_seconds", "oa_tools", "searches", "harness_afp",
                    "runtime_yuan", "harness_yuan"):
            person[key] += row.get(key) or 0
        person["model_yuan"] += row.get("model_yuan") or 0
        person["datapro"] += sum((row.get("datapro") or {}).values())
        person["last_time"] = max(person["last_time"], row.get("time", ""))
        day = days[row.get("time", "")[:10]]
        day["turns"] += 1
        day["yuan"] += (row.get("model_yuan") or 0) + (row.get("runtime_yuan") or 0) + (row.get("harness_yuan") or 0)
    for person in people.values():
        person["total_yuan"] = round(person["model_yuan"] + person["runtime_yuan"] + person["harness_yuan"], 4)
        for key in ("model_yuan", "runtime_yuan", "harness_yuan", "active_seconds"):
            person[key] = round(person[key], 4)
    ordered = sorted(people.values(), key=lambda item: item["total_yuan"], reverse=True)
    keys = ("turns", "input_tokens", "cache_tokens", "output_tokens", "oa_tools", "datapro", "searches", "harness_afp",
            "model_yuan", "runtime_yuan", "harness_yuan", "total_yuan")
    total = {key: round(sum(item[key] for item in ordered), 4) for key in keys}
    return {"people": ordered, "total": total,
            "days": [{"date": date, "turns": value["turns"], "yuan": round(value["yuan"], 4)} for date, value in sorted(days.items())]}
