"""使用已证实的源名称修正详情展示，不覆盖其他已完成的字段和关联。"""

from collections import Counter
from psycopg.types.json import Jsonb
from .common import SOURCE, connect, save_report


def main():
    report = Counter()
    with connect() as db:
        for record in db.execute(
            "SELECT id,data FROM business_records WHERE module='ipr_case' AND data->>'migration_source'=%s", (SOURCE,)
        ).fetchall():
            data = record["data"]
            patch = {"application_type": data.get("case_type_name", "")}
            for key, source_name in [
                ("case_manager", "case_officer_name"),
                ("case_source", "case_origin_people_name"),
                ("agent", "procurator_name"),
                ("writer", "copywriter_name"),
                ("submitter", "case_submitter_name"),
            ]:
                if data.get(source_name):
                    patch[key] = data[source_name]
            db.execute(
                "UPDATE business_records SET data=(data::jsonb||%s)::json WHERE id=%s", (Jsonb(patch), record["id"])
            )
            report["ipr_details_updated"] += 1
        db.commit()
    save_report("page-presentation-report.json", dict(report))


if __name__ == "__main__":
    main()
