# 技能网站选择下载前端返工定位

## 1. 清单原文
- 独立问题，无Excel行。
- 用户原文：你去对应的技能网站啊 让用户可以选择技能下载啊
- 当前状态：本地实施与定向核验通过，待统一构建、发布与用户页面验收。

## 2. 截图分析
- 唯一截图：codex-clipboard-a45bbc85-269d-4ad1-929e-2e47b08f22c8.png。
- 新系统技能弹窗顶部仅有GitHub链接输入、预览按钮；下方自定义技能为空并展示手工新增名称、分类、说明、指令、快捷指令。缺少可直接浏览并选择的技能网站目录。
- 没有旧系统对照图；当前附件已单图读取并完成定位后实施。

## 3. 旧系统实现
不适用：新增网站目录能力，以用户原文和现有技能导入架构实现。

## 4. 新系统当前实现
### 前端
`SkillManager.tsx`原来直接展示GitHub URL导入和手工表单；没有网站目录、来源选择和搜索。原`/agent/skills/github/preview`完整预览和`/github/install`哈希确认路径保留复用。
### 后端
由B线程独占：新增`GET /agent/skills/catalog?source&q`和`POST /agent/skills/catalog/preview`。列表项目ID是服务端opaque标识，前端不猜测SKILL路径；preview请求携带列表source/id/query，返回稳定GitHub来源URL、实际读取resolved_commit和SHA256后再安装。安装仍重新读取核对SHA；不因无关仓库提交变化新增来源副本。
### 数据库
前端不改表和迁移；安装仍使用现有个人技能持久化与账号权限范围。未创建业务数据。

## 5. 需求与当前实现差距
| 用户要求 | 原有差距 | 实际改动 |
|---|---|---|
| 去对应技能网站、用户选择下载 | 只有手工粘贴URL，没有目录 | 默认技能市场展示Skills.sh真实目录，切换OpenAI/Anthropic官方，搜索与来源详情链接 |
| 用户选择下载 | 输入链接才预览 | 卡片选择请求真实完整SKILL正文；用户确认才发送install，取消不写入 |
| 保留原有导入管理 | 市场可能替代旧入口 | 我的技能、GitHub链接、手工新增保留为次级Tab，上传/启停/删除/编辑/使用完整保留 |

## 6. 精确修改清单
- [x] `SkillCatalog.tsx`：真实来源选择、搜索、加载/错误/重试/空目录、卡片选择、完整正文预览、取消与SHA确认安装。源码网站未提供description时明确提示，不编造翻译和安装量。
- [x] `SkillManager.tsx`：默认市场、三个次级Tab；安装成功刷新个人库并选用，停用技能不自动改变当前选择；手工与URL预览统一64000指令字符限制、8000说明字符限制，说明采用TextArea，不静默截断。
- [x] `workspace-context.css`：桌面双列，760px以下单列；来源/搜索/长文本换行，控件44px，modal正文滚动与底部安全区。
- [x] 既有`tests/architecture/caseAgentWorkspaceRuntime.test.mjs`：隔离React真实事件测试，不增加独立测试脚本。
- 不涉及其他已发布手机聊天/首页UI，不修改主工作树。后端范围见B报告。

## 7. 验证清单
- `npm ci --no-audit --no-fund`成功，224依赖，package/lock未改变。
- `npm run typecheck` exit 0。
- `node --test --test-name-pattern='skill market browses|GitHub URL install' tests/architecture/caseAgentWorkspaceRuntime.test.mjs`：pass2/fail0。覆盖目录真实响应消费、输入不自动搜索、提交q、source/id/q预览、>6000正文和>500说明完整、取消零install、确认SHA安装、unsupported错误、目录失败及重试空结果；市场与URL安装均测试持久化成功后refresh失败准确提示，零误选、隐藏重装按钮，重试仅刷新不重复install。仅React/API mock，不业务写测试。
- `git diff --check`通过；`codegraph sync` exit127：CLI不可用，使用rg源码定位。
- 手机源码约束：320/375/390/414宽度均命中760以下单列、最大viewport-24px；768及桌面双列。minmax(0,1fr)和min-width:0避免长内容撑宽；全部卡片按钮、来源链接44px；正文pre不截断，独立滚动。实际构建CSS核验交PM统一构建，未浏览器/真机验收。
- 无API业务写入、无测试库和业务数据、无浏览器标签。无Git暂存、提交、版本或部署。

## 8. 实施记录
- 唯一工作树：`/tmp/oa-skill-market-20261014-GgSORV/source`，基线1.1.370。
- 源码只读追踪与契约已对齐B；前端4精确文件及本文档供PM纳入冻结候选。
- PM补证：市场与GitHub链接安装的持久化响应和刷新失败分开处理；已安装但刷新失败时保留明确警告及“刷新个人技能”按钮，无重复写入，不选中未载入技能。B实际description835字符串前后校验同步8000；q输入maxLength100与GET/POST schema及catalog函数100一致。
- 发布与正式版本由PM统一编排。当前未发布、待用户验收；不宣称网站下载已完成生产业务验收。
