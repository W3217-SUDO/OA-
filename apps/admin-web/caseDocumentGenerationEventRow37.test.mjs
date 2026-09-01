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
  ["archive-cover", "生成归档封面"],
  ["authorization-letter", "生成授权委托书"],
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
