# 8.27 第13行本地验收

## 实现

- 新增独立 `can_generate_document` 能力，前后端使用同一权限口径。
- 历史、复制和导入案件不再因 `case_creation_step` 未完成而隐藏 7 项文书入口。
- 无岗位权限账号仍不可见、不可调用；归档中、已归档和已合并案件仍禁止生成。

## 自动化验证

- 后端专项及相邻回归：`case_document_generation_row13_test.py`、`case_basic_edit_creation_step_independence_row14_test.py`，6/6 通过。
- 前端九项菜单测试：`caseCompanyScheduleOperationMenuParity.test.mjs`，3/3 通过。
- Python `compileall` 通过。
- 前端生产构建通过，5636 modules transformed，版本保持 1.1.12。

## Codex 浏览器验收

- 隔离 SQLite 和本地 8043/5243 服务创建 `CODEX-827-13-BROWSER`，其 `case_creation_step=basic`。
- 案件详情“操作 -> 更多操作”完整显示 7 项文书、案件合并、复制案件，共 9 项。
- 点击“一审所函（我方原告）”后，系统提示缺少一审法院、开庭律师、律师助理、原告、被告、案由；未再出现“请先完成案件新建三步信息”。
- 验收后附件 0、流程事件 0、上传目录文件 0。
- 浏览器仅有既有 Ant Design 弃用警告，无网络错误或运行时异常。

证据：`browser-nine-actions.png`、`browser-missing-fields.png`。
