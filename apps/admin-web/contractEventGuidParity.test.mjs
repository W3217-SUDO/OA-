import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import {
  buildContractEventsRequest,
  CONTRACT_EVENT_PAGE_SIZES,
  createContractEventRequestTracker,
  createContractEventSubmitGate,
  normalizeContractEventsResponse,
} from "./src/contractWorkflowPolicy.mjs";

const contractCenterSource = fs.readFileSync(new URL("./src/ContractCenterPage.tsx", import.meta.url), "utf8");

test("contract events expose the six server page sizes and cap requests at the backend maximum", () => {
  assert.deepEqual(CONTRACT_EVENT_PAGE_SIZES, [10, 15, 20, 50, 100, 200]);
  assert.equal(buildContractEventsRequest({ id: 1 }, { pageSize: 1000 }).params.page_size, 200);
  assert.equal(buildContractEventsRequest({ id: 1 }, { pageSize: 17 }).params.page_size, 15);
  assert.equal(normalizeContractEventsResponse({ page_size: 17 }).pageSize, 15);
  assert.equal(normalizeContractEventsResponse({ page_size: 300 }).pageSize, 200);
});

test("contract events prefer the GUID endpoint with trimmed server-side filters", () => {
  const request = buildContractEventsRequest(
    { id: 41, serial_no: "HT-041", data: { contract_guid: "guid-041" } },
    { page: 2, pageSize: 20, keyword: "  回款  " },
  );
  assert.deepEqual(request, {
    path: "/contracts/guid/guid-041/events",
    params: { page: 2, page_size: 20, keyword: "回款" },
  });
});

test("contract event creation uses the same GUID route and omits empty keywords", () => {
  const request = buildContractEventsRequest(
    { id: 9, serial_no: "HT-009", contract_guid: "guid-009" },
    { page: 1, pageSize: 15, keyword: "   " },
  );
  assert.equal(request.path, "/contracts/guid/guid-009/events");
  assert.deepEqual(request.params, { page: 1, page_size: 15 });
});

test("contract events fall back to the numeric endpoint only when no GUID exists", () => {
  const request = buildContractEventsRequest(
    { id: 12, serial_no: "HT-012", data: {} },
    { page: 1, pageSize: 15, keyword: "审批" },
  );
  assert.equal(request.path, "/contracts/12/events");
  assert.deepEqual(request.params, { page: 1, page_size: 15, keyword: "审批" });
});

test("contract event response keeps pagination and GUID metadata while normalizing rows", () => {
  const result = normalizeContractEventsResponse({
    items: [{ id: 3, content: "回款", operator: "admin", created_at: "2026-08-03" }],
    total: 31,
    page: 2,
    page_size: 20,
    contract_guid: "guid-041",
  });
  assert.deepEqual(result, {
    items: [{ id: 3, content: "回款", operator: "admin", created_at: "2026-08-03", contract_guid: "guid-041" }],
    total: 31,
    page: 2,
    pageSize: 20,
    contractGuid: "guid-041",
  });
});

test("contract event response does not invent pagination for an empty or malformed payload", () => {
  assert.deepEqual(normalizeContractEventsResponse(null), {
    items: [], total: 0, page: 1, pageSize: 15, contractGuid: "",
  });
});

test("contract event request tracking makes an older response stale after a newer request starts", () => {
  const tracker = createContractEventRequestTracker();
  const first = tracker.next();
  const second = tracker.next();
  assert.equal(tracker.isCurrent(first), false);
  assert.equal(tracker.isCurrent(second), true);
});

test("contract event submit gate rejects a synchronous second entry and releases in finally", () => {
  const gate = createContractEventSubmitGate();
  assert.equal(gate.tryEnter(), true);
  assert.equal(gate.tryEnter(), false);
  gate.leave();
  assert.equal(gate.tryEnter(), true);
});

test("contract event production wiring gates before validation, releases in finally, and locks the modal while saving", () => {
  assert.match(contractCenterSource, /if \(!eventTarget \|\| !contractEventSubmitGate\.current\.tryEnter\(\)\) return;/);
  assert.match(contractCenterSource, /finally \{[\s\S]*?contractEventSubmitGate\.current\.leave\(\);[\s\S]*?setEventSaving\(false\);/);
  assert.match(contractCenterSource, /confirmLoading=\{eventSaving\}/);
  assert.match(contractCenterSource, /cancelButtonProps=\{\{ disabled: eventSaving \}\}/);
  assert.match(contractCenterSource, /closable=\{!eventSaving\}/);
  assert.match(contractCenterSource, /onCancel=\{\(\) => \{ if \(eventSaving\) return;/);
});
