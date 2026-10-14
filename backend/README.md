# 后端模块（Backend）

本目录是给学习和查看用的导航入口。真实后端源码仍位于：

`../apps/api-server`

## 从哪里开始

- `../apps/api-server/app/main.py`：FastAPI 应用入口
- `../apps/api-server/app/routing.py`：路由注册
- `../apps/api-server/app/areas/`：按业务域拆分的 API
- `../apps/api-server/app/core/`：权限、存储、任务和共享业务逻辑
- `../apps/api-server/app/models.py`：数据模型
- `../apps/api-server/tests/`：后端回归、结构和集成测试

## 推荐学习顺序

1. `app/main.py`：理解应用启动和中间件
2. `app/routing.py`：理解 API 如何分发到业务域
3. `app/core/dependencies.py`、`app/core/permissions.py`：理解登录和权限
4. `app/areas/`：选择一个业务域，从 router 到 service 追踪
5. `tests/`：用测试确认接口、权限和状态流转

请不要把源码复制到本目录；本地 API、Docker 和测试仍以 `apps/api-server` 为准。
