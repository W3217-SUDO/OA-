import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const read = (name) => fs.readFileSync(new URL(`./src/${name}`, import.meta.url), "utf8");
const business = read("BusinessPage.tsx");
const documents = read("DocumentCenterPage.tsx");
const warehouse = read("WarehousePage.tsx");
const receivables = read("ContractReceivablesPage.tsx");

test("third-batch people fields use projected display names with a stable placeholder", () => {
  for (const [name, source] of Object.entries({ business, documents, warehouse, receivables })) {
    assert.match(source, /String\(value\s*\|\|\s*["']{2}\)\.trim\(\)\s*\|\|\s*["']姓名待维护["']/, `${name} must accept any non-empty display name, including English names`);
  }

  assert.match(business, /dataIndex:'owner_display_name'/);
  assert.match(business, /personDisplayName\(event\.operator_display_name\)/);
  assert.doesNotMatch(business, /<Descriptions\.Item label="负责人">\{viewing\.owner\}/);
  assert.doesNotMatch(business, /<small>\{event\.operator\}/);

  for (const field of ["owner_display_name", "uploader_display_name", "auditor_display_name", "operator_display_name", "signer_display_name", "hearing_lawyer_display_name", "assistant_display_name", "brand_manager_display_name"]) {
    assert.ok(documents.includes(field), `DocumentCenterPage must support ${field}`);
  }
  assert.doesNotMatch(documents, /title: "负责人", dataIndex: "owner"/);
  assert.doesNotMatch(documents, /title: "上传人", dataIndex: "uploader"/);
  assert.doesNotMatch(documents, /title: "申请人", dataIndex: "owner"/);
  assert.doesNotMatch(documents, /title: "审核人", dataIndex: "auditor"/);

  assert.match(warehouse, /data\.investigator_display_name\s*\|\|\s*row\.owner_display_name/);
  assert.match(warehouse, /personDisplayName\(item\.operator_display_name\)/);
  assert.doesNotMatch(warehouse, /render:\(_v,row\)=>row\.data\.investigator\|\|row\.owner/);

  assert.match(receivables, /source_person_display_name\s*\|\|\s*row\.owner_display_name/);
  assert.match(receivables, /customer_manager_display_names\s*\|\|\s*row\.data\.customer_manager_display_name/);
  assert.doesNotMatch(receivables, /render: \(_:\s*unknown, row: Contract\) => row\.data\.source_person \|\| row\.owner/);
  assert.doesNotMatch(receivables, /render: \(_:\s*unknown, row: Contract\) => row\.data\.customer_manager \|\|/);
});
