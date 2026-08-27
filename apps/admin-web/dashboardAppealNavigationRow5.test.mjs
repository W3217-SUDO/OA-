import test from "node:test";
import assert from "node:assert/strict";

import {
  buildCaseOrdinarySearchPayload,
  dashboardCaseQueryForView,
} from "./src/caseOrdinarySearchParity.mjs";

test("dashboard appeal route opens the personal exact-phase case query", () => {
  assert.deepEqual(dashboardCaseQueryForView("case-mine-appeal"), {
    status: "一审等待上诉",
    case_statuses: ["一审等待上诉", "待上诉"],
    sort_order: "updated_desc",
  });
  assert.deepEqual(dashboardCaseQueryForView("case-company"), {});

  assert.deepEqual(
    buildCaseOrdinarySearchPayload(
      dashboardCaseQueryForView("case-mine-appeal"),
      "mine",
      [],
      1,
      15,
    ),
    {
      ...buildCaseOrdinarySearchPayload({}, "mine", [], 1, 15),
      case_status: "一审等待上诉",
      case_statuses: ["一审等待上诉", "待上诉"],
    },
  );
});
