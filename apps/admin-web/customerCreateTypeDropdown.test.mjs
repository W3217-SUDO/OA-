import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const source = readFileSync(new URL("./src/CustomerCenterPage.tsx", import.meta.url), "utf8");

assert.match(source, /const startCreate = \(customerType = "客户"\) =>/);
assert.match(source, /customer_type: customerType/);
assert.match(source, /\{ key: "客户", label: "新建非诉客户" \}/);
assert.match(source, /\{ key: "当事人", label: "新建诉讼客户" \}/);
assert.match(source, /onClick: \(\{ key \}\) => startCreate\(key\)/);
assert.match(source, /api\.post\("\/customers", \{[\s\S]*\.\.\.details/);

console.log("CUSTOMER_CREATE_TYPE_DROPDOWN_OK");
