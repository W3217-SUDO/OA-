import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const source = fs.readFileSync(new URL("./CaseCenterPage.tsx", import.meta.url), "utf8");

test("all three case-fee scopes expose the batch notification-date action", () => {
  assert.match(source, /selectedFirmFeeKeys[\s\S]*label:"修改通知日期"/);
  assert.match(source, /selectedPlatformFeeKeys[\s\S]*label:"修改通知日期"/);
  assert.match(source, /selectedInternalFeeKeys[\s\S]*>修改通知日期<\/Button>/);
  assert.match(source, /if\(key==="inform-date"\)return openInformDateBatchUpdate\(keys\)/);
});

test("notification-date modal requires a date and reports the selected count", () => {
  assert.match(source, /title=\{`修改通知日期（已选 \$\{informDateFeeKeys\?\.length\|\|0\} 条）`\}/);
  assert.match(source, /Form\.Item label="通知日期" name="inform_date" rules=\{\[\{required:true,message:"请选择通知日期"\}\]\}/);
  assert.match(source, /<DatePicker style=\{\{width:"100%"\}\} \/>/);
});

test("selected fee ids and normalized date are submitted to the batch endpoint", () => {
  assert.match(source, /api\.post\("\/finance\/case-fees\/batch-update",\{/);
  assert.match(source, /fee_ids:feeIds/);
  assert.match(source, /inform_date:formatRequiredDate\(values\.inform_date,"通知日期"\)/);
  assert.match(source, /if\(viewingCounselCase\)await openCounselDetail\(viewingCounselCase\)/);
});
