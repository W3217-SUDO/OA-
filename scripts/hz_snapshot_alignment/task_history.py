"""普通案件任务及全部节点、消息、通知的独立历史投影。"""

from .common import connect, save_report
from .sql_projection import project, string, record_views, business_join, state


def aliases(mapping):
    return {target: string(source) for target, source in mapping.items()}


def main():
    report = {}
    with connect() as db:
        record_views(db)
        db.execute(
            "ALTER TABLE legacy_case_task_histories ALTER COLUMN task_title TYPE text,ALTER COLUMN task_sub_title TYPE text"
        )
        mapping = aliases(
            {
                "legacy_task_guid": "TaskGuid",
                "legacy_task_no": "TaskNo",
                "legacy_case_no": "CaseNo",
                "task_title": "TaskTitle",
                "task_sub_title": "TaskSubTitle",
                "is_active": "IsActived",
                "initiator": "Initiator",
                "officer": "Officer",
                "first_officer": "FirstOfficer",
                "associates": "Associates",
                "associate_names": "AssociateNames",
                "current_node_guid": "NodeGuid",
                "first_node_guid": "FirstNodeGuid",
                "task_content": "TaskContent",
            }
        )
        mapping.update(
            {
                "case_record_id": "r.id",
                "legacy_task_id": 's."TaskId"',
                "legacy_case_id": 's."CaseId"',
                "case_mapping_state": state("r"),
                "task_priority": 's."TaskPriority"',
                "task_type_id": 's."TaskTypeId"',
                "task_status": 's."TaskStatus"',
                "task_begin_time": 's."TaskBeginTime"',
                "task_finished_time": 's."TaskFinishedTime"',
                "task_end_time": 's."TaskEndTime"',
                "source_snapshot": "row_to_json(s)",
            }
        )
        report["roots"] = project(
            db,
            "legacy_case_task_histories",
            "Legal_Case_Task",
            mapping,
            ["legacy_task_id"],
            business_join("case", "CaseNo"),
        )
        task_join = 'LEFT JOIN legacy_case_task_histories t ON t.legacy_task_guid=s."TaskGuid"'
        node_join = (
            task_join
            + ' LEFT JOIN legacy_case_task_history_nodes n ON n.legacy_task_guid=s."TaskGuid" AND n.legacy_node_guid=s."NodeGuid"'
        )
        mapping = aliases(
            {
                "legacy_task_guid": "TaskGuid",
                "legacy_node_guid": "NodeGuid",
                "node_type_name": "NodeTypeName",
                "is_active": "IsActived",
                "initiator": "Initiator",
                "officer": "Officer",
                "associates": "Associates",
                "associate_names": "AssociateNames",
                "node_content": "NodeContent",
            }
        )
        mapping.update(
            {
                "legacy_node_id": 's."NodeId"',
                "task_history_id": "t.id",
                "task_relationship_state": state("t"),
                "node_type_id": 's."NodeTypeId"',
                "node_status": 's."NodeStatus"',
                "node_begin_time": 's."NodeBeginTime"',
                "node_finished_time": 's."NodeFinishedTime"',
                "node_end_time": 's."NodeEndTime"',
                "source_snapshot": "row_to_json(s)",
            }
        )
        report["nodes"] = project(
            db, "legacy_case_task_history_nodes", "Legal_Case_Task_Node", mapping, ["legacy_node_id"], task_join
        )
        mapping = aliases(
            {"legacy_task_guid": "TaskGuid", "legacy_node_guid": "NodeGuid", "participant": "Participant"}
        )
        mapping.update(
            {
                "legacy_seq_id": 's."SeqId"',
                "task_history_id": "t.id",
                "node_history_id": "n.id",
                "task_relationship_state": state("t"),
                "node_relationship_state": state("n"),
                "sorting_index": 's."SortingIndex"',
                "source_snapshot": "row_to_json(s)",
            }
        )
        report["participants"] = project(
            db,
            "legacy_case_task_history_node_participants",
            "Legal_Case_Task_Node_Participant",
            mapping,
            ["legacy_seq_id"],
            node_join,
        )
        mapping = aliases(
            {
                "legacy_message_guid": "MessageGuid",
                "legacy_task_guid": "TaskGuid",
                "legacy_node_guid": "NodeGuid",
                "message_type_name": "MessageTypeName",
                "content": "Content",
                "sender": "Sender",
            }
        )
        mapping.update(
            {
                "legacy_message_id": 's."MessageId"',
                "task_history_id": "t.id",
                "node_history_id": "n.id",
                "task_relationship_state": state("t"),
                "node_relationship_state": state("n"),
                "message_type_id": 's."MessageTypeId"',
                "send_time": 's."SendTime"',
                "source_snapshot": "row_to_json(s)",
            }
        )
        report["messages"] = project(
            db,
            "legacy_case_task_history_messages",
            "Legal_Case_Task_Message",
            mapping,
            ["legacy_message_id"],
            node_join,
        )
        message_join = (
            task_join
            + ' LEFT JOIN legacy_case_task_history_messages m ON m.legacy_task_guid=s."TaskGuid" AND m.legacy_message_guid=s."MessageGuid"'
        )
        mapping = aliases(
            {
                "legacy_task_guid": "TaskGuid",
                "legacy_message_guid": "MessageGuid",
                "notification_type_name": "NotificationTypeName",
                "notification_object": "NotificationObject",
                "have_read": "HaveRead",
            }
        )
        mapping.update(
            {
                "legacy_seq_id": 's."SeqId"',
                "task_history_id": "t.id",
                "message_history_id": "m.id",
                "task_relationship_state": state("t"),
                "message_relationship_state": state("m"),
                "notification_type_id": 's."NotificationTypeId"',
                "source_snapshot": "row_to_json(s)",
            }
        )
        report["notifications"] = project(
            db,
            "legacy_case_task_history_notifications",
            "Legal_Case_Task_Message_Notification",
            mapping,
            ["legacy_seq_id"],
            message_join,
        )
        mapping = aliases(
            {
                "legacy_task_guid": "TaskGuid",
                "legacy_message_guid": "MessageGuid",
                "legacy_file_guid": "FileGuid",
                "file_name": "FileName",
                "source_path": "FilePath",
                "upload_user": "UploadUser",
                "is_active": "IsActived",
            }
        )
        mapping.update(
            {
                "legacy_file_id": 's."FileId"',
                "task_history_id": "t.id",
                "message_history_id": "m.id",
                "task_relationship_state": state("t"),
                "message_relationship_state": state("m"),
                "file_size": 's."FileSize"',
                "upload_time": 's."UploadTime"',
                "source_snapshot": "row_to_json(s)",
            }
        )
        report["files"] = project(
            db, "legacy_case_task_history_files", "Legal_Case_Task_File", mapping, ["legacy_file_id"], message_join
        )
        mapping = aliases({"reader": "Reader", "have_read": "HaveRead"})
        mapping.update(
            {
                "legacy_seq_id": 's."SeqId"',
                "legacy_task_id": 's."TaskId"',
                "legacy_message_id": 's."MessageId"',
                "task_history_id": "t.id",
                "message_history_id": "m.id",
                "task_relationship_state": state("t"),
                "message_relationship_state": state("m"),
                "source_snapshot": "row_to_json(s)",
            }
        )
        joins = 'LEFT JOIN legacy_case_task_histories t ON t.legacy_task_id=s."TaskId" LEFT JOIN legacy_case_task_history_messages m ON m.legacy_message_id=s."MessageId"'
        report["read_receipts"] = project(
            db,
            "legacy_case_task_history_read_receipts",
            "Legal_Case_Task_Message_HaveRead",
            mapping,
            ["legacy_seq_id"],
            joins,
        )
    save_report("task-history-report.json", report)


if __name__ == "__main__":
    main()
