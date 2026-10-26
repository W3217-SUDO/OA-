---
name: find-skills（OA 版）
description: 帮用户在开放技能目录（skills.sh）里查找可安装的智能体技能，给出名称、来源、安装量和 OA 可导入的 GitHub 链接。用户问“有没有能做 X 的技能”“帮我找个做 X 的技能”、想扩展智能体能力，或某类专门任务可能已有现成技能时使用。
---

# 查找技能（OA 版）

本技能改编自 vercel-labs/skills 的 find-skills。原版要运行 `npx skills`，OA 的技能容器不能运行 npx，所以改成用本技能包里的脚本 `scripts/find.mjs` 直接查询 skills.sh 和 GitHub。**不要尝试运行 `npx skills find` 或 `npx skills add`。**

## 什么时候用

- 用户问“有没有能做 X 的技能”“帮我找个 X 的技能”“你能不能做 X”（X 是比较专门的能力）。
- 用户想扩展智能体能力，或想找某个领域（设计、文档处理、测试、部署等）的现成工作流。

## 第 1 步：弄清需求

先确定领域（如 PDF、Word、前端设计）和具体任务（如合并 PDF、写周报），把它们换成 1～3 个英文关键词：skills.sh 上的技能大多是英文名，例如“处理 PDF”→ `pdf`，“写更新日志”→ `changelog`。

## 第 2 步：搜索

调用 `harness_run_skill_script`：`name` 填本技能名称，`path` 填 `scripts/find.mjs`，`args` 例如：

- `["search", "pdf"]`
- `["search", "react", "performance", "--limit", "15"]`
- `["search", "review", "--owner", "anthropics"]`（只看某个 GitHub 用户或组织的技能）

脚本输出 JSON：`skills` 按安装量从高到低，每项有 `name`、`source`（GitHub 的 owner/repo）、`skillId`、`installs`、`page`（skills.sh 介绍页）。

## 第 3 步：判断质量

不要只凭搜索结果就推荐：

1. 安装量：优先 1K 以上，低于 100 的要谨慎。
2. 来源：官方来源（anthropics、vercel-labs、microsoft 等）比不知名作者可靠。
3. 对准备推荐的 1～3 个技能，再调用一次脚本取安装信息：`["link", "<source>", "<skillId>"]`，例如 `["link", "anthropics/skills", "pdf"]`。返回 `stars`（GitHub 星标，少于 100 要谨慎）、`archived`（已归档的不推荐）、`import_url`、`oa_compatibility`。
4. 看 `oa_compatibility`：写着“需要 npx/pip 等命令行工具……不建议安装”的，要明确告诉用户装到 OA 里用不了。

## 第 4 步：告诉用户

对每个推荐的技能说明：名称和用途、安装量和来源、在 OA 里能不能用（`oa_compatibility`）、skills.sh 介绍页（`page`）。安装方式写清楚：

1. 先到「智能体设置 → 能力市场」搜同名技能，市场里有的直接安装。
2. 市场里没有的：管理员在「智能体设置 → 全局 Skill → 新增或导入」选 GitHub 链接，粘贴 `import_url`，预览确认后安装；只给自己用的，在个人技能里同样用 GitHub 链接导入。

`import_url` 固定到当前提交，安装的内容和预览一致。

## 没找到时

说明没有找到合适的技能，然后直接用现有能力帮用户完成任务；如果这类任务经常要做，可以建议管理员在「全局 Skill」里自建技能。

## 出错时

脚本返回 `"ok": false` 时如实告诉用户原因（例如网络超时、GitHub 查询额度暂时用完），不要编造搜索结果。
