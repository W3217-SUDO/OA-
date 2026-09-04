import assert from "node:assert/strict";
import test from "node:test";
import {
  dispatchCaseDocumentGenerationMenuClick,
  getLegacyCaseDocumentGenerationItems,
} from "./src/caseDocumentGenerationActions.mjs";

const clickEvent = (key, calls) => ({
  key,
  domEvent: {
    preventDefault: () => calls.push("preventDefault"),
    stopPropagation: () => calls.push("stopPropagation"),
  },
});

for (const [key, label] of [
  ["identification_letter", "生成鉴定函"],
  ["archive-cover", "生成归档封面"],
  ["authorization-letter", "生成授权委托书"],
  ["gd-authorization-letter", "生成广东版授权委托书"],
  ["gd-first-instance-appellant-lawyer-letter", "生成广东版一审上诉人律师函"],
  ["gd-first-instance-appellee-lawyer-letter", "生成广东版一审被上诉人律师函"],
  ["gd-second-instance-appellant-lawyer-letter", "生成广东版二审上诉人律师函"],
  ["gd-second-instance-appellee-lawyer-letter", "生成广东版二审被上诉人律师函"],
  ["gd-execution-lawyer-letter", "生成广东版执行律师函"],
]) {
  test(`${label} menu click dispatches its exact API action key`, () => {
    const calls = [];
    const actions = [];
    const handled = dispatchCaseDocumentGenerationMenuClick(
      clickEvent(key, calls),
      (actionKey) => actions.push(actionKey),
    );

    assert.equal(handled, true);
    assert.deepEqual(calls, ["preventDefault", "stopPropagation"]);
    assert.deepEqual(actions, [key]);
  });
}

test("the first two visible menu labels retain the backend route keys", () => {
  assert.deepEqual(getLegacyCaseDocumentGenerationItems().slice(0, 2), [
    ["archive-cover", "生成归档封面"],
    ["authorization-letter", "生成授权委托书"],
  ]);
});

test("unknown menu keys cannot call the document generation action", () => {
  const actions = [];
  const handled = dispatchCaseDocumentGenerationMenuClick(
    clickEvent("archive-letter", []),
    (actionKey) => actions.push(actionKey),
  );
  assert.equal(handled, false);
  assert.deepEqual(actions, []);
});
