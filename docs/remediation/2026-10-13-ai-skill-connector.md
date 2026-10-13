# AI 助手技能连接器独立新增需求

## 1. 清单原文
原始问题（逐字）：这个ai助手要做一个技能的连接器 跟codex一样仿照

补充说明（逐字）：然后技能可以去github上下载

当前状态：本地实施，待用户页面验收；不是 Excel 批次。

## 2. 截图分析
图 1：`/var/folders/lm/3mbkryqx3_d766wf4fpc708r0000gn/T/codex-clipboard-ea27db33-9ba0-4908-a8f9-e8b6cd85c06f.png` 已单张查看。
可读副本：`/tmp/oa-ai-skill-connector-20261013/evidence/user-screenshot.png`；SHA256 `6b10061192aee854e5308c7c385119968c6d55844023e4a5986da1cf1ba0adaf`。截图只在树外保留，不进入 GitHub 或运行包。
画面为 AI 助手新对话；底部有「通用办公」选择器、快速/深度、关联案件、上传和无文字烧杯按钮。无 GitHub 安装入口；截图未展示管理弹窗。需求是在现有技能能力上增加清晰管理和 GitHub 安装，不能从截图推断外部代码执行能力。

## 3. 旧系统实现
不适用：新增需求，旧系统不存在。不查询旧站。

## 4. 新系统当前实现
前端 `personal-agent/AssistantWorkspaceTools.tsx` 已有技能选择器，烧杯按钮打开 `SkillManager.tsx`。管理已有新增、编辑、文件上传、启停、删除，但无 GitHub 来源预览或安装。
后端既有 `/agent/skills` 持久化用户自定义技能；新增 GitHub preview/install 由 B 独占实现。数据库不新增表，来源 metadata 由后端保存并返回。
CodeGraph CLI 不存在，使用直接文件读取补充，未把代码图谱作为验收证据。

## 5. 需求与当前实现差距
「技能连接器」对应明确「技能」按钮、管理/选择/启停；「github上下载」对应 URL 输入、完整指令预览、确认安装及可追溯来源。保留已有技能选择、上传、编辑能力。

## 6. 精确修改清单
- [x] `AssistantWorkspaceTools.tsx`：管理按钮显示技能文字，保留个人 AI 空间手机入口。
- [x] `SkillManager.tsx`：GitHub URL 预览、错误、指令与来源展示、确认安装、刷新后选中；已装技能可显式选择。
- [x] `types.ts`：可选来源与内容 hash。
- [x] `workspace-context.css` / `assistant-workspace-tools.css`：长文本、窄屏 44px 操作、弹窗单列布局。
不涉及 OA 业务审批或数据关系。外部技能内容作为用户技能指令，页面不执行外部脚本。

## 7. 验证清单
既有 frontend unit、TypeScript/生产构建由 PM 汇总；核对 320/375/390/414/768 与桌面构建 CSS 生效链，待用户实际页面与手机验收。GitHub 预览/安装成功、hash 变化阻断、用户隔离由后端验证，前端仅以真实 API 成功返回提示。
未创建业务测试数据、未打开或控制浏览器。

## 8. 实施记录
本地 dev，未提交、推送、部署或改版本。其他已有改动保留。
工作基线由 PM 从旧 dev 安全快进至 `16882118` / `1.1.368` 后恢复，个人 AI 空间能力保留。
`npm run typecheck` 已通过；`git diff --check` 已通过。无现有技能专项单元测试文件，未新增重复实现测试。
手机宽度 320/375/390/414 命中 760px 管理弹窗规则（链接行单列、名称/指令/来源换行、44px操作）；768 命中 991px 工具弹层（技能整行），管理弹窗宽度受 Ant Modal 视口最大宽度约束。桌面继续760px弹窗、两列编辑字段。全宽按钮、pre局部滚动和现有Modal页面滚动允许访问全部指令。最终生产产物规则仍待 PM 构建后核对，未声称实际手机或浏览器通过。
