import test from "node:test";
import assert from "node:assert/strict";

import {
  buildLegacyCasePhaseTree,
  buildCaseOrdinarySearchPayload,
  createLatestRequestGuard,
  LEGACY_PHASE_CHILDREN,
  ordinaryCaseTypesForView,
  ordinaryCustomerIdForView,
  parseOrdinarySearchResult,
} from "./src/caseOrdinarySearchParity.mjs";

test("legacy civil phase catalog matches every target group exactly", () => {
  assert.deepEqual(LEGACY_PHASE_CHILDREN, {
    "一审阶段": [
      "一审立案受理", "一审补充证据", "一审准备开庭", "一审再次开庭", "一审庭后待判",
      "一审等待上诉", "一审待执行", "一审上诉准备", "一审补充代理意见", "一审和解中",
      "一审和解结案", "一审判决结案", "一审待客户回款",
    ],
    "二审阶段": [
      "二审立案受理", "二审补充证据", "二审通知开庭", "二审再次开庭", "二审庭后待判",
      "二审待执行", "二审补充代理意见", "二审和解中", "二审和解结案", "二审判决结案",
      "二审待客户回款",
    ],
    "再审阶段": [
      "再审立案受理", "再审补充证据", "再审通知开庭", "再审庭后待判", "再审待执行",
      "再审和解中", "再审和解结案", "再审判决结案", "再审待客户回款",
    ],
    "执行阶段": [
      "执行立案", "执行受理", "执行中止", "执行结案", "执行终本", "终结执行", "执行和解中",
    ],
    "归档阶段": [
      "归档审核", "已归档", "归档拒绝", "亏损内审", "亏损审核", "亏损归档", "亏损拒绝",
    ],
  });
});

test("civil routes include both legacy and current civil case labels", () => {
  assert.deepEqual(ordinaryCaseTypesForView("case-company-civil"), ["民事争议", "民事案件"]);
  assert.deepEqual(ordinaryCaseTypesForView("case-mine-criminal"), ["刑事案件"]);
  assert.deepEqual(ordinaryCaseTypesForView("case-dept-administrative"), ["行政案件及国家赔偿"]);
  assert.deepEqual(ordinaryCaseTypesForView("case-company-arbitration"), ["仲裁"]);
});

test("customer-scoped case routes preserve the stable customer id across remounts", () => {
  assert.equal(ordinaryCustomerIdForView("case-company-civil-customer-11119"), 11119);
  assert.equal(ordinaryCustomerIdForView("case-dept-civil-customer-42"), 42);
  assert.equal(ordinaryCustomerIdForView("case-company-civil"), 0);
});

test("buildLegacyCasePhaseTree follows the exact legacy civil hierarchy and aggregates groups", () => {
  const items = [
    { label: "审核公证书", value: "审核公证书", count: 0 },
    { label: "一审阶段", value: "一审阶段", count: 0 },
    { label: "二审阶段", value: "二审阶段", count: 0 },
    { label: "执行阶段", value: "执行阶段", count: 0 },
    { label: "归档阶段", value: "归档阶段", count: 0 },
  ];
  const tree = buildLegacyCasePhaseTree(items, [], {
    二审: 1,
    二审通知开庭: 2,
    等待审核公证书: 4,
    一审通知开庭: 1,
    一审待执行: 3,
    提交法院: 1,
    执行终结: 1,
    亏损内审: 1,
  });

  assert.equal(tree[0].count, 4);
  assert.ok(tree[1].children.some((child) => child.label === "一审补充代理意见"));
  assert.deepEqual(tree[1].children.map((child) => child.label), [
    "一审立案受理", "一审补充证据", "一审准备开庭", "一审再次开庭", "一审庭后待判",
    "一审等待上诉", "一审待执行", "一审上诉准备", "一审补充代理意见", "一审和解中",
    "一审和解结案", "一审判决结案", "一审待客户回款",
  ]);
  assert.equal(tree[2].count, 3);
  assert.ok(tree[2].children.some((child) => child.label === "二审通知开庭" && child.count === 2));
  assert.ok(!tree[2].children.some((child) => child.label === "二审准备开庭"));
  assert.ok(tree[1].children.some((child) => child.label === "一审待执行" && child.count === 3));
  assert.ok(tree[1].children.some((child) => child.label === "一审准备开庭" && child.count === 1));
  assert.deepEqual(tree[2].children.map((child) => child.label), [
    "二审立案受理", "二审补充证据", "二审通知开庭", "二审再次开庭", "二审庭后待判",
    "二审待执行", "二审补充代理意见", "二审和解中", "二审和解结案", "二审判决结案",
    "二审待客户回款",
  ]);
  assert.deepEqual(tree[3].children.map((child) => child.label), [
    "执行立案", "执行受理", "执行中止", "执行结案", "执行终本", "终结执行", "执行和解中",
  ]);
  assert.equal(tree[3].children.find((child) => child.label === "执行立案")?.count, 1);
  assert.equal(tree[3].children.find((child) => child.label === "终结执行")?.count, 1);
  assert.deepEqual(tree[4].children.map((child) => child.label), [
    "归档审核", "已归档", "归档拒绝", "亏损内审", "亏损审核", "亏损归档", "亏损拒绝",
  ]);
  assert.equal(tree[4].count, 1);
});

