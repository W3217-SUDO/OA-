import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const page = readFileSync(new URL("./src/CaseCenterPage.tsx", import.meta.url), "utf8");

test("row 9 gives platform fees the same legacy detail columns as firm fees", () => {
  assert.match(page, /const externalCaseFeeColumns=\[/);
  for (const title of ["合同编号", "费用类型", "申请付款金额", "付款账号", "退费", "提交人", "提交日期", "回款日期", "回款金额", "开票日期", "发票号"]) {
    assert.match(page, new RegExp(`title:\"${title}\"`));
  }
  assert.match(page, /dataSource=\{platformFeeRows\}[\s\S]*?rowSelection=\{\{selectedRowKeys:selectedPlatformFeeKeys,onChange:setSelectedPlatformFeeKeys\}\}[\s\S]*?columns=\{externalCaseFeeColumns\}/);
});

test("row 9 exposes the four legacy create entries for populated platform fees", () => {
  assert.match(page, /platformFeeRows\.length>0&&<Space className="case-legacy-bottom-actions">/);
  assert.match(page, /\{key:"官费",label:"新增官费"\}[\s\S]*?\{key:"第三方费用",label:"新增第三方费用"\}[\s\S]*?\{key:"代理费",label:"新增代理费"\}[\s\S]*?\{key:"其他费用",label:"新增其他费用"\}/);
  assert.match(page, /onClick:\(\{key\}\)=>openCaseFeeBySubtype\("平台",key\)/);
  assert.doesNotMatch(page, />新增平台费用<\/Button>/);
});

test("row 9 keeps platform selection and operations isolated from firm fees", () => {
  assert.match(page, /const \[selectedPlatformFeeKeys, setSelectedPlatformFeeKeys\] = useState<Key\[]>\(\[\]\)/);
  assert.match(page, /const selectedPlatformFee=platformFeeRows\.find\(row=>selectedPlatformFeeKeys\.includes\(row\.id\)\)/);
  assert.match(page, /handleExternalFeeOperation\(selectedPlatformFeeKeys,selectedPlatformFee,key\)/);
});
