import test from "node:test";
import assert from "node:assert/strict";
import {
  intersectInvestigationTaskScopes,
  investigationTaskPathAllowed,
} from "../src/investigation/taskRegionScope.ts";

const allGroups = [
  { province: "江苏省", cities: ["南京市", "苏州市"] },
  { province: "上海市", cities: ["市辖区"] },
];

test("历史父任务的宽授权不能扩大当前根调查区域", () => {
  const root = [{ province: "江苏省", cities: ["南京市"] }];
  const allowed = intersectInvestigationTaskScopes(root, allGroups);
  assert.deepEqual(allowed, root);
  assert.equal(investigationTaskPathAllowed(["江苏省", "南京市"], allowed, allGroups), true);
  assert.equal(investigationTaskPathAllowed(["上海市", "市辖区"], allowed, allGroups), false);
  assert.equal(investigationTaskPathAllowed(["江苏省"], allowed, allGroups), false);
});

test("选择不同父任务后只保留根与父共同允许的路径", () => {
  const root = allGroups;
  const parent = [{ province: "江苏省", cities: ["苏州市"] }];
  const allowed = intersectInvestigationTaskScopes(root, parent);
  const selected = [["江苏省", "南京市"], ["江苏省", "苏州市"], ["上海市", "市辖区"]];
  assert.deepEqual(selected.filter((path) => investigationTaskPathAllowed(path, allowed, allGroups)), [
    ["江苏省", "苏州市"],
  ]);
});
