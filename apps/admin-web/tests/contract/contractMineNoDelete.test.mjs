// BUG20261028014（范文玲）：合同中心“我的合同”底部不放“删除合同”；公司合同、回收站的删除不变。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import ts from "typescript";

const source = fs.readFileSync(new URL("../../src/contract/ContractList.tsx", import.meta.url), "utf8");
const file = ts.createSourceFile("ContractList.tsx", source, ts.ScriptTarget.ES2022, true, ts.ScriptKind.TSX);

function deleteButtonBranches() {
  const found = [];
  const visit = (node) => {
    if (ts.isConditionalExpression(node) && /initialView === "contract-(company|mine)"/.test(node.condition.getText(file))) {
      found.push({ condition: node.condition.getText(file), whenTrue: node.whenTrue, whenFalse: node.whenFalse });
    }
    ts.forEachChild(node, visit);
  };
  visit(file);
  return found;
}

test("我的合同不显示删除合同，公司合同和回收站仍有", () => {
  const branches = deleteButtonBranches();
  const mine = branches.find((item) => item.condition === 'initialView === "contract-mine"' && item.whenFalse.getText(file).includes("onDeleteRecycled"));
  assert.ok(mine, "找不到我的合同/回收站的删除按钮分支");
  const mineTrue = ts.isParenthesizedExpression(mine.whenTrue) ? mine.whenTrue.expression : mine.whenTrue;
  assert.equal(mineTrue.kind, ts.SyntaxKind.NullKeyword);
  assert.match(mine.whenFalse.getText(file), /删除合同/);
  const company = branches.find((item) => item.condition === 'initialView === "contract-company"' && item.whenTrue.getText(file).includes("onDeleteCompany"));
  assert.ok(company, "公司合同的删除合同按钮还在");
  assert.match(company.whenTrue.getText(file), /删除合同/);
});
