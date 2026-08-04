import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const source = await readFile(
  fileURLToPath(new URL("./src/OrganizationCenterPage.tsx", import.meta.url)),
  "utf8",
);

function block(startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle);
  assert.notEqual(start, -1, "missing source anchor: " + startNeedle);
  const end = endNeedle ? source.indexOf(endNeedle, start) : source.length;
  assert.notEqual(end, -1, "missing source end anchor: " + endNeedle);
  return source.slice(start, end);
}

const openRolePermissions = block("const openRolePermissions =", "const saveRolePermissions =");
const saveRolePermissions = block("const saveRolePermissions =", "const departmentColumns:");
const rolePermissionModal = block("className=\"legacy-role-permission-tree\"", "</div>");

test("role permission tree preserves legacy menu-node selections from the API", () => {
  assert.ok(
    source.includes("rolePermissionsToTreeCheckedKeys"),
    "role permissions should normalize legacy menu resource codes into tree checked keys",
  );
  assert.ok(
    openRolePermissions.includes("rolePermissionsToTreeCheckedKeys(row.permissions || [], permissionTreeData)"),
    "row fallback permissions should keep menu nodes visible before remote tree loads",
  );
  assert.ok(
    openRolePermissions.includes("rolePermissionsToTreeCheckedKeys(data.permissions || row.permissions || [], nextRolePermissionTreeData)"),
    "remote permissions should be mapped against the returned menu tree",
  );
});

test("role permission save round-trips menu nodes instead of silently dropping them", () => {
  assert.ok(
    saveRolePermissions.includes("permissions: rolePermissionTreeKeysToPayload(selectedRolePermissions)"),
    "save payload should convert checked menu tree keys back to legacy resource codes",
  );
  assert.ok(
    rolePermissionModal.includes("normalizeRolePermissionCheckedKeys"),
    "Tree onCheck should use the shared checked-key normalizer",
  );
  assert.ok(
    !rolePermissionModal.includes("!key.startsWith(\"menu:\")"),
    "Tree onCheck must not discard checked menu nodes",
  );
});
