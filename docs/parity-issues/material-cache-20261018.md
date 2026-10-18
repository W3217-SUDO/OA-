# 聊天材料上传、PDF 解析与缓存交接记录

## 本轮范围

本轮处理截图所反映的新增需求：用户把 PDF、Word、表格或图片放进智能体聊天框后，发送问题时系统必须真正读取材料正文或页面图像，并把可确认内容交给大模型；同一材料在后续提问中应复用解析结果。上传状态、解析状态和失败原因需要在聊天工作区中可见。

这是智能体聊天材料链路的新增运行时能力，旧系统没有对应实现，旧系统代码不适用。截图仅作为用户交互和问题证据，不能替代接口、存储、解析和模型上下文验收。

## 证据与根因

- 用户截图显示聊天框存在“案件文件”和附件入口，但发送材料后大模型仍按未读文件处理，无法理解 PDF 内容。
- 原有 `read_attachment` 缓存按临时文件路径、文件名、大小和修改时间缓存。来自签名 OSS 地址的材料每次在新的临时目录下载，路径必然变化，因此同一附件跨轮提问不能命中缓存。
- 原有上传响应只返回附件编号，没有返回实际解析状态；前端无法区分“已保存但未解析”“正文已解析”“扫描页已提取”和“解析失败”。
- 聊天请求虽然携带 `attachment_ids`，但模型上下文必须使用本轮真实解析的 `readings.content` 和文件名、页码信息，不能只把附件清单交给模型。

## 缓存、解析和上下文改动

- 解析缓存改为按用户作用域、附件 ID、原文件名、内容 SHA-256 和内容大小生成稳定键，临时 OSS 下载路径变化不会影响命中。
- 缓存只持久化成功的 `parsed` 或 `visual` 结果，包括正文、页数和扫描页图像；损坏缓存会被忽略并重新解析，解析失败不会伪造成功状态。
- `AttachmentReading` 和 `prepare_materials` 增加 `cache_hit`、`cache_status`、`content_sha256`、`content_size` 等可审计字段。
- `/api/v1/agent-tools/upload` 返回 `reading.status`、缓存状态、页数、正文字符数、图像数量和内容哈希，上传成功与材料可读性分开表达。
- `material_message` 将文件名、实际正文及安全提示注入模型上下文；模型只能依据真实解析内容回答，并受 PDF 页数和正文截取限制约束。
- 前端保留上传得到的附件 ID，在发送消息时继续提交选中的材料，并显示上传/读取状态；失败状态不会被渲染成“已读”或成功结果。

## 变更文件

- `apps/api-server/app/agent_attachment_reader.py`
- `apps/api-server/app/areas/personal_agent/materials.py`
- `apps/api-server/app/agent_mcp/router.py`
- `apps/admin-web/src/personal-agent-center.css`
- `apps/admin-web/src/personal-agent/AssistantWorkspaceTools.tsx`
- `apps/admin-web/src/personal-agent/ConversationMessage.tsx`
- `apps/admin-web/src/personal-agent/assistant-workspace-tools.css`
- `apps/admin-web/src/personal-agent/types.ts`
- `apps/admin-web/src/personal-agent/usePersonalWorkspace.ts`
- `apps/api-server/tests/regression/personal_agent_material_cache_contract_test.py`
- `apps/api-server/tests/regression/mcp_direct_upload_contract_test.py`

## 本地验证

在候选 worktree `/tmp/oa-material-final-20261018` 使用项目虚拟环境运行材料相关回归：

- 材料缓存回归：真实 PDF 首次解析、跨临时路径命中、损坏缓存重解析、正文上下文注入；3 passed；
- 附件 reader 既有回归：6 passed；
- MCP direct upload 回归：3 passed，包含真实 PDF multipart 上传和 reading 状态；
- 合计：**12 passed（4.45 秒）**；
- 两个测试文件 `py_compile` 通过，测试数据均在临时目录生成和清理。

## 发布状态

- 本轮只完成本地候选验证，尚未提交、推送或部署；未重启线上服务，未执行线上健康检查。
- 前端 typecheck/build 由主线程记录为 `37 passed`、typecheck/build 通过；本记录不把这些结果替代浏览器材料验收。
- 部署前仍需由主线程完成精确暂存、完整源码门禁和前端构建，并在部署后分别验收上传状态、PDF 正文注入、缓存命中及失败状态。
