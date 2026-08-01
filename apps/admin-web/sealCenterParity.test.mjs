import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal center exposes all required views and safety gates", () => {
  const source = fs.readFileSync(new URL("./src/SealCenterPage.tsx", import.meta.url), "utf8");
  for (const route of ["seal-my-pending", "seal-my-stamping", "seal-my-used", "seal-my-refused", "seal-my-withdrawn", "seal-audit-pending", "seal-admin-pending"]) {
    assert.match(source, new RegExp(route.replace(/[.*+?^${}()|[\\]\\]/g, "\\$&")));
  }
  for (const label of ["保存草稿", "取消", "上传用印文件", "下载", "删除用印草稿"]) assert.match(source, new RegExp(label));
  assert.match(source, /未上传文件不能提交审批/);
  for (const status of ["待审批", "待用印", "已拒绝", "已撤回"]) assert.match(source, new RegExp(status));
});