test("buildCaseOrdinarySearchPayload maps ordinary filters to the server contract", () => {
  const formatted = { format: (pattern) => (pattern === "YYYY-MM-DD" ? "2026-08-03" : "unexpected") };
  assert.deepEqual(
    buildCaseOrdinarySearchPayload(
      {
        customer: "  客户甲  ",
        serial_no: " ORD-001 ",
        keyword: "  案由  ",
        status: "  进行中 ",
        handling_lawyer: " 律师甲 ",
        assistant: " 助理甲 ",
        document_name: " 文书.pdf ",
        counsel_range: [formatted, null],
        advanced_logic: "union",
        finance_bill_statuses: [" 未开票 ", ""],
        file_type_ids: [" F1 ", "F2"],
      },
      "department",
      [" 民事案件 "],
      3,
      15,
    ),
    {
      scope: "department",
      case_types: ["民事案件"],
      customer_id: null,
      customer_no: "",
      customer: "客户甲",
      serial_no: "ORD-001",
      keyword: "案由",
      counsel_start: "2026-08-03",
      counsel_end: null,
      counsel_type: "",
      case_status: "进行中",
      case_statuses: [],
      handling_lawyer: "律师甲",
      assistant: "助理甲",
      document_name: "文书.pdf",
      plaintiff: "",
      prosecutor: "",
      defendant: "",
      evidence_org: "",
      notary_no: "",
      hearing_lawyer: "",
      investigator: "",
      court: "",
      source_from: null,
      source_to: null,
      channel: "",
      warehouse: "",
      hearing_from: null,
      hearing_to: null,
      area: "",
      location: "",
      log_content: "",
      sort_order: "updated_desc",
      page: 3,
      page_size: 15,
      advanced_logic: "or",
      assisted_response_user: "",
      assisted_response_user_not: false,
      assisted_request_date_from: null,
      assisted_request_date_to: null,
      assisted_request_date_not: false,
      assisted_response_date_from: null,
      assisted_response_date_to: null,
      assisted_response_date_not: false,
      finance_inform_date_from: null,
      finance_inform_date_to: null,
      finance_inform_date_not: false,
      finance_gained_date_from: null,
      finance_gained_date_to: null,
      finance_gained_date_not: false,
      finance_response_user: "",
      finance_response_user_not: false,
      finance_bill_no: "",
      finance_bill_no_not: false,
      finance_bill_statuses: ["未开票"],
      finance_bill_status_not: false,
      finance_bill_date_from: null,
      finance_bill_date_to: null,
      finance_bill_date_not: false,
      finance_fee_type_ids: [],
      finance_fee_type_not: false,
      file_uploading_user: "",
      file_uploading_user_not: false,
      file_uploading_time_from: null,
      file_uploading_time_to: null,
      file_uploading_time_not: false,
      file_type_ids: ["F1", "F2"],
      file_type_not: false,
    },
  );
});

test("buildCaseOrdinarySearchPayload applies safe scope, sort, paging, and date defaults", () => {
  const payload = buildCaseOrdinarySearchPayload(
    { sort_order: "unknown", source_range: ["2026-08-03", "2026-08-04"] },
    "all-users",
    [],
    0,
    999,
  );

  assert.equal(payload.scope, "company");
  assert.deepEqual(payload.case_types, []);
  assert.equal(payload.sort_order, "updated_desc");
  assert.equal(payload.page, 1);
  assert.equal(payload.page_size, 200);
  assert.equal(payload.counsel_start, null);
  assert.equal(payload.counsel_end, null);
  assert.deepEqual(payload.case_statuses, []);
});

