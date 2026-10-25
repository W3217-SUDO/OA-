# 沪知 OA 移动端（原生 App）

React Native + Expo 写的一套代码，同时出安卓和 iOS 包。App 直接调用线上同一套后端接口（`/api/v1`），和网页端共用数据，不嵌网页。

第一版范围按 2026-10-10 ～ 10-24 生产 Nginx 日志里的手机端实际使用情况确定：智能体对话、案件查看、我的任务。

## 功能

| 模块 | 内容 | 用到的接口 |
| --- | --- | --- |
| 登录 | 账号密码登录、首次登录改密；token 存 iOS 钥匙串 / 安卓 Keystore，过期或被停用（401）自动回到登录页 | `POST /auth/login`、`GET/PATCH /auth/me` |
| 智能体 | 对话列表、新建对话、流式回答、停止生成、待确认操作的确认/取消 | `/personal-agent/conversations*`、`POST /personal-agent/messages`（SSE）、`/personal-agent/actions/{id}/decision` |
| 案件 | 我的 / 部门 / 全所案件搜索；详情（案件信息、各审级法院、进展日志、案件任务） | `POST /cases/search`、`GET /records/{id}`、`/cases/{id}/logs`、`/cases/{id}/tasks`、`/cases/reference-options` |
| 我的任务 | 待处理 / 进行中 / 我发起的 / 我协作的 / 未读消息 / 已完成；详情里接受、提交完成、验收、文字反馈，打开即标记已读 | `GET /tasks`、`/tasks/unread-messages`、`/tasks/{id}/history`、`/tasks/{id}/{accept,complete,confirm}`、`/tasks/{id}/feedback`、`/tasks/{id}/messages/read` |

字段取值和按钮显示规则沿用网页端同名代码（文件内注释写明了出处），最终权限以后端校验为准。

## 目录

```text
src/app/          页面（Expo Router，文件即路由）
  (tabs)/         底部四个标签：agent / cases / tasks / me
  case/[id].tsx   案件详情
  task/[id].tsx   任务详情
  login.tsx
src/lib/          接口、登录状态、类型、业务规则
src/components/   通用界面组件、Markdown 渲染
scripts/build-apk.sh  本机打安卓正式包
```

`android/`、`ios/` 由 `expo prebuild` 生成，不进仓库，也不要手改；原生配置写在 `app.config.ts`。

## 本地开发

需要 Node.js 22、JDK 21、Android SDK（platform 35、build-tools 35）。

```bash
cd apps/mobile
npm ci
npx tsc --noEmit && npx expo lint   # 提交前必须通过
```

## 打安卓包

```bash
bash scripts/build-apk.sh                                                   # 连生产，输出 dist/huzhi-oa-<版本>.apk
EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:8000/api/v1 bash scripts/build-apk.sh   # 连本机后端（模拟器），输出 -dev 包
```

- 发新版前先改 `package.json` 的 `version` 和 `app.config.ts` 里的 `android.versionCode`（每次 +1），否则手机上无法覆盖安装。
- 正式签名密钥在 `~/.huzhi-oa/`（`release.jks` + `keystore.properties`），不进仓库。**密钥丢了，已装 App 的用户就再也收不到覆盖升级**，必须另外备份两份。
- 证书 SHA-256：`28:9D:6A:F9:52:6D:EF:75:88:9F:36:D5:63:12:29:70:4B:6E:9F:E4:D2:2C:47:1E:2B:1A:6E:9B:0A:CE:DC:69`

## iOS

同一套代码。出包还需要：完整 Xcode、苹果开发者账号（每年 99 美元），然后 `npx expo prebuild -p ios` 后在 Xcode 里签名，走 TestFlight 分发。

## 验证记录（0.1.0，2026-10-24）

在安卓 15 模拟器上，连本机测试后端（SQLite 副本）逐项验证：登录、首次登录改密（旧密码失效）、退出登录、覆盖升级后保持登录；智能体流式消息（含后端报错时的提示）；任务列表各视图、接受、发起人验收、文字反馈、从“未读消息”打开后标记已读；案件我的/部门/全所搜索、详情三个分区、从任务跳转关联案件。App 显示结果与同一账号直接调接口的结果逐项一致。

正式包只做了连通性检查（不存在的账号登录，线上返回“账号或密码错误”），还没有用真实账号在真机上走流程。

与网页端保持一致、看起来像问题但不是问题的规则：
- 只有从“未读消息”打开任务才标记已读（网页端 `openCommunication` 同样如此）。
- `/auth/me` 对所有人返回 `role: admin`（后端界面权限投影），App 不用它判断权限。

## 已知限制 / 后续

- 模拟器桌面上图标外圈有一道金色包边（安装包里的图标是纯白底，需在华为等真机上确认实际效果）。

- 推送通知还没接（国内安卓要接厂商通道或聚合推送，iOS 走 APNs）；现在的提醒仍走钉钉工作通知。
- 任务反馈暂不支持附件；案件文书不能在 App 里预览。
- 需要外部凭证的智能体操作（MCP 类）只能在网页端确认。
- 纯血鸿蒙（HarmonyOS NEXT）不能装 APK，需要另打 .hap 包。
- 后端目前不读取 `X-OA-Client` 请求头；审计日志要区分 App 请求，需要后端补上。
