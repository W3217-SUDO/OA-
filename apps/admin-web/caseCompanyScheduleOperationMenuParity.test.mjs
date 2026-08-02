import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const source = fs.readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("公司案件开庭排期详情使用旧站九项操作菜单且隔离其他来源路由", () => {
  const labelsMatch = source.match(
    /export const getCompanyScheduleDetailOperationLabels = \(\) => (\[[\s\S]*?\]);/,
  );
  assert.ok(labelsMatch, "公司排期详情应声明独立的旧站操作菜单");
  const getCompanyScheduleDetailOperationLabels = new Function(
    `return (${labelsMatch[1]});`,
  );

  assert.deepEqual(getCompanyScheduleDetailOperationLabels(), [
    "修改基本信息",
    "修改案件阶段",
    "修改公证信息",
    "修改开庭律师",
    "修改当事人",
    "修改法院信息",
    "修改诉讼或判决金额",
    "申请归档",
    "更多操作",
  ]);

  const routeMatch = source.match(
    /export const shouldUseCompanyScheduleDetailOperationMenu = \(initialView: string, sourceRoute\?: string\) => ([^;]+);/,
  );
  assert.ok(routeMatch, "公司排期操作菜单应继续使用精确来源路由判断");
  const shouldUseCompanyScheduleDetailOperationMenu = new Function(
    "initialView",
    "sourceRoute",
    `return (${routeMatch[1]});`,
  );
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu("case-company-schedule"), true);
  assert.equal(
    shouldUseCompanyScheduleDetailOperationMenu(
      "case-detail-5-SH191000382B",
      "case-company-schedule",
    ),
    true,
  );
  assert.equal(
    shouldUseCompanyScheduleDetailOperationMenu(
      "case-detail-5-SH191000382B",
      "case-company-civil",
    ),
    false,
  );
  assert.equal(shouldUseCompanyScheduleDetailOperationMenu("case-schedule"), false);

  assert.match(
    source,
    /shouldUseCompanyScheduleDetailOperationMenu\(initialView,caseListReturnContext\?\.route\)\?<Dropdown[\s\S]*?\{companyScheduleDetailActionButtons\}[\s\S]*?<\/Dropdown>:caseDetailActionButtons/,
  );
});