test("phase group filter submits all exact legacy descendants", async () => {
  const { legacyCasePhaseFilterValues } = await import("./src/caseOrdinarySearchParity.mjs");
  const first = legacyCasePhaseFilterValues("一审阶段");
  assert.ok(first.includes("一审"));
  assert.ok(first.includes("一审补充代理意见"));
  assert.ok(first.includes("一审待执行"));
  assert.deepEqual(legacyCasePhaseFilterValues("一审待执行"), ["一审待执行"]);
  assert.deepEqual(legacyCasePhaseFilterValues("审核公证书"), ["审核公证书", "等待审核公证书"]);
  assert.deepEqual(legacyCasePhaseFilterValues("一审准备开庭"), ["一审准备开庭", "一审通知开庭"]);
  assert.deepEqual(legacyCasePhaseFilterValues("执行立案"), ["执行立案", "提交法院"]);
  assert.deepEqual(legacyCasePhaseFilterValues("终结执行"), ["终结执行", "执行终结"]);
});

test("普通案件服务端搜索默认使用旧分页 15 条", () => {
  assert.equal(buildCaseOrdinarySearchPayload({}, "company", [], 1).page_size, 15);
  assert.equal(buildCaseOrdinarySearchPayload({}, "company", [], 1, undefined).page_size, 15);
});

test("普通案件响应保留分页前 phase_counts，并对缺失或非法统计清零", () => {
  assert.deepEqual(
    parseOrdinarySearchResult(
      {
        items: [{ id: 1 }],
        total: 17,
        page: 2,
        page_size: 15,
        phase_counts: { "新案待分配": 12, "执行阶段": 5 },
      },
      1,
      15,
    ),
    {
      items: [{ id: 1 }],
      total: 17,
      page: 2,
      pageSize: 15,
      phaseCounts: { "新案待分配": 12, "执行阶段": 5 },
    },
  );
  assert.deepEqual(parseOrdinarySearchResult({ phase_counts: { bad: -1, text: "no" } }, 1, 15), {
    items: [],
    total: 0,
    page: 1,
    pageSize: 15,
    phaseCounts: {},
  });
});

test("buildCaseOrdinarySearchPayload preserves every visible ordinary query field", () => {
  const sourceStart = { format: () => "2026-01-02" };
  const sourceEnd = { format: () => "2026-01-31" };
  const hearingStart = { format: () => "2026-02-02" };
  const hearingEnd = { format: () => "2026-02-28" };
  const payload = buildCaseOrdinarySearchPayload({
    plaintiff: " plaintiff ",
    prosecutor: " prosecutor ",
    defendant: " defendant ",
    evidence_org: " evidence-org ",
    notary_no: " notary-001 ",
    hearing_lawyer: " hearing-lawyer ",
    investigator: " investigator ",
    court: " court ",
    source_range: [sourceStart, sourceEnd],
    channel: " channel ",
    warehouse: " warehouse ",
    hearing_range: [hearingStart, hearingEnd],
    area: " area ",
    location: " location ",
    log_content: " log-content ",
  });

  assert.equal(payload.plaintiff, "plaintiff");
  assert.equal(payload.prosecutor, "prosecutor");
  assert.equal(payload.defendant, "defendant");
  assert.equal(payload.evidence_org, "evidence-org");
  assert.equal(payload.notary_no, "notary-001");
  assert.equal(payload.hearing_lawyer, "hearing-lawyer");
  assert.equal(payload.investigator, "investigator");
  assert.equal(payload.court, "court");
  assert.equal(payload.source_from, "2026-01-02");
  assert.equal(payload.source_to, "2026-01-31");
  assert.equal(payload.channel, "channel");
  assert.equal(payload.warehouse, "warehouse");
  assert.equal(payload.hearing_from, "2026-02-02");
  assert.equal(payload.hearing_to, "2026-02-28");
  assert.equal(payload.area, "area");
  assert.equal(payload.location, "location");
  assert.equal(payload.log_content, "log-content");
});

test("latest ordinary search request guard rejects stale responses", () => {
  const guard = createLatestRequestGuard();
  const firstRequest = guard.begin();
  const secondRequest = guard.begin();

  assert.equal(guard.isLatest(firstRequest), false);
  assert.equal(guard.isLatest(secondRequest), true);
});
