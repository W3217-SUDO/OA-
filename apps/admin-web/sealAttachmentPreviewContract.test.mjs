import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal preview consumes the JSON preview contract before rendering", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

  assert.match(source, /type SealPreviewMode/);
  assert.match(source, /function getSealPreviewMode/);
  assert.match(source, /getSealPreviewMode\(/);
  assert.match(source, /previewText/);
  assert.doesNotMatch(
    source,
    /api\.get\(\`\/attachments\/\$\{item\.id\}\/preview\`, \{\s*responseType: "blob"/,
  );
});
