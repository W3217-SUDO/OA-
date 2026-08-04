import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

const appSource = await readFile(
  fileURLToPath(new URL('./src/App.tsx', import.meta.url)),
  'utf8',
)
const hrSource = await readFile(
  fileURLToPath(new URL('./src/HrCenterPage.tsx', import.meta.url)),
  'utf8',
)

function block(source, startNeedle, endNeedle) {
  const start = source.indexOf(startNeedle)
  assert.notEqual(start, -1, 'missing source anchor: ' + startNeedle)
  const end = endNeedle ? source.indexOf(endNeedle, start) : source.length
  assert.notEqual(end, -1, 'missing source end anchor: ' + endNeedle)
  return source.slice(start, end)
}

const canonicalRouteBlock = block(appSource, 'function canonicalRoute(route: string): string {', 'function financeRouteFromPlatform')
const routeLabelsBlock = block(appSource, 'const routePageLabels: Record<string, string> = {', 'function resolveWorkspacePageLabel')
const requestedPageBlock = block(appSource, 'const requestedPage =', '<Card className="panel">')
const editModalBlock = block(hrSource, 'const editModal=', 'const transitionModal=')

test('HR approval relationship entry keeps its guarded frontend route', () => {
  assert.ok(editModalBlock.includes('审批关系'), 'employee edit modal should keep the approval relationship entry')
  assert.ok(
    editModalBlock.includes("openHrAdminNavigation('contract-approver-settings'"),
    'HR approval relationship entry should use the dedicated route key',
  )
})

test('approval relationship route lands on existing system user approval settings page', () => {
  assert.ok(
    canonicalRouteBlock.includes('route === "contract-approver-settings"') &&
      canonicalRouteBlock.includes('return "system-users"'),
    'contract-approver-settings must canonicalize to the existing system user approval settings page',
  )
  assert.ok(
    routeLabelsBlock.includes('"contract-approver-settings": "审批关系"'),
    'workspace tab label should describe approval relationship instead of a generic business page',
  )
  assert.ok(
    requestedPageBlock.indexOf('route.startsWith("system-")') <
      requestedPageBlock.indexOf('route.startsWith("contract-")'),
    'system canonical routes must be selected before generic contract routes can render',
  )
})
