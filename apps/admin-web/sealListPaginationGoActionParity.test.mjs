import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync("src/SealCenterPage.tsx", "utf8");

test("seal list legacy GO footer drives the visible table page", () => {
  assert.match(
    source,
    /const \[applicationPage, setApplicationPage\] = useState\(1\);/,
    "the list page must be controlled instead of leaving the legacy GO button inert",
  );
  assert.match(
    source,
    /current: applicationPage,[\s\S]*?onChange: \(page: number, pageSize: number\) => \{[\s\S]*?setApplicationPage\(page\);/,
    "table pagination and the legacy footer must share one page state",
  );
  assert.match(
    source,
    /const goToApplicationPage = \(\) => \{[\s\S]*?applicationPageCount[\s\S]*?setApplicationPage\(page\);/,
    "GO should constrain the requested page to the visible page range",
  );
  assert.match(
    source,
    /aria-label="分页跳转"[\s\S]*?value=\{applicationGoPage\}[\s\S]*?<Button size="small" onClick=\{goToApplicationPage\}>[\s\S]*?GO/,
    "the visible GO button must submit the selected page rather than being decorative",
  );
});
