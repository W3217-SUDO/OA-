# 8.28 第4行本地验收

- 问题：案件详情的客户/合同关联文档被合同状态锁误拦截，审批中或已归档合同无法上传、删除附件。
- 修复：案件详情上传关联文档时提交案件上下文；后端校验目标必须是该案件绑定的客户或合同，并按案件文档权限授权。合同中心通用附件接口仍保留审批中/已归档状态锁。
- 后端测试：`case_related_attachment_status_row4_test.py` 与 `case_document_upload_row22_test.py`，3/3 通过；`py_compile` 通过。
- 前端测试：第2、3、4行相关测试 7/7 通过。
- 生产构建：`sunhold-admin-web@1.1.27` 构建通过，5637 modules transformed。
- Codex 内置浏览器：在案件 `CODEX828R4CASE` 的“合同文档”目录，对状态为“审批中”的关联合同上传 `CODEX828R4-upload.txt` 成功，未出现合同状态限制提示；文件列表可见，随后从同一案件目录删除成功并恢复空列表。
- 浏览器日志：无业务接口错误；仅存在基线 Ant Design 弃用/上下文警告。
- 证据：`local-upload-approved-contract.png`、`local-delete-approved-contract.png`。
- 清理：测试案件、合同、客户、附件及审计事件残留均为 0；8098/5301 临时服务已停止。
