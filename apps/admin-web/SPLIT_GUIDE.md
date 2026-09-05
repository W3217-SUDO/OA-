# 前端中心页拆分任务说明

## 通用拆分原则

1. **零功能变更**：纯架构重构，不改变任何业务逻辑和UI行为
2. **父组件保留状态**：所有 useState、Form 实例、API 调用函数都留在父组件
3. **子组件纯展示**：通过 props 接收状态和回调函数
4. **按 Tab 拆分**：详情页每个 Tab 一个子组件文件
5. **弹窗独立**：Modal/Drawer 内容作为独立组件
6. **hooks 提取（可选）**：数据加载逻辑可以提取为自定义 hook
7. **构建验证**：拆分完成后 `npm run build` 必须 0 errors

## 目录结构模板

```
src/{page}-center/
  index.ts                     # 桶导出
  {Page}.tsx                   # 主容器（保留状态）
  types.ts                     # 共享类型定义
  constants.ts                 # 共享常量
  {Xxx}List.tsx                # 列表组件
  {Xxx}CreateModal.tsx         # 新建弹窗
  {Xxx}Detail/
    index.tsx
    {Xxx}DetailHeader.tsx      # 详情头部
    {Xxx}Tab1Panel.tsx        # Tab面板
    {Xxx}Tab2Panel.tsx
    ...
  hooks/
    use{Xxx}List.ts
    use{Xxx}Detail.ts
```

## 步骤

1. 通读原文件，理解完整结构
2. 创建目录和基础文件
3. 逐个拆出子组件（从最简单的开始）
4. 每拆一个验证一次构建
5. 全部完成后做最终构建验证
6. 报告拆分结果

## 注意事项

- 不确定的代码先保留在主组件中，不要硬拆
- 保持原有代码风格和 import 顺序
- props 类型用 interface 定义
- 拆分后主文件应该减少 30%-60% 的行数
