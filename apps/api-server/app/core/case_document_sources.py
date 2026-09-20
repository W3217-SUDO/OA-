"""按案件合并关系收集文档来源，保留各来源的原始信息。"""


def case_document_sources(record):
    pending = [{"id": record.id, "serial_no": record.serial_no, "data": record.data or {}}]
    sources = []
    seen = set()
    while pending:
        source = pending.pop(0)
        case_id = source.get("id")
        if case_id in seen:
            continue
        seen.add(case_id)
        sources.append(source)
        pending.extend((source.get("data") or {}).get("merged_sources") or [])
    return sources
