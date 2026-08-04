import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('./src/IprCenterPage.tsx', import.meta.url), 'utf8');

test('IPR main list exposes legacy page size and GO pagination controls', () => {
  assert.match(
    source,
    /pagination=\{\{[\s\S]*?current: page,[\s\S]*?pageSize: pageSize,[\s\S]*?total,[\s\S]*?showSizeChanger: true,[\s\S]*?pageSizeOptions: \["15", "20", "50", "100"\],[\s\S]*?showQuickJumper: \{ goButton: <Button size="small">GO<\/Button> \},[\s\S]*?onChange: \(nextPage, nextPageSize\) => void load\(nextPage, nextPageSize\),[\s\S]*?\}\}/,
    'IPR main table should keep server pagination while exposing page-size selection and a GO jumper.',
  );
});
