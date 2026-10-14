# 前端模块（Frontend）

本目录是给学习和查看用的导航入口。真实前端源码仍位于：

`../apps/admin-web`

## 从哪里开始

- `../apps/admin-web/src/App.tsx`：路由、菜单和应用外壳
- `../apps/admin-web/src/`：React + TypeScript 页面、组件、请求封装和样式
- `../apps/admin-web/package.json`：前端脚本和依赖
- `../apps/admin-web/tests/`：前端架构与行为测试

## 推荐学习顺序

1. `src/App.tsx`：理解页面如何进入系统
2. `src/api/`：理解前端如何调用后端 API
3. `src/*CenterPage.tsx`：按业务模块阅读页面
4. `src/personal-agent/`：阅读 AI 对话、文件空间和技能入口
5. `tests/architecture/`：用测试理解不可破坏的前端约束

请不要把源码复制到本目录；构建、开发服务器和测试仍以 `apps/admin-web` 为准。
