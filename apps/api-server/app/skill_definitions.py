"""Render the saved definition, without pretending it is the original import file."""
import hashlib
import re

import yaml


def skill_definition(record, scope):
    metadata = {"name": record["name"], "description": record["description"],
                "category": record.get("category", "自定义"), "quick_prompts": record.get("quick_prompts", [])}
    content = "---\n" + yaml.safe_dump(metadata, allow_unicode=True, sort_keys=False) + "---\n\n" + record["instruction"] + "\n"
    safe_id = str(record["id"])
    if not re.fullmatch(r"(?:custom|global)-[A-Za-z0-9_-]{1,100}", safe_id):
        safe_id = "skill-" + hashlib.sha256(safe_id.encode()).hexdigest()[:16]
    result = {"id": record["id"], "name": record["name"], "scope": scope,
              "filename": f"{safe_id}-SKILL.md", "content": content,
              "definition_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()}
    original = record.get("sha256")
    if isinstance(original, str) and re.fullmatch(r"[a-f0-9]{64}", original):
        result["import_sha256"] = original
    return result
