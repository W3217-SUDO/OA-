import assert from "node:assert/strict";
import fs from "node:fs";

const center = fs.readFileSync(new URL("./src/IprCenterPage.tsx", import.meta.url), "utf8");

assert.match(
  center,
  /import \{ rememberCustomerDetailTarget, resolveCustomerDetailTarget \} from "\.\/customerDetailNavigation";/,
  "IPR detail should reuse the protected customer detail navigation contract.",
);

assert.match(
  center,
  /const openLinkedCaseCustomer = async \(customer: IprCaseCustomer\) => \{[\s\S]*?resolveCustomerDetailTarget\(\{[\s\S]*?id: customer\.customer_id,[\s\S]*?serial_no: customer\.customer_no,[\s\S]*?title: customer\.name,[\s\S]*?\}\)/,
  "IPR case customer navigation should resolve by customer id, customer number, and name before routing.",
);

assert.match(
  center,
  /const openLinkedCaseCustomer = async \(customer: IprCaseCustomer\) => \{[\s\S]*?message\.warning\("未找到关联客户或当前账号无权查看"\)/,
  "IPR case customer navigation should show a clear no-access or missing-target warning.",
);

assert.match(
  center,
  /const openLinkedCaseCustomer = async \(customer: IprCaseCustomer\) => \{[\s\S]*?rememberCustomerDetailTarget\(target\);[\s\S]*?onNavigate\?\.\("customer-company"\)/,
  "IPR case customer navigation should remember the resolved target and enter the company customer page.",
);

assert.match(
  center,
  /title: "客户编号",[\s\S]*?dataIndex: "customer_no",[\s\S]*?render: \(value, row\) => <Button type="link" size="small" onClick=\{\(\) => void openLinkedCaseCustomer\(row\)\}>\{value \|\| "—"\}<\/Button>/,
  "IPR detail customer number should be clickable like the legacy ViewCustomer entry.",
);

assert.match(
  center,
  /title: "客户名称",[\s\S]*?dataIndex: "name",[\s\S]*?render: \(value, row\) => <Space><Button type="link" size="small" onClick=\{\(\) => void openLinkedCaseCustomer\(row\)\}>\{value \|\| "—"\}<\/Button>\{row\.is_primary \? <Tag color="blue">主客户<\/Tag> : null\}<\/Space>/,
  "IPR detail customer name should remain visibly marked as primary while linking to customer detail.",
);

console.log("ipr case customer navigation parity: PASS");
