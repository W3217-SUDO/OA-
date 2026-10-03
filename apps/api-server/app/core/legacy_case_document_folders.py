"""从迁入的新数据库读取旧案件目录身份，不按文件名重分类。"""

from collections import Counter

from sqlalchemy import bindparam, text

from app.core.case_document_sources import case_document_sources


def _legacy_sources(record):
    return [source for source in case_document_sources(record)
            if (source.get("data") or {}).get("migration_source") == "hz_crm_20260930"]


def legacy_folder_key(record_id, folder_id):
    return f"legacy-case-folder:{record_id}:{folder_id}"


async def legacy_case_folder_tree(record, db):
    sources = _legacy_sources(record)
    if not sources:
        return []
    case_nos = [(source["data"].get("legacy_record") or {}).get("CaseNo") for source in sources]
    if not all(case_nos):
        raise ValueError("迁移案件缺少旧案号，不能定位原目录")
    statement = text('''SELECT "FileTypeId","ParentFileTypeId","FileTypeName","CaseNo","TypeId"
        FROM "Legal_Case_FileType" WHERE "CaseNo" IN :case_nos AND "IsActived"='T'
        ORDER BY "FileTypeId"''').bindparams(bindparam("case_nos", expanding=True))
    rows = (await db.execute(statement, {"case_nos": case_nos})).mappings().all()
    tree = []
    for source, case_no in zip(sources, case_nos):
        nodes = {}
        for row in rows:
            if row["CaseNo"] != case_no:
                continue
            folder_id = row["FileTypeId"]
            nodes[folder_id] = {
                "label": row["FileTypeName"], "value": legacy_folder_key(source["id"], folder_id),
                "legacy_folder_id": folder_id, "legacy_parent_id": row["ParentFileTypeId"],
                "legacy_type_id": row["TypeId"], "legacy_record_id": source["id"], "options": [],
            }
        names = Counter(node["label"] for node in nodes.values())
        for folder_id, node in nodes.items():
            node["legacy_unique_name"] = names[node["label"]] == 1
            seen = {folder_id}
            parent_id = node["legacy_parent_id"]
            while parent_id in nodes and parent_id != nodes[parent_id]["legacy_parent_id"]:
                if parent_id in seen:
                    raise ValueError("旧案件目录存在循环父子关系，不能生成目录树")
                seen.add(parent_id)
                parent_id = nodes[parent_id]["legacy_parent_id"]
            parent_id = node["legacy_parent_id"]
            if parent_id == folder_id or parent_id not in nodes:
                # 旧 zTree 将没有匹配父节点的记录展示在顶层；保留异常父 ID 供核查。
                node["legacy_parent_missing"] = parent_id != folder_id
                tree.append(node)
            else:
                nodes[parent_id]["options"].append(node)
    return tree


async def legacy_attachment_folder_keys(files, records, db):
    legacy_record_ids = {record_id for record_id, record in records.items()
                         if record.module == "case" and _legacy_sources(record)}
    attachments = {item.id: item for item in files
                   if item.record_id in legacy_record_ids
                   and item.stored_name.startswith("legacy-oss-Legal_Case_File-")}
    if not attachments:
        return {}
    statement = text('''SELECT l.attachment_id,l.case_record_id,r."CaseNo" case_no,r."CaseFileTypeId" folder_id,
        t."FileTypeName" folder_name FROM legacy_case_attachment_relations l
        JOIN "Legal_Case_File" r ON r."FileId"=l.legacy_file_id
        LEFT JOIN "Legal_Case_FileType" t ON t."FileTypeId"=r."CaseFileTypeId" AND t."CaseNo"=r."CaseNo"
        WHERE l.attachment_id IN :attachment_ids''').bindparams(bindparam("attachment_ids", expanding=True))
    result = {}
    for row in (await db.execute(statement, {"attachment_ids": list(attachments)})).mappings():
        item = attachments[row["attachment_id"]]
        if item.record_id != row["case_record_id"] or not row["folder_id"]:
            continue
        expected_case_no = (records[item.record_id].data.get("legacy_record") or {}).get("CaseNo")
        if row["case_no"] != expected_case_no:
            raise ValueError("旧附件案号与当前父案件不一致，不能绑定目录")
        # 用户已经在新系统更改分类的文件不得被旧投影移回原目录。
        if row["folder_name"] and item.category != row["folder_name"]:
            continue
        result[item.id] = legacy_folder_key(item.record_id, row["folder_id"])
    return result


def append_native_case_folders(tree, categories, custom_folders, record_id):
    """保留新系统后来建立的目录，不以同名合并旧节点。"""
    pending = list(tree)
    names = set()
    root = None
    while pending:
        node = pending.pop()
        names.add(node["label"])
        if node.get("legacy_type_id") == 7 and node.get("legacy_record_id") == record_id:
            root = node
        pending.extend(node.get("options") or [])
    for name in dict.fromkeys([*custom_folders, *categories]):
        if not name or name in names or name == "AI空间":
            continue
        node = {"label": name, "value": name, "native_custom": name in custom_folders}
        (root["options"] if root is not None else tree).append(node)
        names.add(name)
    return tree
