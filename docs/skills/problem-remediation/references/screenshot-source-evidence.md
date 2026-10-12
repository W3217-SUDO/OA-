# 截图清单与源码补证

图片清单保留原有字段，并记录`visual_identity`（实际查看到的页面、按钮、对象）。同一sheet/row/col可有多个不同图片；image_id必须唯一。同一图片重复登记、跨行混用、文件缺失或SHA256不符仍失败。不同工作表的相同行号分别校验。

当原表缺少一侧截图，可另存源码补证JSON数组，显式传给校验器。不得把源码伪装成截图或把已有截图复制到缺失侧。

```json
[
  {
    "sheet_id": "sheet-id",
    "row": 3,
    "evidence_type": "new",
    "mapping_status": "confirmed",
    "missing_screenshot_reason": "原表该行只提供旧系统目标截图",
    "filename": "/absolute/path/to/actual/source.py",
    "sha256": "实际文件的SHA256",
    "line_start": 10,
    "line_end": 30,
    "entry": "已核对的页面入口与函数/接口",
    "finding": "该行原问题对应的实际源码行为与差异，不能只写已查看",
    "reviewed_by": "实际核对任务或人员",
    "reviewed_at": "实际核对时间"
  }
]
```

`filename`可为相对补证JSON的路径；行号从1开始。校验器验证文件存在、SHA256、行号范围、行归属、角色和核对字段是否齐全；它不证明finding内容正确。执行任务仍需亲自读取对应源码并核对结论。源码变化后须重新核对与更新校验值。

```text
python scripts/validate-screenshot-manifest.py manifest.json --require-old-new --source-evidence source-evidence.json
```

`--require-rework`仍要求真实返工截图，不接受源码代替。没有补证文件时仍要求每行同时有old/new截图。已存在的未知角色或未确认归行不能被补证掩盖。保留以前失败日志，另存修正后的结果，以便追溯。
