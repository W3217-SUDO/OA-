import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'

const source = fs.readFileSync(new URL('./src/SystemCenterPage.tsx', import.meta.url), 'utf8')
const models = fs.readFileSync(new URL('../api-server/app/models.py', import.meta.url), 'utf8')

test('system menu edits implemented menu metadata without exposing dead-route creation', () => {
  assert.doesNotMatch(source, /新增菜单/)
  assert.doesNotMatch(source, /setEditingMenu\(null\)/)
  assert.match(source, /菜单名称描述|菜单描述/)
  assert.match(source, /menuOpen/)
  assert.match(source, /title="修改菜单"/)
  assert.match(source, /name="description"/)
  assert.match(source, /TreeSelect/)
  assert.match(source, /treeCheckable/)
  assert.match(source, /TreeSelect\.SHOW_ALL/)
  assert.match(source, /initialView === "system-roles".*loadMenus/s)
})

test('description belongs to SystemMenu and is not duplicated on SystemConfig', () => {
  const config = models.slice(models.indexOf('class SystemConfig'), models.indexOf('class LawFirm'))
  const menu = models.slice(models.indexOf('class SystemMenu'), models.indexOf('class RolePermission'))
  assert.equal((config.match(/\n\s+description:/g) || []).length, 1)
  assert.match(menu, /\n\s+description:/)
})
