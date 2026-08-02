import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

test("seal detail exposes a read-only file preview action", () => {
  const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");
  assert.match(source, /const \[previewOpen, setPreviewOpen\] = useState\(false\)/);
  assert.match(source, /const \[previewUrl, setPreviewUrl\] = useState\(""\)/);
  assert.doesNotMatch(source, /window\.open\(/);
  assert.match(source, /title=\{`文件预览：\$\{previewName\}`\}/);
  assert.match(source, /预览/);
});
