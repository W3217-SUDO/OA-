"""Application composition. Business implementations live in areas/ and core/."""
from app.core.storage import _xls_preview_sheets
from app.areas.aws.router import (
    create_official_outgoing_document, delete_official_documents, document_summary, download_official_outgoing_documents, export_official_documents,
    get_official_outgoing_document, link_official_documents_to_cases, list_official_outgoing_documents, mark_official_outgoing_documents_stamped, process_official_documents,
    review_official_outgoing_document, rollback_official_outgoing_document, submit_official_outgoing_document, transition_document, update_official_outgoing_document,
    update_official_receipt_date, upload_official_document, upload_official_outgoing_stamp_file,
)
from app.areas.contract.router import (
    approve_contract, archive_contract, batch_delete_contract_attachments, change_contract, close_contract_archive_subjects,
    contract_approvals, contract_approver_settings, contract_archive_subjects, contract_changes, contract_payment_candidates,
    create_contract_draft, create_contract_event, create_contract_event_by_guid, create_contract_investigation, create_contract_object,
    create_contract_payment_application, create_contract_payment_type, create_contract_seal_application, delete_company_contract_records, delete_contract_object,
    delete_contract_records, export_contract_archive_records, export_contract_detail_excel, list_contract_archive_records, list_contract_events,
    list_contract_events_by_guid, list_contract_object_cases, list_contract_objects, list_contract_payment_applications, pay_contract_payment_application,
    review_contract_change, review_contract_payment_application, revoke_contract_draft, save_contract_approver_settings, submit_contract,
    update_contract_draft, update_contract_object, writeoff_contract_payment_application,
)
from app.areas.crm.router import (
    activate_customer_portal, add_customer_contact, add_customer_note, claim_customer, close_customer_portal,
    create_customer, create_customer_event_by_guid, create_law_firm, create_law_firm_contact, customer_conflicts,
    customer_portal_create_demand, customer_portal_download, customer_portal_overview, customer_reference_options, delete_customer_contact,
    delete_customer_note, delete_law_firm, download_customer_contact_photo, download_customer_file_by_guid, download_law_firm_license,
    get_customer_legacy_history, get_law_firm, import_customers, list_customer_assignment_history, list_customer_contacts,
    list_customer_events_by_guid, list_customer_files_by_guid, list_customer_shared_objects, list_customers, list_law_firm_audits,
    list_law_firm_contacts, list_law_firms, lookup_notary_by_certificate, open_customer_portal, patch_customer,
    recycle_customer, register_notary_certificate, release_customer, restore_customer, review_customer_key_change,
    review_customer_level_change, review_notary, set_law_firm_default_contact, share_customer, submit_customer_key_change,
    submit_customer_level_change, update_customer_contact, update_customer_contact_status, update_customer_managers, update_customer_note,
    update_law_firm, update_law_firm_contact, upload_customer_contact_photo, upload_law_firm_license,
)
from app.areas.finance.router import (
    add_refund_case_fee_logs, allocate_incoming_payment, apply_general_settlements, approve_finance_fee, batch_refund_status,
    batch_review_finance_fees, batch_update_case_fee_inform_date, cancel_finance_payment, cancel_internal_payment_package, change_invoice_date,
    change_invoice_number, claim_incoming_payment, complete_litigation_refund, confirm_finance_fee_inform_arrival, confirm_reconciliation,
    create_finance_fee, create_finance_fee_inform, create_finance_fee_payment_type, create_finance_transaction, create_incoming_payment,
    create_internal_fee, create_internal_payment_package, create_invoice_application, create_jar_fee, create_litigation_refund,
    create_receivable, create_reconciliation, create_refund_page_case_fees, delete_finance_fee, delete_finance_fee_inform,
    delete_finance_transaction, delete_general_settlement_application, delete_incoming_payment, delete_internal_fee, delete_jar_fee,
    delete_jar_fee_file, delete_receivable, delete_reconciliation, download_finance_fee_inform_bill, download_jar_fee_file,
    export_archive_settlement_payments, export_finance_fee_query, export_general_settlements, export_incoming_payments, export_internal_fees,
    export_invoice_applications, export_invoice_case_fees, export_jar_fees, export_paid_archive_settlements, export_payment_package_word,
    export_pending_archive_settlements, export_refund_applications, export_refund_case_fees, export_rejected_archive_settlements, export_selected_refund_applications,
    finance_ar_summary, finance_contract_ledger, finance_fee_readiness, finance_summary, get_finance_payment_source,
    get_incoming_payment, get_internal_payment_package, get_jar_fee, get_legacy_finance_history_record, import_incoming_payments,
    incoming_payment_allocation_candidates, incoming_payment_refund_candidates, issue_invoice, legacy_finance_history_summary, link_finance_fee_inform,
    list_archive_settlement_payments, list_finance_customer_options, list_finance_fee_informs, list_finance_fee_payment_types, list_finance_payment_types,
    list_finance_transactions, list_general_settlement_applications, list_general_settlement_candidates, list_incoming_payments, list_internal_fees,
    list_internal_payment_package_candidates, list_internal_payment_packages, list_internal_refund_review_candidates, list_invoice_applications, list_invoice_case_fees,
    list_jar_fee_files, list_jar_fee_operation_logs, list_jar_fees, list_legacy_finance_history, list_paid_archive_settlements,
    list_pending_archive_settlements, list_pending_finance_settlements, list_receivable_details, list_receivables, list_reconciliations,
    list_rejected_archive_settlements, mark_finance_fee_no_payment, mark_finance_fee_refund_not_required, mark_finance_settlements_commission_paid, pay_or_rollback_general_settlement_applications,
    preview_internal_payment_package, query_finance_fees, query_refund_applications, query_refund_case_fees, reapply_general_settlement_applications,
    reapply_rejected_archive_settlements, receive_payment, refund_claim_incoming_payment, reject_invoice_issue, review_archive_settlement_payments,
    review_finance_fee, review_general_settlement_applications, review_invoice_application, review_litigation_refund, revoke_incoming_payment_allocations,
    rollback_finance_payment, rollback_paid_archive_settlements, rollback_rejected_archive_settlements, submit_finance_fee, submit_invoice_application,
    submit_litigation_refund, unlock_finance_fee_inform, update_finance_fee, update_incoming_payment, update_internal_fee,
    update_internal_payment_package, update_invoice_application, update_jar_fee, update_jar_fee_status, update_refund_amount,
    update_refund_case_fee_status, upload_finance_fee_inform_bill, upload_jar_fee_file, view_assigned_incoming_payment, void_invoice,
    void_rejected_finance_fee, withdraw_invoice_application, writeoff_finance_fee, writeoff_internal_payment_package,
)
from app.areas.hr.router import (
    create_department, create_hr_employee, create_hr_performance, create_hr_subrecord, create_job_role,
    delete_department, delete_hr_employee, delete_hr_employees_batch, delete_hr_performance, delete_hr_subrecord,
    delete_job_role, export_hr_performance, get_employee_performance_for_case, get_hr_employee_batch_deletion_impact, get_hr_employee_deletion_impact,
    get_hr_performance, get_job_role_permissions, list_departments, list_hr_employees, list_hr_performance,
    list_hr_subrecords, list_job_roles, transition_employee, update_department, update_hr_employee,
    update_hr_employee_contract_approval_status, update_hr_employee_login_status, update_hr_performance, update_hr_subrecord, update_job_role,
    update_job_role_permissions,
)
from app.areas.investigation.router import (
    assign_investigation_record, batch_create_cases_from_clues, batch_delete_investigation_records, batch_submit_investigation_clues, bind_clue_source_contract,
    close_investigation, clue_import_template, create_evidence_from_clue, create_investigation_fee_application, create_investigation_record,
    create_investigation_task, create_notary_from_clue, customer_review_investigation_clue, delete_investigation_evidence, export_investigation_clues,
    export_investigation_handover, file_evidence, get_investigation_clue_workspace, import_investigation_clues, import_investigation_notaries,
    import_notary_certificate_file, import_notary_invoice_file, import_notary_storage, investigation_action_capabilities, investigation_assignment_supervisor,
    list_investigation_clue_reviewer_candidates, list_investigation_materials, list_investigation_parties, list_investigation_tasks, list_notary_files,
    notary_import_template, organize_evidence, register_clue_collection, register_clue_collection_batch, resolve_clue_case_contracts,
    review_investigation_clue, submit_investigation_clue, turn_on_investigation_clue_audit, update_evidence_record, update_investigation_parties,
    update_investigation_record,
)
from app.areas.ipr.router import (
    add_ipr_cases_to_annual_fee_monitoring, batch_create_ipr_cases, batch_ipr_official_file_action, batch_ipr_official_history_action, batch_maintain_ipr_cases,
    batch_upload_ipr_case_file, close_ipr_case, complete_ipr_official_file, confirm_ipr_case_assisted_fee, confirm_ipr_case_file_custom_import_candidates,
    confirm_ipr_official_import_candidates, correct_ipr_case_file_custom_import_candidate, correct_ipr_official_import_candidate, create_ipr_case, create_ipr_case_annual_fee,
    create_ipr_case_assisted_fee, create_ipr_case_fee, create_ipr_case_fee_arrival, create_ipr_case_fee_invoice, create_ipr_case_fee_payment_application,
    create_ipr_case_fee_payment_type, create_ipr_case_file_custom_import_batch, create_ipr_case_log, create_ipr_case_reminder, create_ipr_case_task,
    create_ipr_litigation_court, create_ipr_litigation_party, create_ipr_official_import_batch, create_ipr_reminder_type, create_ipr_warning_rule,
    delete_ipr_case_annual_fee, delete_ipr_case_assisted_fee, delete_ipr_case_fee, delete_ipr_case_file, delete_ipr_case_log,
    delete_ipr_case_reminder, delete_ipr_litigation_court, delete_ipr_litigation_party, delete_ipr_official_file, delete_ipr_reminder_type,
    delete_ipr_warning_rule, download_ipr_official_files_zip, export_ipr_cases_excel, export_ipr_cases_word, export_ipr_official_file_checklist,
    export_ipr_official_files_excel, generate_ipr_case_application_file, generate_ipr_case_document, generate_ipr_warnings, get_ipr_case,
    get_ipr_case_reminder_suppressions, get_ipr_litigation_court_info, list_ipr_case_annual_fees, list_ipr_case_assisted_fees, list_ipr_case_customer_candidates,
    list_ipr_case_customer_contact_candidates, list_ipr_case_customer_contacts, list_ipr_case_customers, list_ipr_case_fee_payment_types, list_ipr_case_fees,
    list_ipr_case_file_custom_import_batches, list_ipr_case_file_custom_import_candidates, list_ipr_case_file_types, list_ipr_case_files, list_ipr_case_law_firm_candidates,
    list_ipr_case_law_firms, list_ipr_case_logs, list_ipr_case_reminders, list_ipr_case_tasks, list_ipr_cases,
    list_ipr_cases_by_reminder_type, list_ipr_lawsuit_cases, list_ipr_litigation_courts, list_ipr_litigation_parties, list_ipr_official_file_checklist,
    list_ipr_official_files, list_ipr_official_import_batches, list_ipr_official_import_candidates, list_ipr_reminder_event_types, list_ipr_reminder_types,
    list_ipr_warning_rules, list_ipr_warnings, maintain_ipr_case, mark_ipr_case_file_transmitted, mark_ipr_case_files_transmitted,
    match_ipr_case_file_custom_import_candidate, match_ipr_official_import_candidate, preview_ipr_case_reboot, process_ipr_warning, read_ipr_warning,
    reboot_ipr_case, remove_ipr_cases_from_annual_fee_monitoring, reopen_ipr_case, replace_ipr_case_customer_contacts, replace_ipr_case_customers,
    replace_ipr_case_law_firms, replace_ipr_case_reminder_suppressions, review_ipr_case, submit_ipr_case, transact_ipr_case_assisted_fee,
    transmit_ipr_official_file, unlock_ipr_case_fee, unlock_ipr_case_file, update_ipr_case, update_ipr_case_annual_fee,
    update_ipr_case_assisted_fee, update_ipr_case_links, update_ipr_case_reminder, update_ipr_litigation_court, update_ipr_litigation_court_info,
    update_ipr_litigation_party, update_ipr_reminder_type, update_ipr_warning_rule, upload_ipr_case_file, upload_ipr_official_file,
    validate_ipr_official_file,
)
from app.areas.legal.router import (
    acquire_case_word_editor_lock, approve_seal_application, archive_case, archive_readiness, archive_seal_application,
    assign_case, batch_delete_case_events, batch_delete_seal_attachments, batch_download_seal_files, batch_stamp_seal_applications,
    batch_update_cases, batch_withdraw_seal_applications, case_agent_state, case_agent_status, case_detail_action_capabilities,
    case_list_action_capabilities, case_summary, close_case_for_archive, complete_case_creation, confirm_case_assisted_fee,
    create_case, create_case_ai_draft, create_case_assisted_fee, create_case_batch_fees, create_case_commissions,
    create_case_document_folder, create_case_event, create_case_log, create_case_reminder, create_communication,
    create_hearing, create_record, create_seal_application, create_seal_asset, decide_case_agent_action,
    delete_case, delete_case_assisted_fee, delete_case_attachments, delete_case_document_folder, delete_case_event,
    delete_case_reminder, delete_communication, delete_communication_attachment, delete_hearing, delete_record,
    delete_seal_application, delete_seal_asset, download_case_attachments, duplicate_case, export_counsel_cases,
    export_records, export_records_excel, export_selected_case_archive_manifest, export_selected_case_qr_word, export_selected_ordinary_cases_excel,
    finish_case_tasks, generate_case_document, get_case_ai_draft_content, get_case_ai_space, get_case_space_context,
    get_case_word_editor_content, get_case_workflow_guide, get_record, hearing_sms_outbox, import_business_records,
    import_case_invoice_files, list_case_assisted_fees, list_case_document_folders, list_case_eligible_contracts, list_case_events,
    list_case_fee_contracts, list_case_litigant_candidates, list_case_logs, list_case_phases, list_case_reference_options,
    list_case_relations, list_case_reminders, list_case_tasks, list_communication_attachments, list_communications,
    list_hearings, list_pending_execution_cases, list_records, list_seal_application_files, list_seal_applications,
    list_seal_asset_audit, list_seal_assets, maintain_criminal_courts, maintain_criminal_litigants, maintain_criminal_procuratorates,
    maintain_criminal_public_security, merge_case, move_case_attachments, package_download_seal_files, preview_case_commissions,
    promote_case_ai_draft, record_history, records_import_template, release_case_word_editor_lock, rename_case_attachment,
    rename_case_document_folder, renew_case_word_editor_lock, request_case_unarchive, review_case_archive, review_case_creation,
    review_case_unarchive, search_counsel_cases, search_ordinary_cases, send_case_agent_message, stamp_seal_application,
    submit_seal_application, transition_record, unlock_case_attachment, update_arbitration_case_basic, update_case_ai_draft_content,
    update_case_assisted_fee, update_case_court_info, update_case_event, update_case_execution_status, update_case_hearing_lawyer,
    update_case_judicial, update_case_litigants, update_case_litigants_from_detail, update_case_notary_info, update_case_phase,
    update_case_progress, update_case_settlement_amount, update_case_word_editor_content, update_communication, update_counsel_case_basic,
    update_normal_case_basic, update_record, update_seal_application, update_seal_asset, upload_communication_attachment,
    upload_seal_application_files, withdraw_seal_application,
)
from app.areas.rpt.router import (
    customer_roi_report, download_report, export_customer_roi_report, export_report_analytics, export_report_staff_roi,
    generate_report, report_analytics, report_large_screen, report_staff_roi, report_summary,
)
from app.areas.system.router import (
    agent_chat, autocomplete_system_causes, bind_dingtalk_login, bind_system_user_dingtalk, clear_all_system_caches,
    clear_system_cache, clear_system_caches, confirm_agent_document, create_agent_document, create_system_menu,
    create_system_parameter, create_system_user, create_template, create_user_agent_skill, current_user_profile,
    dashboard, delete_agent_document, delete_attachment, delete_notification, delete_smoke_agent_document,
    delete_smoke_case, delete_smoke_ipr_official_import_batch, delete_smoke_record, delete_system_menu, delete_system_parameter,
    delete_system_user, delete_template, delete_test_ipr_case_file_custom_import_batch, delete_user_agent_skill, dingtalk_login,
    dingtalk_login_config, download_agent_document, download_attachment, get_attachment, get_legacy_case_task_history,
    get_legacy_historical_attachment, get_pdf_preview_metadata, get_security_policy, get_system_user_permissions, get_template,
    global_search, health, list_active_people_options, list_agent_documents, list_attachments,
    list_audit_events, list_legacy_case_task_history_graph, list_legacy_historical_attachments, list_notifications, list_role_permissions,
    list_system_caches, list_system_configs, list_system_menus, list_system_parameter_categories, list_system_parameter_options,
    list_system_parameter_relations, list_system_parameters, list_system_users, list_templates, list_user_agent_skills,
    login, navigation_menus, preview_attachment, read_all_notifications, read_notification,
    render_pdf_preview_page, replace_system_parameter_relations, reset_system_menus, reset_system_user_password, retry_agent_document,
    send_user_message, unlock_system_user, update_agent_document, update_current_user_profile, update_role_permission,
    update_security_policy, update_system_config, update_system_menu, update_system_parameter, update_system_user,
    update_system_user_permissions, update_template, update_user_agent_skill, upload_attachment, upload_user_agent_skill,
    user_directory, writeback_agent_document,
)
from app.areas.tp.router import (
    accept_task, add_task_comment, batch_lifecycle_tasks, batch_read_task_messages, batch_update_tasks,
    complete_task, confirm_task, create_task, create_task_feedback, create_vip_task,
    create_vip_task_message, create_vip_task_node, delete_vip_task, delete_vip_task_node, export_task_print_table,
    get_vip_task, handoff_task, list_tasks, list_unread_task_messages, list_vip_task_messages,
    list_vip_task_nodes, list_vip_tasks, mark_task_history_unread, read_task_messages, read_vip_task_messages,
    reject_task, request_task_exception, resend_task, restart_task, review_task_exception,
    task_history, update_vip_task, update_vip_task_node, upload_task_materials, withdraw_task,
)
from app.areas.wms.router import (
    batch_register_evidence, borrow_warehouse_item, check_in_warehouse_evidence, check_out_warehouse_evidence, confirm_warehouse_return,
    create_warehouse_evidence, destroy_warehouse_evidence, import_evidence_records, list_evidence_files, list_evidence_records,
    list_warehouse_evidence, recheck_in_warehouse_evidence, register_evidence, return_warehouse_item, scrap_warehouse_item,
    update_warehouse_evidence, warehouse_catalog, warehouse_goods_list, warehouse_storage_location_goods_count_list,
)
from app.core.cases import (
    _active_case_phase_values, _case_action_granted, _case_ai_draft, _case_ai_draft_bytes, _case_ai_draft_name,
    _case_archive_checks, _case_commission_person_tokens, _case_commission_preview, _case_conflict_entities, _case_copy_root,
    _case_copy_suffix, _case_event_dict, _case_event_mutable_by, _case_event_status, _case_file_type_tree,
    _case_party_match_values, _case_party_values, _case_phase_changed_days, _case_phase_is_allowed, _case_phase_option,
    _case_team_payload, _case_team_role, _case_type_parameter_for_value, _clean_case_litigant_values, _commission_scheme_for_case,
    _criminal_detail_maintenance_case, _dashboard_case_hearing, _dashboard_latest_case_row, _delete_case_events_for_case_cleanup, _hearing_dict,
    _is_civil_case_type, _is_pending_execution_case, _is_urgent_case, _large_screen_case_is_closed, _large_screen_case_is_excluded,
    _matches_dashboard_case_queue, _next_case_copy_serial, _next_case_serial, _ordinary_case_export_rows, _persist_case_litigants,
    _phase_is_builtin_for_case_type, _prioritize_new_case_assistants, _query_counsel_cases, _resolve_active_case_people, _resolve_case_phase,
    _selected_ordinary_case_export_records, _validate_case_execution_status,
)
from app.core.constants import (
    ADMINISTRATIVE_CLIENT_POSITIONS, AGENT_ACTION_CAPABILITY, AGENT_CASE_DATA_FIELDS, AGENT_CASE_UPDATE_FIELDS, AI_SPACE_CATEGORY,
    AI_SPACE_EDITABLE_SUFFIXES, ARCHIVE_REQUIRED_CATEGORIES, ATTACHMENT_TEXT_PREVIEW_MAX_CHARS, CASE_CLIENT_POSITIONS_BY_TYPE, CASE_COMMISSION_ROLES,
    CASE_CREATABLE_TYPES, CASE_CREATE_PERMISSION_BY_TYPE, CASE_CREATE_PERMISSION_KEYS, CASE_CREATE_STATUS_ALIASES, CASE_CUSTOM_DOCUMENT_FOLDERS_KEY,
    CASE_DEFENDANT_FIELDS, CASE_DOCUMENT_CATEGORY, CASE_DOCUMENT_FOLDER_HEADERS, CASE_DOCUMENT_TYPES, CASE_EVENT_COMPLETED_STATUS,
    CASE_EVENT_OVERDUE_STATUS, CASE_EVENT_PENDING_STATUS, CASE_EVENT_TIME_ZONE, CASE_EXECUTION_STATUSES, CASE_EXECUTION_STATUS_ALIASES,
    CASE_FORMAL_DOCUMENT_FOLDERS, CASE_FORMAL_DOCUMENT_FOLDER_ORDER, CASE_INVESTIGATION_DOCUMENT_FOLDERS, CASE_LEGACY_LAW_FIRM_LETTER_TYPES, CASE_PARTY_SEPARATOR,
    CASE_PENDING_EXECUTION_PHASES, CASE_PHASE_STATUS_BY_CODE, CASE_PLAINTIFF_FIELDS, CASE_SOURCE_CONTRACT_STATUSES, CASE_THIRD_PARTY_FIELDS,
    CIVIL_CASE_TYPES, CONTRACT_APPROVAL_ACTION_CODE, CONTRACT_APPROVED_STATUS, CONTRACT_NON_PERSON_NAME_MARKERS, CONTRACT_PERSON_NAME_PATTERN,
    CONTRACT_PERSON_NAME_PLACEHOLDER, COURT_JUDICIAL_KEYS, CRIMINAL_JUDICIAL_PREFIXES, CUSTOMER_CREATE_DATA_FIELDS, CUSTOMER_CREATE_STATUSES,
    CUSTOMER_LEVELS, CUSTOMER_MODIFICATION_ACTIONS, CUSTOMER_SYSTEM_DATA_FIELDS, DASHBOARD_CASE_QUEUES, DASHBOARD_SUPPLEMENT_EVIDENCE_STATUSES,
    DASHBOARD_SUPPLEMENT_OPINION_STATUSES, DEFAULT_DEPARTMENTS, DEFAULT_JOB_ROLES, DEFAULT_MENU_LABEL_BY_KEY, DEFAULT_ROLE_PERMISSIONS,
    DEFAULT_SYSTEM_CONFIGS, DEFAULT_SYSTEM_MENUS, DEFAULT_SYSTEM_PARAMETERS, EXPENSE_SCOPE_FEE_TYPES, EXPENSE_SUBTYPE_FEE_TYPE,
    FEE_TYPE_BASE_SCOPES, FEE_TYPE_ROOT_BASES, FIELD_KEYS, FIELD_PERMISSION_DATA_KEYS, FINANCE_DEFAULT_VOUCHER_CATEGORY,
    FINANCE_FEE_TYPES, FINANCE_PAYMENT_CANCELABLE_STATUSES, FINANCE_PAYMENT_ROLLBACKABLE_STATUSES, FINANCE_TRANSACTION_TYPES, FINANCE_VOUCHER_CATEGORIES,
    GENERIC_RECORD_DELETABLE_MODULES, GENERIC_RECORD_EDITABLE_MODULES, GENERIC_RECORD_TRANSITION_MODULES, HR_SUBRECORD_KINDS, INVESTIGATION_CREATE_STATUS_BY_MODULE,
    INVESTIGATION_EDIT_DATA_FIELDS, INVESTIGATION_MATERIAL_CATEGORIES, INVESTIGATION_RECORD_MODULES, INVOICE_RELEASED_STATUSES, IPR_CASE_CATEGORIES,
    IPR_CASE_DOCUMENT_TYPES, IPR_CASE_DRAFT_STATUSES, IPR_CASE_KINDS, IPR_REMINDER_EVENT_TYPES, IPR_REMINDER_EVENT_TYPE_BY_ID,
    IPR_WARNING_TIME_NODES, JAR_FEE_MODULE, JAR_FEE_STATUSES, JAR_FEE_TRANSITIONS, JOB_ACTION_MENU_GRANTS,
    JOB_ROLE_ACTION_KEY_GRANTS, JOB_ROLE_LABEL_MENU_GRANTS, LEGACY_ADMIN_MENU_KEYS, LEGACY_CONTRACT_STATUS_BY_NEW, LEGACY_FINANCE_MENU_KEYS,
    LEGACY_INVESTIGATION_CLUE_STATUS, LEGACY_INVESTIGATION_MENU_KEYS, LEGACY_INVESTIGATION_STATUS, LEGACY_INVESTIGATION_TASK_STATUS, LEGACY_IPR_REMINDER_TYPE_SEEDS,
    LEGACY_OFFICIAL_DOCUMENT_STATUS, LEGACY_TASK_MENU_KEYS, LEGACY_UPLOAD_ROOTS, MENU_CHILDREN_BY_KEY, MENU_KEYS,
    MENU_PARENT_BY_KEY, NORMAL_CASE_BASIC_TYPES, ORIGINAL_ADMIN_MENU_KEYS, ORIGINAL_FINANCE_MENU_KEYS, ORIGINAL_INVESTIGATION_MENU_KEYS,
    PARAMETER_REFERENCE_FIELDS, PDF_PREVIEW_MAX_DIMENSION, PDF_PREVIEW_MAX_FILE_BYTES, PDF_PREVIEW_MAX_PAGES, PDF_PREVIEW_MAX_PIXELS,
    PDF_PREVIEW_MAX_WIDTH, PDF_PREVIEW_MIN_WIDTH, PERSON_NAME_NON_PERSON_MARKERS, PERSON_NAME_PLACEHOLDER, RECORD_IMPORT_COLUMNS,
    RECORD_IMPORT_SAMPLES, RECORD_MODULE_MENU_ROOTS, RECORD_PERSON_FIELDS_BY_MODULE, RECORD_PERSON_LIST_FIELDS_BY_MODULE, REFUND_CASE_FEE_STATUSES,
    REFUND_CASE_FEE_STATUS_BY_LABEL, REFUND_GROUP_ALIASES, REFUND_LIST_STATUSES, REFUND_PAGE_SIZES, REQUIRED_SEAL_ASSETS,
    REQUIRED_SEAL_TYPES, ROLE_DATA_SCOPES, SEAL_ACTION_CODES, SEAL_APPLICATION_FILE_CATEGORY, SEAL_STAMPED_FILE_CATEGORY,
    SEAL_USE_TYPES, SYSTEM_ACTION_BY_CODE, SYSTEM_ACTION_DEFINITIONS, SYSTEM_ACTION_OPERATION_LABELS, SYSTEM_ADMIN_JOB_PERMISSIONS,
    SYSTEM_CACHE_META, SYSTEM_CACHE_REGISTRY, SYSTEM_MENU_ROUTE_KEYS, SYSTEM_PARAMETER_CACHE, SYSTEM_PARAMETER_CATEGORIES,
    SYSTEM_PARAMETER_RELATION_CONFIG, SYSTEM_USER_ROLE_CODES, UPLOAD_ROOT, VIP_TASK_PRIORITIES, VIP_TASK_STATUSES,
    WORD_DOCUMENT_CONTENT_TYPE, WORD_EDITOR_LOCK_SECONDS, WORKFLOW_TRANSITIONS, XLSX_PREVIEW_MAX_COLUMNS, XLSX_PREVIEW_MAX_ROWS_PER_SHEET,
    XLSX_PREVIEW_MAX_SHEETS, _BUILTIN_DOCUMENT_TEMPLATES, _CASE_HEARING_LEVELS, _INVALID_RECEIVABLE_FEE_STATUSES, _LEGACY_CASE_TASK_HISTORY_ENTITIES,
    _OFFICIAL_RECEIVABLE_FEE_WORDS, _contract_serial_lock, _menu_key, _menu_parent_key, _system_action_definitions,
    case_agent_runtime, logger,
)
from app.core.contracts import (
    _contract_allows_downstream_creation, _contract_archive_rows, _contract_customer_manager_values, _contract_customer_record_dict, _contract_customer_record_dicts,
    _contract_customer_source_person, _contract_event_dict, _contract_events_payload, _contract_investigation_source_data, _contract_object_payload,
    _contract_object_writable, _contract_person_values, _create_contract_event_for_record, _delete_contract_records, _has_explicit_contract_approval_action,
    _is_contract_approver, _next_contract_serial_no, _resolve_clue_source_contract, _resolve_contract_customer, _single_linked_case_for_contract,
    _stored_contract_guid, _user_has_contract_approval_action, _valid_contract_chinese_person_name, _valid_contract_person_name,
)
from app.core.crm import (
    _active_customer_usernames, _case_customer_has_vip_marker, _case_is_for_allocation_customer, _conflict_customer_managers, _create_law_firm_record,
    _customer_by_guid, _customer_contact_dict, _customer_contact_or_404, _customer_event, _customer_files_by_guid,
    _customer_guid, _customer_has_vip_marker, _customer_linked_business_counts, _customer_or_404, _customer_reference_from_maps,
    _customer_roi_analytics, _dashboard_customer_for_case, _empty_customer_conflict_result, _law_firm_audit_dict, _law_firm_contact_dict,
    _law_firm_dict, _law_firm_license, _law_firm_or_404, _locked_customer_or_404, _mark_customer_modified,
    _next_customer_serial_no, _persist_case_litigant_customers, _portal_customer, _prioritize_new_customer_managers, _resolve_active_customer_managers,
    _sync_customer_contact_metrics,
)
from app.core.dependencies import (
    AgentDocument, Annotated, AsyncSession, Base, BaseModel,
    BusinessRecord, CORSMiddleware, CPC_APPLICATION_CATEGORY, CUSTOM_SKILL_FILE_LIMIT, CUSTOM_SKILL_LIMIT,
    CaseAssistedFee, CaseEvent, CaseFileTypeFeeTypeRelation, CaseTypeCasePhaseRelation, CaseTypeFileTypeRelation,
    Cm, CommunicationLog, ContractApprovalStep, ContractEvent, ContractObject,
    ContractObjectLog, ContractPaymentLine, Decimal, Department, Depends,
    DingTalkError, Document, DocumentTemplate, FastAPI, Field,
    File, FileAttachment, FileResponse, FinanceTransaction, Form,
    GENERAL_SKILL, HTTPException, HearingSchedule, HrSubrecord, Inches,
    IncomingPayment, IntegrityError, InvestigationClueLink, InvestigationEvidence, InvestigationEvidenceFile,
    InvestigationHistoricalReference, InvestigationTaskLink, IprCaseAnnualFee, IprCaseAssistedFee, IprCaseBatch,
    IprCaseBatchItem, IprCaseCustomer, IprCaseCustomerContact, IprCaseFileCustomImportBatch, IprCaseFileCustomImportCandidate,
    IprCaseLawFirm, IprCaseLog, IprCaseRebootLink, IprCaseReminder, IprCaseReminderSuppression,
    IprCaseReminderType, IprCaseWarning, IprCaseWarningRule, IprOfficialImportBatch, IprOfficialImportCandidate,
    JSONResponse, JarFeeAuditLog, JobRole, LawFirm, LawFirmAudit,
    LawFirmContact, LegacyCase, LegacyCaseFile, LegacyCaseLog, LegacyCaseParticipant,
    LegacyCaseTaskHistory, LegacyCaseTaskHistoryFile, LegacyCaseTaskHistoryMessage, LegacyCaseTaskHistoryNode, LegacyCaseTaskHistoryNodeParticipant,
    LegacyCaseTaskHistoryNotification, LegacyCaseTaskHistoryReadReceipt, LegacyContract, LegacyContractAudit, LegacyContractFile,
    LegacyCustomer, LegacyCustomerContact, LegacyCustomerHistoryBaseline, LegacyCustomerHistoryContact, LegacyCustomerHistoryCoordinator,
    LegacyCustomerHistoryEvent, LegacyCustomerHistoryFile, LegacyFinanceAllocation, LegacyFinanceAudit, LegacyFinanceFile,
    LegacyFinanceRecord, LegacyHistoricalAttachment, LegacyInvestigation, LegacyInvestigationClue, LegacyInvestigationClueEvidence,
    LegacyInvestigationClueEvidenceFile, LegacyInvestigationClueFile, LegacyInvestigationTask, LegacyOfficialDocument, LegacyOfficialDocumentAudit,
    LegacyOfficialDocumentFile, Literal, NAMESPACE_URL, Notification, OAuth2PasswordRequestForm,
    OfficialOutgoingDocument, Path, Pt, Query, ROUND_UP,
    ReceivablePlan, ReconciliationBatch, Request, RequestValidationError, Response,
    RolePermission, SKILLS_BY_ID, SQLAlchemyError, SealAsset, SealAssetAudit,
    SecurityPolicy, SessionLocal, StreamingResponse, String, SystemConfig,
    SystemMenu, SystemParameter, UploadFile, User, VipTask,
    VipTaskMessage, VipTaskNode, WD_ALIGN_PARAGRAPH, Warehouse, WarehouseEvidenceLocation,
    WarehouseLegacyEvidenceMapping, WarehouseStorageLocation, WorkflowEvent, ZoneInfo, align_legacy_column_types,
    align_legacy_constraints, align_legacy_indexes, and_, asynccontextmanager, asyncio,
    base64, build_case_workflow_guide, create_case_agent_runtime, create_full_legacy_schema, create_ipr_cpc_router,
    create_legacy_contract_history_router, create_legacy_ipr_history_router, create_legacy_ls_history_router, create_token, csv,
    ctypes, current_identity, custom_skill_agent, custom_skill_public, date,
    datetime, delete, dingtalk_client, engine, ensure_legacy_indexes,
    false, field_validator, func, gc, get_db,
    hash_password, hashlib, httpx, inspect, io,
    ipr_fee_file_router, is_cpc_application_attachment, json, load_workbook, logging,
    math, normalize_custom_skill, or_, parse_uploaded_skill, password_needs_rehash,
    pdfium, public_skill_catalog, qn, qrcode, quote,
    re, read_attachment, secrets, select, settings,
    status, suppress, sys, text, timedelta,
    timezone, unicodedata, update, user_role_ids, user_skill_config_key,
    uuid4, uuid5, verify_password, xml_escape, zipfile,
)
from app.core.documents import (
    _acquire_case_word_editor_lock, _agent_content_hash, _agent_document_dict, _agent_document_operation_result, _build_case_template_data,
    _case_agent_changes, _case_custom_document_folders, _case_document_bytes, _case_document_context, _case_document_paragraph,
    _case_document_required_fields, _case_document_value, _case_formal_document_folder_payload, _case_related_document_record, _clean_case_litigant_agents,
    _execute_case_agent_action, _fill_template, _get_seal_application, _get_seal_application_for_action, _next_seal_application_serial,
    _replace_word_editor_blocks, _run_document_agent, _save_user_agent_skills, _seal_asset_audit_dict, _seal_asset_dict,
    _seal_authorization_context, _seal_legacy_file_names, _seal_record_dict, _sync_case_document_readiness, _sync_seal_document_names,
    _template_dict, _user_agent_skill_store, _user_has_seal_action, _validate_case_formal_document_category, _validated_seal_relations,
    _word_editor_blocks, _word_editor_lock_payload, _word_editor_now, _word_editor_paragraph_editable, _word_editor_version,
)
from app.core.finance import (
    _active_payment_type, _active_payment_type_rows, _archive_settlement_decision_rows, _case_assisted_fee_dict, _case_assisted_fee_for_case,
    _case_fee_contract_body, _case_fee_link_maps, _case_fee_type_snapshot, _contract_payment_candidate_rows, _create_payment_type,
    _editable_finance_fee, _editable_invoice_application, _editable_jar_fee, _editable_refund_case_fees, _fee_inform_dict,
    _fee_inform_record, _fee_matches_contract_object, _fee_query_rows, _fee_type_base_from_root, _fee_type_catalog,
    _finance_fee_commission_details, _finance_fee_readiness, _finance_linked_case, _finance_payment_type_dict, _finance_payment_type_for_fee,
    _finance_transaction_dict, _general_settlement_rows, _incoming_payment_dict, _incoming_payment_legacy_summary, _internal_fee_mutation_target,
    _internal_fee_payment_status, _internal_fee_row, _internal_fee_rows, _invoice_case_fee_rows, _invoice_linked_fee_ids,
    _invoice_list_rows, _invoice_original_type, _ipr_annual_fee_dict, _ipr_annual_fee_reminder_content, _ipr_assisted_fee_dict,
    _ipr_case_assisted_fee_row, _ipr_case_fee, _ipr_case_fee_row, _ipr_case_fee_rows, _jar_fee_audit,
    _jar_fee_contract, _jar_fee_data, _jar_fee_dict, _jar_fee_or_404, _new_internal_payment_package_no,
    _payment_package_for_word, _pending_archive_settlement_rows, _prepare_internal_payment_package, _receivable_dict, _receivable_fee_category,
    _receivable_number, _receivable_relation_id, _reconciliation_dict, _refund_case_fee_authorized_ids, _refund_case_fee_rows,
    _refund_case_fee_started_at, _refund_case_fee_status, _refund_export_request, _refund_export_response, _refund_group,
    _refund_query_rows, _rejected_archive_settlement_records, _resolve_case_fee_contract, _resolve_case_fee_link_id, _resolve_case_fee_type_master,
    _review_finance_fee_records, _round_fee_amount, _set_ipr_annual_fee_monitoring, _settlement_fee_kind, _sync_ipr_annual_fee_reminder,
    _validate_invoice_source_links, _validate_ipr_annual_fee_values,
)
from app.core.formatters import (
    _apply_record_person_displays, _case_agent_date, _case_agent_required_text, _case_ai_draft_text, _case_assistant_display,
    _case_event_display_time, _case_fee_date, _case_fee_display_type, _case_filing_date, _case_hearing_datetime,
    _case_phase_changed_date, _contract_person_display_name, _convert_notary_to_case, _csv_date, _dashboard_case_date,
    _dashboard_text, _dingtalk_allowed_display_names, _format_case_document, _investigation_task_date, _is_complete_person_display_name,
    _normalize_case_document_folder_name, _normalize_case_numbers, _normalize_conflict_entity, _normalize_customer_name, _normalize_customer_yes_no,
    _normalize_external_contract_numbers, _normalized_customer_name, _normalized_fee_type_extra, _parse_customer_contact_at, _parse_ipr_batch_date,
    _parse_ipr_official_candidate_date, _person_display_name, _person_reference_display, _record_belongs_to_customer, _record_links_to_case,
    _staff_roi_date_matches, _sync_agent_document_to_case_ai_space, _task_display_dict, _task_display_dicts, _task_display_with_users,
    _user_display_map, _warehouse_location_display,
)
from app.core.investigation import (
    _apply_clue_submission, _apply_notary_auto_conversion, _build_evidence_record, _configured_investigation_supervisor, _create_collection_evidence_record,
    _import_notary_named_file, _investigation_authorization_expired, _is_investigation_task, _next_investigation_clue_serial, _register_clue_collection,
    _resolve_investigation_task_root, _resolve_warehouse_location, _set_warehouse_evidence_location, _sync_case_notary_warehouse_evidence, _sync_investigation_materials,
    _sync_investigation_relation_links, _validate_clue_submission, _warehouse_evidence_dict, _warehouse_evidence_location_statement, _warehouse_evidence_status,
    _warehouse_goods_legacy_row, _warehouse_location_data,
)
from app.core.ipr import (
    _active_ipr_case_file_type, _custom_ipr_filename_parts, _ipr_case_contact_candidates, _ipr_case_customer_dict, _ipr_case_customer_links,
    _ipr_case_document_bytes, _ipr_case_export_headers, _ipr_case_export_values, _ipr_case_file_type_dict, _ipr_case_list_conditions,
    _ipr_case_log_dict, _ipr_case_matches_reminder_type, _ipr_case_reminder_dict, _ipr_cases_for_reminder_type, _ipr_custom_candidate_dict,
    _ipr_law_firm_dict, _ipr_litigation_rows, _ipr_reminder_type_dict, _ipr_reminder_type_or_404, _ipr_reminder_type_query_object,
    _ipr_warning_dict, _ipr_warning_for_recipient, _ipr_warning_rule_dict, _materialize_ipr_case_warnings, _next_ipr_case_serial,
    _next_ipr_official_file_serial, _next_ipr_reboot_serial, _refresh_ipr_custom_candidate, _save_ipr_litigation_data, _seed_legacy_ipr_reminder_types,
    _validate_ipr_warning_rule_payload,
)
from app.core.legacy_sync import (
    _legacy_case_amount, _legacy_case_datetime, _legacy_case_fee_projection, _legacy_case_list, _legacy_case_number_values,
    _legacy_case_task_history_dict, _legacy_case_task_history_item_dict, _legacy_case_text, _legacy_contract_business_failure_response, _legacy_contract_datetime,
    _legacy_contract_float, _legacy_contract_int, _legacy_customer_business_failure_response, _legacy_customer_history_item, _legacy_customer_history_users,
    _legacy_evidence_status, _legacy_failure_response, _legacy_finance_audit_table_exists, _legacy_finance_business_failure_response, _legacy_finance_record_dict,
    _legacy_finance_scope_conditions, _legacy_historical_attachment_dict, _legacy_official_document_customer_no, _legacy_projection_pk, _legacy_region,
    _legacy_snapshot_value, _legacy_yes_no, _sync_legacy_case, _sync_legacy_case_relations, _sync_legacy_contract,
    _sync_legacy_contract_audit, _sync_legacy_contract_files, _sync_legacy_customer, _sync_legacy_customer_contacts, _sync_legacy_investigation,
    _sync_legacy_investigation_clue, _sync_legacy_investigation_clue_evidence, _sync_legacy_investigation_task, _sync_legacy_official_audit, _sync_legacy_official_document,
    _sync_legacy_official_document_files, _sync_legacy_projection,
)
from app.core.lifecycle import (
    _backfill_clue_generated_case_register_dates, _upgrade_schema, lifespan, request_validation_error_handler,
)
from app.core.permissions import (
    _agent_document_capabilities, _agent_skill_catalog_for_identity, _agent_skill_for_identity, _apply_job_role_policy, _can_act_on_contract_approval_step,
    _case_detail_action_capabilities, _case_event_access, _case_mine_scope_condition, _case_personal_scope_condition, _configured_user_job_role_name,
    _denied_job_role_payload, _effective_job_role_action_keys, _effective_job_role_menu_keys, _ensure_active_ipr_case_write, _ensure_agent_document_access,
    _ensure_attachment_record_visible, _ensure_case_assisted_fee_write, _ensure_case_document_folder_name_available, _ensure_case_fixed_tasks, _ensure_case_word_editor_not_locked,
    _ensure_contract_approval_access, _ensure_contract_by_guid, _ensure_contract_object_not_reserved, _ensure_ipr_case_assisted_fee_write, _ensure_ipr_case_fee_write,
    _ensure_ipr_case_file_write, _ensure_ipr_custom_import_batch_visible, _ensure_ipr_import_batch_visible, _ensure_ipr_litigation_case_write, _ensure_legacy_case_task_history_visible,
    _ensure_record_module, _ensure_record_visible, _ensure_refund_company_record, _ensure_system_user_lifecycle_safe, _ensure_unique_customer_name,
    _ensure_unique_dingtalk_user_id, _expand_menu_permission_keys, _filter_visible_attachments, _find_visible_ipr_case_by_legacy_no, _hr_duplicate_identity_canonical,
    _hr_duplicate_identity_group, _hr_record_identity_tokens, _identity_role_ids, _ipr_annual_fee_capabilities, _ipr_case_assisted_fee_capabilities,
    _ipr_case_role_view_conditions, _jar_fee_capabilities, _job_role_dict, _job_role_for_name, _job_role_menu_permission_keys,
    _normalize_job_role_data_scope, _normalize_job_role_field_keys, _normalize_system_user_role_ids, _organization_permission_tree, _permission_payload,
    _permission_payload_for_identity, _permission_payload_for_roles, _record_dict_for_identity, _record_scope_conditions, _refund_identity_department,
    _require_admin, _require_case_action, _require_case_agent_action_access, _require_case_attachment_upload_access, _require_case_court_info_write_access,
    _require_case_creation_completed, _require_case_detail_write_access, _require_case_document_write_access, _require_case_event_write_access, _require_case_note_write_access,
    _require_case_phase_change_access, _require_case_progress_write_access, _require_case_related_attachment_target, _require_case_task_write_access, _require_case_word_editor_lock,
    _require_company_task_read_scope, _require_contract_action, _require_contract_attachment_write_access, _require_contract_investigation_create_access, _require_customer_conflict_permission,
    _require_dingtalk_access, _require_hr_attachment_write_access, _require_hr_employee_action, _require_hr_employee_target_access, _require_internal_fee_payload,
    _require_investigation_clue_write_permission, _require_ipr_reminder_type_manage, _require_jar_fee_access, _require_legacy_attachment_history_access, _require_record_module_menu,
    _require_record_owner_or_manager, _require_seal_base_action, _require_task_owner_or_initiator, _require_unique_hr_display_name, _role_permission_dict,
    _scoped_export_records, _seal_application_capabilities, _settlement_application_scope, _split_role_permission_keys, _stored_menu_permission_keys,
    _system_permission_tree, _system_user_role_ids, _user_can_write_investigation_clue, _user_has_job_permission, _user_permission_overrides,
    _user_permission_payload, _validate_finance_fee_scope_subtype, _visible_ipr_cases, _visible_ipr_import_batches, _visible_legacy_contract_history_parent_keys,
    _visible_legacy_ipr_case_ids, _visible_legacy_ls_case_ids, _visible_record_ids,
)
from app.core.projections import (
    _contract_customer_projection_context, _receivable_detail_projection,
)
from app.core.storage import (
    _attachment_dict, _attachment_storage_path, _authorized_pdf_preview_attachment, _case_event_storage_time, _case_word_editor_attachment,
    _communication_attachment_context, _copy_seal_source_attachments, _docx_bytes, _ipr_case_file_attachment, _open_preview_pdf,
    _payment_package_docx_bytes, _pdf_preview_response_headers, _resolve_seal_source_attachment_ids, _xlsx_preview_text,
)
from app.core.system import (
    _active_employee_usernames, _allowed_field_keys, _approval_step_dict, _audit_hr_performance, _business_rule_loop,
    _clear_all_system_parameter_cache, _clear_parameter_cache, _clear_registered_cache, _collect_hr_employee_deletion_blockers, _commission_employee_index,
    _communication_dict, _conflict_entity_tokens, _criminal_maintenance_payload, _csv_response, _csv_value,
    _dashboard_people, _department_dict, _excel_response, _explicit_vip_value, _export_ids,
    _get_hr_performance, _hr_performance_rows, _hr_record_linked_username, _hr_subrecord_dict, _import_relation_data,
    _is_smoke_test_username, _large_screen_month_keys, _load_hr_batch_deletion_impact, _login_response, _menu_root,
    _official_outgoing_dict, _optional_record_id, _organization_page, _parameter_reference_examples, _portal_code_hash,
    _positive_record_id, _record_dict, _record_module_menu_allowed, _record_module_menu_roots, _record_organization_audit,
    _record_person_usernames, _registered_cache_is_clearable, _rename_system_username, _replace_username_value, _report_analytics,
    _save_criminal_detail, _security_policy, _security_policy_dict, _seed_business_records, _staff_roi_report,
    _system_audit, _system_cache_entry_count, _system_cache_list_payload, _system_menu_dict, _system_parameter_dict,
    _system_parameter_relation_config, _system_user_dict, _system_user_manager_profile, _unique_import_record, _validate_hr_subrecord,
    _validate_import_relation_consistency, _validate_parameter_parent, _validate_parameter_references, _validate_system_config, _vip_active_usernames,
    _vip_message_dict, _vip_node_dict, _vip_node_member, _vip_node_or_404, _vip_validate_node_transition,
    _vip_validate_schedule,
)
from app.core.tasks import (
    _active_task_username, _add_task_message_notifications, _advance_case_from_fixed_task, _apply_hearing_sms_reminders, _apply_task_auto_completion,
    _apply_task_overdue_performance, _delete_task_notifications, _dingtalk_notification_loop, _dispatch_dingtalk_notifications, _is_task_participant,
    _next_manual_task_serial, _next_rw_task_serial_no, _notification_dict, _sync_case_event_reminder, _sync_notifications,
    _task_creation_mode, _task_dict, _task_has_vip_customer, _task_or_404, _validate_case_event_reminder,
    _validate_task_deadline, _vip_task_dict, _vip_task_member, _vip_task_or_404, _vip_task_response,
    _vip_validate_task_transition,
)
from app.models_shared import (
    AgentDocumentConfirmInput, AgentDocumentInput, AgentDocumentUpdate, ArchiveCheckInput, ArchiveReviewInput,
    ArchiveSettlementPaymentReviewInput, ArchiveSettlementRejectedActionInput, ArchiveSettlementRollbackInput, AttachmentBatchInput, BatchClueCaseInput,
    CacheBatchClearInput, CaseAgentDecisionInput, CaseAgentMessageInput, CaseAgentProposedAction, CaseAiDraftCreateInput,
    CaseAiDraftPromoteInput, CaseAiDraftUpdateInput, CaseArbitrationBasicInput, CaseAssignmentInput, CaseAssistedFeeConfirmInput,
    CaseAssistedFeeCreateInput, CaseAssistedFeeUpdateInput, CaseAttachmentMoveInput, CaseAttachmentRenameInput, CaseBatchFeeInput,
    CaseBatchUpdateInput, CaseCommissionBatchInput, CaseCommissionCreateItemInput, CaseCounselBasicInput, CaseCourtInfoInput,
    CaseCreateInput, CaseCreationCompleteInput, CaseCreationReviewInput, CaseDocumentFolderInput, CaseDocumentFolderRenameInput,
    CaseEventBatchDeleteInput, CaseEventInput, CaseEventUpdateInput, CaseExecutionStatusInput, CaseFeeBatchUpdateInput,
    CaseFeeRefundLogInput, CaseHearingLawyerInput, CaseJudicialInput, CaseLitigantAgentInput, CaseLitigantsInput,
    CaseLogInput, CaseMergeInput, CaseNormalBasicInput, CaseNotaryInfoInput, CasePhaseChangeInput,
    CaseProgressInput, CaseReminderInput, CaseSettlementAmountInput, CaseTaskFinishedInput, CaseUnarchiveRequestInput,
    CaseUnarchiveReviewInput, CaseWordEditorLockInput, CaseWordEditorSaveInput, ClueBatchCollectionInput, ClueBatchSubmitInput,
    ClueCaseContractResolveInput, ClueCollectionInput, ClueReviewInput, ClueSourceContractBindingInput, ClueTurnOnAuditInput,
    CommunicationLogInput, CommunicationLogUpdate, ContractApprovalInput, ContractApproverSettingsInput, ContractArchiveClosureInput,
    ContractAttachmentBatchDeleteInput, ContractChangeInput, ContractChangeReviewInput, ContractDraftInput, ContractEventInput,
    ContractInvestigationInput, ContractObjectInput, ContractPaymentApplicationInput, ContractPaymentLineInput, ContractPaymentPayInput,
    ContractPaymentReviewInput, ContractPaymentWriteoffInput, ContractSealApplicationInput, ContractSubmitInput, ContractWholeDeleteInput,
    CounselCaseSearchInput, CriminalCourtMaintenanceInput, CriminalProcuratorateMaintenanceInput, CriminalPublicSecurityMaintenanceInput, CurrentUserUpdate,
    CustomerActionInput, CustomerContactInput, CustomerContactStatusInput, CustomerCreateInput, CustomerEventInput,
    CustomerKeyChangeInput, CustomerKeyChangeReviewInput, CustomerLevelChangeInput, CustomerLevelReviewInput, CustomerManagersInput,
    CustomerNoteInput, CustomerPatchInput, CustomerPortalActionInput, CustomerPortalActivationInput, CustomerPortalDemandInput,
    CustomerPortalLoginInput, CustomerShareInput, DepartmentInput, DepartmentUpdate, DifyRequest,
    DingTalkBindInput, DingTalkBindingInput, DingTalkLoginInput, DocumentTransitionInput, EvidenceBatchRegistrationInput,
    EvidenceCreateInput, EvidenceRegistrationItem, EvidenceUpdateInput, FinanceActionInput, FinanceFeeArrivalInput,
    FinanceFeeBatchReviewInput, FinanceFeeCommissionDetailInput, FinanceFeeInformInput, FinanceFeeInformLinksInput, FinanceFeeInput,
    FinanceFeeReviewInput, FinanceFeeUpdateInput, FinancePaymentCancelInput, FinancePaymentPackageCreateInput, FinancePaymentPackagePreviewInput,
    FinancePaymentPackageUpdateInput, FinancePaymentPackageWriteoffInput, FinancePaymentRollbackInput, FinancePaymentTypeCreateInput, FinanceReviewInput,
    FinanceSettlementApplyInput, FinanceSettlementMarkInput, FinanceSettlementPaymentInput, FinanceSettlementReapplyInput, FinanceSettlementReviewInput,
    FinanceTransactionInput, FinanceWriteoffInput, HearingInput, HrEmployeeBatchDeleteInput, HrEmployeeContractApprovalStatusInput,
    HrEmployeeCreateInput, HrEmployeeLoginStatusInput, HrEmployeeUpdateInput, HrPerformanceInput, HrSubrecordInput,
    HrSubrecordUpdate, HrTransitionInput, IncomingPaymentAllocateInput, IncomingPaymentAllocationItem, IncomingPaymentClaimInput,
    IncomingPaymentInput, IncomingPaymentRefundClaimInput, IncomingPaymentRevokeInput, IncomingPaymentSettlementItem, IncomingPaymentUpdateInput,
    InvestigationAssignmentInput, InvestigationBatchDeleteInput, InvestigationFeeInput, InvestigationPartyInput, InvestigationTaskInput,
    InvoiceApplicationInput, InvoiceDateChangeInput, InvoiceIssueInput, InvoiceNumberChangeInput, InvoiceVoidInput,
    IprCaseAnnualFeeCreateInput, IprCaseAnnualFeeMonitoringInput, IprCaseAnnualFeeUpdateInput, IprCaseAssistedFeeConfirmInput, IprCaseAssistedFeeCreateInput,
    IprCaseAssistedFeeUpdateInput, IprCaseBatchCreateInput, IprCaseBatchCreateRow, IprCaseBatchMaintenanceInput, IprCaseCreateInput,
    IprCaseCrossModuleLinkInput, IprCaseCustomerContactReplaceInput, IprCaseCustomerReplaceInput, IprCaseFeeActionInput, IprCaseFeeArrivalInput,
    IprCaseFeeCreateInput, IprCaseFeeInvoiceInput, IprCaseFeePaymentApplicationInput, IprCaseFileBatchTransmitInput, IprCaseFileCustomCandidateConfirmInput,
    IprCaseFileCustomCandidateCorrectInput, IprCaseFileCustomCandidateMatchInput, IprCaseFileTransmitInput, IprCaseLawFirmReplaceInput, IprCaseLifecycleInput,
    IprCaseLogInput, IprCaseMaintenanceInput, IprCaseRebootInput, IprCaseReminderInput, IprCaseReminderSuppressionInput,
    IprCaseReminderTypeInput, IprCaseReminderTypeQueryInput, IprCaseReminderTypeUpdateInput, IprCaseReminderUpdate, IprCaseReviewInput,
    IprCaseUpdateInput, IprCaseWarningProcessInput, IprCaseWarningRuleInput, IprCaseWarningRuleUpdateInput, IprLitigationCourtInfoInput,
    IprLitigationCourtInput, IprLitigationPartyInput, IprOfficialCandidateConfirmInput, IprOfficialCandidateCorrectInput, IprOfficialCandidateMatchInput,
    IprOfficialDualStatusInput, IprOfficialFileActionInput, IprOfficialFileBatchActionInput, JarFeeInput, JarFeeStatusInput,
    JobRoleInput, JobRolePermissionUpdate, JobRoleUpdate, LawFirmContactInput, LawFirmInput,
    LitigationRefundInput, NotaryCertificateInput, NotaryReviewInput, OfficialDocumentBatchCaseIdsInput, OfficialDocumentDeleteInput,
    OfficialDocumentProcessInput, OfficialDocumentReceiptDateInput, OfficialOutgoingBatchInput, OfficialOutgoingCreateInput, OfficialOutgoingReviewInput,
    OfficialOutgoingRollbackInput, OfficialOutgoingSubmitInput, OfficialOutgoingUpdateInput, ReceivableInput, ReceivePaymentInput,
    ReconciliationInput, RecordInput, RecordUpdate, RefundAmountUpdateInput, RefundBatchStatusInput,
    RefundCaseFeeBatchCreateInput, RefundCaseFeeBatchItemInput, RefundCompleteInput, ReportInput, RolePermissionUpdate,
    SealApplicationInput, SealApprovalInput, SealAssetInput, SealAssetUpdate, SealBatchApplicationInput,
    SealBatchStampInput, SealPackageDownloadInput, SealStampInput, SecurityPolicyUpdate, SystemConfigUpdate,
    SystemMenuInput, SystemMenuUpdate, SystemParameterInput, SystemParameterRelationReplaceInput, SystemParameterUpdate,
    SystemUserInput, SystemUserPasswordResetInput, SystemUserUpdate, TaskActionInput, TaskBatchLifecycleInput,
    TaskBatchReadInput, TaskBatchUpdateInput, TaskExceptionRequestInput, TaskExceptionReviewInput, TaskHandoffInput,
    TaskInput, TemplateInput, TemplateUpdate, TransitionInput, UserAgentSkillInput,
    UserAgentSkillUpdate, UserMessageInput, UserPermissionOverrideUpdate, VipTaskInput, VipTaskMessageInput,
    VipTaskMessageReadInput, VipTaskNodeInput, VipTaskNodeUpdateInput, VipTaskUpdateInput, WarehouseBorrowInput,
    WarehouseEvidenceCheckInInput, WarehouseEvidenceCheckOutInput, WarehouseEvidenceDestroyInput, WarehouseEvidenceInput, WarehouseEvidenceRecheckInInput,
    WarehouseGoodsListInput, WarehouseGoodsListSearchCondition, WarehouseReturnConfirmInput, WarehouseReturnInput, WarehouseScrapInput,
    WordEditorTextBlockInput,
)
from app.areas.aws.router import router as aws_router
from app.areas.contract.router import router as contract_router
from app.areas.crm.router import router as crm_router
from app.areas.finance.router import router as finance_router
from app.areas.hr.router import router as hr_router
from app.areas.investigation.router import router as investigation_router
from app.areas.ipr.router import router as ipr_router
from app.areas.legal.router import router as legal_router
from app.areas.rpt.router import router as rpt_router
from app.areas.system.router import router as system_router
from app.areas.tp.router import router as tp_router
from app.areas.wms.router import router as wms_router
from app.routing import include_route_slice, verify_route_coverage


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.exception_handler(RequestValidationError)(request_validation_error_handler)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost", "http://127.0.0.1"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
include_route_slice(app, system_router, 0, 1)
app.include_router(
    create_legacy_ipr_history_router(visible_legacy_case_ids=_visible_legacy_ipr_case_ids),
    prefix=settings.api_prefix,
)
app.include_router(ipr_fee_file_router, prefix=settings.api_prefix)
app.include_router(
    create_legacy_ls_history_router(visible_legacy_case_ids=_visible_legacy_ls_case_ids),
    prefix=settings.api_prefix,
)
app.include_router(
    create_legacy_contract_history_router(
        visible_history_parent_keys=_visible_legacy_contract_history_parent_keys,
    ),
    prefix=settings.api_prefix,
)
include_route_slice(app, system_router, 1, 36)
include_route_slice(app, crm_router, 0, 12)
include_route_slice(app, system_router, 36, 48)
include_route_slice(app, investigation_router, 0, 1)
include_route_slice(app, contract_router, 0, 2)
include_route_slice(app, system_router, 48, 52)
include_route_slice(app, legal_router, 0, 7)
include_route_slice(app, rpt_router, 0, 10)
include_route_slice(app, system_router, 52, 53)
include_route_slice(app, legal_router, 7, 9)
include_route_slice(app, contract_router, 2, 3)
include_route_slice(app, legal_router, 9, 12)
include_route_slice(app, investigation_router, 1, 3)
include_route_slice(app, aws_router, 0, 1)
include_route_slice(app, tp_router, 0, 1)
include_route_slice(app, crm_router, 12, 13)
include_route_slice(app, legal_router, 12, 15)
include_route_slice(app, crm_router, 13, 49)
include_route_slice(app, investigation_router, 3, 4)
include_route_slice(app, contract_router, 3, 4)
include_route_slice(app, finance_router, 0, 25)
include_route_slice(app, contract_router, 4, 30)
include_route_slice(app, finance_router, 25, 26)
include_route_slice(app, contract_router, 30, 37)
include_route_slice(app, finance_router, 26, 28)
include_route_slice(app, investigation_router, 4, 25)
include_route_slice(app, wms_router, 0, 5)
include_route_slice(app, investigation_router, 25, 30)
include_route_slice(app, crm_router, 49, 51)
include_route_slice(app, investigation_router, 30, 41)
include_route_slice(app, crm_router, 51, 52)
include_route_slice(app, tp_router, 1, 18)
include_route_slice(app, system_router, 53, 55)
include_route_slice(app, tp_router, 18, 35)
include_route_slice(app, finance_router, 28, 42)
include_route_slice(app, crm_router, 52, 54)
include_route_slice(app, finance_router, 42, 64)
include_route_slice(app, system_router, 55, 57)
include_route_slice(app, finance_router, 64, 82)
include_route_slice(app, legal_router, 15, 17)
include_route_slice(app, finance_router, 82, 135)
include_route_slice(app, legal_router, 17, 31)
include_route_slice(app, finance_router, 135, 137)
include_route_slice(app, legal_router, 31, 67)
include_route_slice(app, system_router, 57, 62)
include_route_slice(app, legal_router, 67, 91)
include_route_slice(app, aws_router, 1, 17)
include_route_slice(app, system_router, 62, 69)
include_route_slice(app, legal_router, 91, 110)
include_route_slice(app, aws_router, 17, 18)
include_route_slice(app, system_router, 69, 75)
include_route_slice(app, contract_router, 37, 38)
include_route_slice(app, legal_router, 110, 111)
include_route_slice(app, finance_router, 137, 140)
include_route_slice(app, legal_router, 111, 131)
include_route_slice(app, hr_router, 0, 31)
include_route_slice(app, wms_router, 5, 19)
include_route_slice(app, ipr_router, 0, 83)
app.include_router(create_ipr_cpc_router(
    ensure_visible=lambda case_id, identity, db: _ensure_record_module(case_id, "ipr_case", identity, db),
    ensure_write=_ensure_ipr_case_file_write,
    upload_root=lambda: UPLOAD_ROOT,
), prefix=settings.api_prefix)
include_route_slice(app, ipr_router, 83, 92)
include_route_slice(app, system_router, 75, 76)
include_route_slice(app, ipr_router, 92, 103)
include_route_slice(app, legal_router, 131, 132)
include_route_slice(app, ipr_router, 103, 111)
include_route_slice(app, system_router, 76, 77)
include_route_slice(app, ipr_router, 111, 121)
include_route_slice(app, legal_router, 132, 138)
include_route_slice(app, system_router, 77, 89)
verify_route_coverage(app, [aws_router, contract_router, crm_router, finance_router, hr_router, investigation_router, ipr_router, legal_router, rpt_router, system_router, tp_router, wms_router])
