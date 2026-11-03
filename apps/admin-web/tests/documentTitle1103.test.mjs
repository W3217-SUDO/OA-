// 陶威 11-03：保存 AI 回答为 Word 时，文件名取文书标题，不取回答开头的说明句。
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";
import ts from "typescript";

const source = fs.readFileSync(new URL("../src/legal/documentTitle.ts", import.meta.url), "utf8");
const output = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const module = { exports: {} };
vm.runInNewContext(output, { module, exports: module.exports });
const { documentTitleFromContent } = module.exports;

test("回答开头是说明句时，取后面的文书标题", () => {
  const answer = "关于 Word 这件事需要先说明一点：我在后台沙箱里生成的文件，你在页面上看不到。\n\n**委托代理合同**\n\n甲方：____";
  assert.equal(documentTitleFromContent(answer), "委托代理合同");
  assert.equal(documentTitleFromContent("以下是模板，可以直接保存：\n\n# 民事起诉状\n\n原告：张三"), "民事起诉状");
});

test("没有标题标记时取第一行像标题的短句，都没有才退回第一行", () => {
  assert.equal(documentTitleFromContent("好的，下面是草稿。\n律师函\n致：某某公司"), "律师函");
  assert.equal(documentTitleFromContent("这是一段很长的说明，没有任何标题，也没有短行可以当作标题使用的情况下应该如何处理呢"),
    "这是一段很长的说明，没有任何标题，也没有短行可以当作标题使用的情况下应该如何处理呢".slice(0, 60));
  assert.equal(documentTitleFromContent("# 合同/补充协议:第1版"), "合同 补充协议 第1版");
});
