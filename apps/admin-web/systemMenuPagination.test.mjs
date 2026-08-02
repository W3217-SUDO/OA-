import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/SystemCenterPage.tsx', import.meta.url), 'utf8')
const menuStart = source.indexOf('} else if (initialView === "system-management-menu")')
const menuEnd = source.indexOf('} else if (initialView === "system-management-config")', menuStart)
const menuBlock = source.slice(menuStart, menuEnd)

test('menu management supports local pagination and page-size controls', () => {
  assert.match(source, /menuPageSize/)
  assert.match(source, /menuSearchInput/)
  assert.match(source, /const \[menuSearch, setMenuSearch\]/)
  assert.match(source, /pageSizeOptions: \["10", "15", "20", "30", "50", "100", "200"\]/)
  assert.match(source, /showQuickJumper: true/)
  assert.doesNotMatch(menuBlock, /menuPageInput|setMenuPageInput/)
  assert.match(menuBlock, /menuJumpPage/)
  assert.match(menuBlock, />GO<\/Button>/)
  assert.match(source, /filteredSystemMenus\.length/)
})

test('menu query and reset return to page one', () => {
  assert.match(source, /setMenuSearch\(menuSearchInput\); setMenuPage\(1\)/)
  assert.match(source, /setMenuSearchInput\(""\); setMenuSearch\(""\); setMenuPage\(1\)/)
  assert.match(source, /showQuickJumper: true/)
})
