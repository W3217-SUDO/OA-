import assert from "node:assert/strict";
import { shouldApplyCaseClueResponse } from "./src/caseClueRelationsRequestGuard.mjs";

assert.equal(
  shouldApplyCaseClueResponse({ requestId: 4, currentRequestId: 4, currentCaseId: 81, targetCaseId: 81 }),
  true,
  "the active request for the active case must update the list",
);
assert.equal(
  shouldApplyCaseClueResponse({ requestId: 3, currentRequestId: 4, currentCaseId: 81, targetCaseId: 81 }),
  false,
  "a late search or page response must not overwrite a newer result",
);
assert.equal(
  shouldApplyCaseClueResponse({ requestId: 4, currentRequestId: 4, currentCaseId: 82, targetCaseId: 81 }),
  false,
  "a response from the previous case must not populate the newly opened case",
);

console.log("case clue relations request guard: PASS");
