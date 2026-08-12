import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";

const source = await readFile(new URL("./src/TaskCenterPage.tsx", import.meta.url), "utf8");

test("task center renders system display names without requiring Chinese characters", () => {
  assert.match(source, /const visiblePersonName = \(displayName\?: string \| null\) =>/);
  assert.match(source, /String\(displayName \|\| ""\)\.trim\(\) \|\| PERSON_NAME_PLACEHOLDER/);
  assert.doesNotMatch(source, /\\u4e00|hasChinese|isChinese|中文姓名/);
  assert.doesNotMatch(source, /displayName[^\n]*(?:username|owner|initiator|operator|uploader)/);
});

test("task lists and details use projected owner and initiator names", () => {
  assert.match(source, /visiblePersonName\(row\.initiator_display_name\)/);
  assert.match(source, /visiblePersonName\(row\.owner_display_name\)/);
  assert.match(source, /visiblePersonName\(communication\?\.owner_display_name\)/);
  assert.match(source, /visiblePersonName\(communication\?\.initiator_display_name\)/);
  assert.doesNotMatch(source, />\{row\.owner \|\| "-"\}</);
  assert.doesNotMatch(source, />\{communication\?\.owner \|\| "-"\}</);
  assert.doesNotMatch(source, />\{communication\?\.initiator \|\| "-"\}</);
});

test("task history and attachments never expose account identifiers as names", () => {
  assert.match(source, /visiblePersonName\(item\.operator_display_name\)/);
  assert.match(source, /visiblePersonName\(item\.uploader_display_name\)/);
  assert.doesNotMatch(source, /<b>\{item\.operator\}<\/b>/);
  assert.doesNotMatch(source, /title: "上传人", dataIndex: "uploader", width: 110 \}/);
});

test("missing unread sender and collaborator projections use a safe placeholder", () => {
  assert.match(source, /visibleOptionalPersonName\(value, row\.latest_unread_sender_display_name\)/);
  assert.match(source, /visibleCollaboratorNames\(communication\)/);
  assert.match(source, /return names\.length === row\.collaborators\.length \? names\.join\("、"\) : PERSON_NAME_PLACEHOLDER/);
  assert.doesNotMatch(source, /communication\?\.collaborators\?\.join/);
});

test("raw usernames remain available for ACL and value operations", () => {
  assert.match(source, /row\.initiator === profile\.username/);
  assert.match(source, /item\.uploader === profile\.username/);
  assert.match(source, /dialogForm\.setFieldsValue\(\{ recipient: row\.owner \}\)/);
});
