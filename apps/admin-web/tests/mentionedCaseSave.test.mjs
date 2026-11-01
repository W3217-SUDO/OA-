import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';

// 陶国南 11-01：说“存到/保存到某某案件”并写了案号，回答下方给“保存到案件”按钮。
const source = fs.readFileSync(new URL('../src/personal-agent/types.ts', import.meta.url), 'utf8');
const start = source.indexOf('export function mentionedCaseSerial');
const body = source.slice(start, source.indexOf('\n}\n', start) + 2);
const compiled = ts.transpileModule(body, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText;
const exports = {};
new Function('exports', compiled)(exports);
const { mentionedCaseSerial } = exports;

test('case number with a save request is detected', () => {
  assert.equal(mentionedCaseSerial('帮我下载并保存为word格式，保存到HZMS2600441案件文档中'), 'HZMS2600441');
  assert.equal(mentionedCaseSerial('把这个存入 hzms2600441 案件'), 'HZMS2600441');
  assert.equal(mentionedCaseSerial('放到案件HZXS2500012里'), 'HZXS2500012');
});

test('no save request or no case number means no case button', () => {
  assert.equal(mentionedCaseSerial('查一下 HZMS2600441 的开庭时间'), null);
  assert.equal(mentionedCaseSerial('帮我保存为 word'), null);
  assert.equal(mentionedCaseSerial(undefined), null);
});
