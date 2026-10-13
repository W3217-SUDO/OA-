# 技能市场来源与生产传输核验

## 范围与授权

当前用户要求技能选择下载。本记录只读核验公开技能来源和正式运行环境，不执行第三方仓库脚本、不安装 Codex 技能、不写业务数据或服务器配置。后端与前端分别由明确所有者实施；当前核验者负责来源证据及发布准备。

## 真实市场和官方目录

- [skills.sh 网站](https://skills.sh/) 当前可用；站点条目跳转至 `www.skills.sh`，生产 HTTPX 请求 `https://www.skills.sh/anthropics/skills/pdf` 返回 200。
- [官方 skills CLI 查询实现](https://github.com/vercel-labs/skills/blob/main/src/find.ts) 当前公开使用 `GET https://skills.sh/api/search?q=<关键词>&limit=20`，可附 `owner`。实际本机及生产 HTTPX 请求 `q=pdf` 均返回 200，无需令牌。官方 `/docs/api` 的鉴权 v1 接口不是本次公开查询路径，不能混用。
- 实际返回结构为 `{skills:[...]}`。PDF 首项包含 `id=anthropics/skills/pdf`、`source=anthropics/skills`、`skillId=pdf`、`name=pdf`、`installs=209717`；第二项为 `openai/skills/pdf`，实际安装数仅为即时目录显示，不作为信任或完整安装证明。
- [OpenAI 官方目录](https://api.github.com/repos/openai/skills/contents/skills/.curated) 实际本机/生产均 200，条目 `type=dir`、`name`、`path`，根路径为 `skills/.curated`。
- [Anthropic 官方目录](https://api.github.com/repos/anthropics/skills/contents/skills) 实际本机/生产均 200，根路径为 `skills`，其中真实包含 `docx`、`pdf` 等目录。
- 目录返回只证明目录存在。不得根据市场 `name` 拼接固定 `skills/<name>/SKILL.md` 并宣称可安装；应从实际目录树定位并核验文件。实测猜测 OpenAI `skills/.curated/doc/SKILL.md` 返回 404，证明必须处理名称和目录差异。

## 文件传输与正文大小

2026-10-14 生产运行解释器、HTTPX、固定官方主机只读检查：

| 真实官方文件 | Contents API | 正文字符 / UTF-8字节 |
| --- | --- | --- |
| `anthropics/skills:skills/pdf/SKILL.md` | 200，file/base64 | 8035 / 8072 |
| `anthropics/skills:skills/docx/SKILL.md` | 200，file/base64 | 6868 / 6911 |
| `openai/skills:skills/.curated/pdf/SKILL.md` | 200，file/base64 | 2517 / 2517 |

两份 Anthropic 常用文档技能真实超过旧 6000 字符限制，必须完整支持新的有限上限，不能截断内容当作完整技能。下载只导入经过用户选择和确认的指令正文；若正文引用第三方运行脚本、模板或环境依赖，必须明确本次未安装这些运行依赖，不执行远端代码。

生产请求 `raw.githubusercontent.com` 的两份官方 PDF 文件均发生 `ConnectError: connection reset by peer`；同一服务器 GitHub Contents API 文件返回 200、`encoding=base64`、`type=file`、准确 `path` 和可解码正文。因此正式部署必须通过可达的固定 GitHub Contents API读取文件，或者明确传输失败；不能仅凭本机 raw 200 推断服务器可下载。

实际 370 既有 preview 已使用 Contents API 加 `Accept: application/vnd.github.raw+json`，不是 raw 域名。按这个真实协商格式另外在生产实测 PDF 和 DOCX，均返回 200，Content-Type 正确、正文以 `---` 开始，字符/字节与上表完全一致。该既有传输可继续保留；无需为本次市场接入额外改成 base64。默认 JSON 检查与实际 raw+json 协商检查均完成，不能混淆两种响应格式。

## 必须显式处理的限制

- skills.sh 搜索结果可能是非 GitHub 来源、非普通文件、不同目录布局、已删除或私有文件，必须保留真实来源并明确不支持/不可用；不得伪造目录或静默替换来源。
- API 速率限制、403/404、网络超时、文件类型/编码不符、正文超限均应给出真实失败；不能把失败当作空目录成功。
- URL、返回路径、文件编码、文件长度和导入前摘要均须由后端核验；市场条目元数据是非可信输入，安装数不能放宽这些约束。
- 网站导航与后端下载是不同路径：网站条目 308→www 后可打开；后端应限制远端目标并避免任意重定向。
- 当前仅完成真实来源和传输证据，不代表浏览器展示、选择、预览、确认下载的完整交互已验收。

## 发布准备状态

只读核验时实际运行版本为 `1.1.370`，源码 `f4a2a65c57b9abb8e77eb36971cf3aa88586c9c1`；GitHub `dev`、`main`、`v1.1.370` annotated 解引用相同。生产 `current` 指向 `/opt/sunhold-oa/runtime/enterprise/packages/1.1.370`；队列/ledger 已收口 released，无依据接管历史预留。有效服务为 `sunhold-oa-api`、`sunhold-oa-web`，均 active。

正式执行继续使用已校验的 tools `1.1.345` native/runtime_package 及当前 Python 3.12 环境；helper 和解释器 SHA 与上次 reviewed-input 协议一致。正式 mutex 当时无占用，仅是只读观察，尚未取得租约。本任务还未领取版本、推送、建标签、构包或激活。

业务冻结后由唯一发布所有者在 PM 发放时段中：重新读 baseline/queue/locks/refs，按现有工具取得真实独占时段；晚分配一个未占用版本并形成最终提交；准确 HEAD 正常 source hook 与本地构建、GitHub static 成功；严格验包、上传本任务 staging、封存、一次激活、健康及耐久回执、dev/main/tag 同步和精确清理。新版本不在准备阶段猜测。

现有自动化目录未发现匹配本次 OA 技能市场监督任务。Skill 明确静态准备不触发部署；正式部署未收口阶段须建立唯一五分钟监督并记录准确 ID，成功完整收尾后删同 ID，不能重复建立或口头声称已建立。

## 六项交接

1. 已完成：官方来源、公开搜索真实字段、目录路径、生产传输与正文上限证据。
2. 修改文件：仅本记录；业务文件由 B/C 所有者独占。
3. 核验：本机/生产 HTTPX GET 及 SSH 状态均为只读；失败 raw 传输明确保留，Contents API替代已实测。
4. 清理：无业务记录、附件、浏览器标签或临时运行服务；查询进程均已结束。
5. Git/构建/发布：未执行提交、推送、版本、build、server 写入；等待冻结候选和 PM 互斥时段。
6. 剩余：B/C 完整实现与聚焦检查、正式 source/构建/static、真实独占发布、用户页面验收；生产可达性风险已明确传给 B。
