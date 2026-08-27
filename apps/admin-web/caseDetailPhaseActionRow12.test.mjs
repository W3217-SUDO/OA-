import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  source,
  /getLegacyCaseDetailPrimaryOperationLabels\s*=\s*\(\)\s*=>\s*\[\s*"修改基本信息",\s*"修改案件阶段",/s,
  "案件详情操作菜单应在修改基本信息后显示修改案件阶段",
);
assert.match(
  source,
  /counselDetailCapabilities\.can_change_phase[\s\S]*?openPhaseChange\(\[viewingCounselCase\]\)[\s\S]*?primaryOperationLabels\[1\]/,
  "修改案件阶段入口必须由服务端能力控制并打开真实阶段变更流程",
);
assert.match(
  source,
  /buildLegacyCasePhaseTree\(\s*CASE_PHASE_ROOT_LABELS\.map/,
  "阶段修改弹窗必须复用案件列表的阶段根节点定义",
);
assert.match(
  source,
  /api\.get\("\/cases\/phases"[\s\S]*?api\.post\("\/cases\/phase-change"/,
  "阶段弹窗必须读取服务端阶段并调用专用持久化接口",
);
assert.match(
  source,
  /currentDetailChanged[\s\S]*?await openCounselDetail\(updatedDetail\)[\s\S]*?await load\(\)/,
  "详情页阶段保存后必须直接回读当前案件并同步刷新列表",
);

console.log("CASE_DETAIL_PHASE_ACTION_ROW12_OK");
