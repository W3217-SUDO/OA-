import assert from "node:assert/strict";
import test from "node:test";
import {
  intersectInvestigationTaskScopes,
  investigationTaskPathAllowed,
  investigationTaskRegionOptions,
  investigationTaskScopeGroups,
} from "../../src/investigation/taskRegionScope.ts";

test("regional authorization keeps province-city selection and parent intersection", () => {
  const root = investigationTaskScopeGroups({
    authorization_scope_type: "R",
    authorization_regions: [["上海市", "市辖区"], ["江苏省", "南京市"]],
  });
  const parent = investigationTaskScopeGroups({
    authorization_scope_type: "R",
    authorization_regions: [["上海市", "市辖区"]],
  });
  const allowed = intersectInvestigationTaskScopes(root, parent);
  assert.deepEqual(allowed, [{ province: "上海市", cities: ["市辖区"] }]);
  assert.equal(investigationTaskPathAllowed(["上海市", "市辖区"], allowed, root), true);
  assert.equal(investigationTaskPathAllowed(["江苏省", "南京市"], allowed, root), false);
  assert.deepEqual(investigationTaskRegionOptions(allowed)[0].children.map((item) => item.value), ["市辖区"]);
});

test("nationwide authorization exposes the province-city catalog", () => {
  const groups = investigationTaskScopeGroups({ authorization_scope_type: "N", authorization_scope: "全国" });
  assert.ok(groups.some((group) => group.province === "上海市" && group.cities.includes("市辖区")));
  assert.ok(groups.some((group) => group.province === "江苏省" && group.cities.includes("南京市")));
});
