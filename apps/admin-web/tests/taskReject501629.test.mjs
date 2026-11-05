// 501629（tgn 11-05）：我接受的任务“待处理”页签补“拒绝任务”，照老系统规则，由后端 can_reject 控制。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const read = (path) => fs.readFileSync(new URL(path, import.meta.url), "utf8");
const list = read("../src/tp/TaskList.tsx");
const page = read("../src/tp/TaskCenterPage.tsx");
const modals = read("../src/tp/TaskActionModals.tsx");

test("待处理页签单选、可拒绝时显示拒绝任务按钮", () => {
  assert.match(list, /canManageAcceptedTask && statusTab === "pending" && selectedRows\.length === 1 && selected\?\.can_reject && \(\s*roleActionAllowed\("task\.accept"\) && <Button danger onClick=\{\(\) => onRejectTask\(selected\)\}>拒绝任务<\/Button>/);
});

test("拒绝走拒绝弹窗，必须写拒绝理由", () => {
  assert.match(page, /onRejectTask=\{\(row\) => openDialog\(row, "reject"\)\}/);
  assert.match(modals, /dialog\?\.action === "reject" \? "拒绝理由" : "派发说明"/);
  assert.match(modals, /name="comment"\s*rules=\{\[\{ required: true \}\]\}/);
});
