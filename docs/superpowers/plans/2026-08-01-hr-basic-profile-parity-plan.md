# HR Basic Profile Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本地 `dev` 工作副本中，以旧系统为基准补齐员工基本信息缺口，同时保留开发页已有扩展字段。

**Architecture:** 用独立的纯函数模块保存旧系统核心字段顺序、必填字段顺序和状态选项；`HrCenterPage.tsx` 继续负责表单渲染和 API 保存，只消费这些纯函数。验证采用 Node 单元测试、本地前端构建和旧系统/本地页面并行操作。

**Tech Stack:** React 19、TypeScript、Ant Design、Vite、Node test runner、FastAPI/SQLite 本地运行环境。

## Global Constraints

- 所有修改只发生在本地 `dev` 工作副本；服务器只在最终提交后接收推送和部署。
- 开发页已有多余字段不删除；只补旧系统确实存在而开发页缺少的字段或行为。
- 旧系统只读，不创建、修改、删除旧系统数据。
- 不把密码、令牌或私有环境配置提交到 Git。
- 每个行为先写失败测试，再实现，再跑本地浏览器双页面验证。

---

### Task 1: 建立员工核心字段和首个校验缺口的可测试契约

**Files:**
- Create: `apps/admin-web/src/employeeBasicParity.mjs`
- Create: `apps/admin-web/employeeBasicParity.test.mjs`

**Interfaces:**
- Produces `legacyEmployeeCoreFields`, `legacyRequiredEmployeeFields`, and `firstMissingRequiredEmployeeField(values)`.
- `firstMissingRequiredEmployeeField` returns `{key,label,message}` for the first empty required field, or `null` when all required values exist.

- [ ] **Step 1: Write the failing tests**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import {legacyEmployeeCoreFields, legacyRequiredEmployeeFields, firstMissingRequiredEmployeeField} from './src/employeeBasicParity.mjs'

test('keeps the old system core field order without removing extension fields', () => {
  assert.deepEqual(legacyEmployeeCoreFields, [
    'serial_no','username','title','role','password','company','department','position',
    'data_level','is_active','account_type','id_no','mobile','english_level','education',
    'extension','native_place','foreign_language','graduation_date','social_security',
    'school','address','id_address',
  ])
})

test('returns only the first missing required field in old-system order', () => {
  assert.deepEqual(firstMissingRequiredEmployeeField({}), {key:'serial_no',label:'员工号',message:'请输入员工号.'})
  assert.deepEqual(firstMissingRequiredEmployeeField({serial_no:'E-1'}), {key:'username',label:'用户名',message:'请输入用户名.'})
  assert.equal(firstMissingRequiredEmployeeField(Object.fromEntries(legacyRequiredEmployeeFields.map(key => [key, 'ok']))), null)
})
```

- [ ] **Step 2: Run the tests to verify the contract fails**

Run: `node --test employeeBasicParity.test.mjs`

Expected: FAIL because `employeeBasicParity.mjs` does not exist yet.

- [ ] **Step 3: Implement the minimal pure helper**

```js
export const legacyEmployeeCoreFields = [
  'serial_no','username','title','role','password','company','department','position',
  'data_level','is_active','account_type','id_no','mobile','english_level','education',
  'extension','native_place','foreign_language','graduation_date','social_security',
  'school','address','id_address',
]
export const legacyRequiredEmployeeFields = ['serial_no','username','title','role','password','department','position']
export function firstMissingRequiredEmployeeField(values) {
  const labels = {serial_no:'员工号',username:'用户名',title:'中文姓名',role:'角色',password:'密码',department:'部门',position:'职务'}
  const key = legacyRequiredEmployeeFields.find(item => values?.[item] == null || String(values[item]).trim() === '')
  return key ? {key,label:labels[key],message:`请输入${labels[key]}.`} : null
}
```

- [ ] **Step 4: Run the focused tests and all existing HR tests**

Run: `node --test employeeBasicParity.test.mjs employeeBasicSelectOptions.test.mjs employeeSubrecordGuard.test.mjs`

Expected: all tests pass.

- [ ] **Step 5: Commit the tested helper**

```bash
git add apps/admin-web/src/employeeBasicParity.mjs apps/admin-web/employeeBasicParity.test.mjs
git commit -m "test: define employee basic parity contract"
```

### Task 2: Wire the missing-behavior contract into the local employee form

**Files:**
- Modify: `apps/admin-web/src/HrCenterPage.tsx`
- Test: `apps/admin-web/employeeBasicParity.test.mjs`

**Interfaces:**
- `saveEmployee` reads `form.getFieldsValue(true)` and uses `firstMissingRequiredEmployeeField` only for the old-system first-missing behavior; existing extension fields remain rendered and submitted.

- [ ] **Step 1: Add a failing integration-level helper assertion**

```js
test('does not treat extension fields as required core fields', () => {
  assert.equal(firstMissingRequiredEmployeeField({serial_no:'E-1',username:'u',title:'n',role:'user',password:'p',department:'d',position:'普通员工'}), null)
})
```

- [ ] **Step 2: Run the focused test and confirm the failure if the helper contract regresses**

Run: `node --test employeeBasicParity.test.mjs`

Expected: PASS after Task 1; this is the guard used while wiring the form.

- [ ] **Step 3: Wire the helper without deleting extension fields**

In `HrCenterPage.tsx`, import `firstMissingRequiredEmployeeField`; before the existing save API call, read the current form values, derive the first missing required field, and show the existing Ant Design modal with that exact message, returning before any API request. Leave `basicFields` entries after `id_address` intact.

- [ ] **Step 4: Run tests and build locally**

Run: `node --test employeeBasicParity.test.mjs employeeBasicSelectOptions.test.mjs employeeSubrecordGuard.test.mjs` and `npm run build` from `apps/admin-web`.

Expected: all tests pass and Vite reports a successful build.

- [ ] **Step 5: Commit the local form wiring**

```bash
git add apps/admin-web/src/HrCenterPage.tsx apps/admin-web/employeeBasicParity.test.mjs apps/admin-web/package-lock.json
git commit -m "fix: fill employee basic form parity gaps"
```

### Task 3: Verify the local page against the legacy page

**Files:**
- Modify: `docs/功能实现清单.md`
- Modify: `docs/迁移交接与当前状态.md`

- [ ] **Step 1: Reload the local `5173` page and take a fresh DOM snapshot**
- [ ] **Step 2: In both old and local pages, verify the core fields, extension fields, four status defaults, and all five employee tabs**
- [ ] **Step 3: Click save on both empty forms and verify the first missing-field behavior without submitting data**
- [ ] **Step 4: Record only evidence-backed status as 已完成、已验证 or 仍未证明 in the project documents**
- [ ] **Step 5: Run `git diff --check` and commit the verification record**

```bash
git add docs/功能实现清单.md docs/迁移交接与当前状态.md
git commit -m "docs: record local employee parity verification"
```

### Task 4: Prepare final server synchronization without remote builds

**Files:**
- Modify: `docs/迁移交接与当前状态.md`

- [ ] **Step 1: Run local frontend build and backend syntax checks again**
- [ ] **Step 2: Verify `git status`, branch `dev`, and commit history locally**
- [ ] **Step 3: Push the reviewed commits to the server `dev` remote**
- [ ] **Step 4: Trigger the server’s deployment-only workflow, never `npm run build` or dependency installation on the server**
- [ ] **Step 5: Check 8088/8089 health and repeat the same old/local page checks after deployment**
