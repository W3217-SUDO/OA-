import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const source = readFileSync(new URL('./src/WarehousePage.tsx', import.meta.url), 'utf8');

assert.match(source, /pageSizeOptions:\['10','15','20','50','100','200'\]/);
assert.match(source, /defaultPageSize:15/);
assert.match(source, /showSizeChanger:true/);
assert.match(source, /showQuickJumper:true/);
assert.match(source, /showTotal:total=>`共 \$\{total\} 条`/);
assert.match(source, /onClick=\{\(\)=>void load\(\)\}/);
assert.match(source, /onClick=\{\(\)=>openEditor\(\)\}/);
assert.match(source, /onCancel=\{\(\)=>setEditorOpen\(false\)\}/);
console.log('warehouse parity checks passed');
