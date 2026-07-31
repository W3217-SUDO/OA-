# First Priority Corrections Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve the first independently implementable rows of the 2026-07-31 priority workbook without changing the live release until verified.

**Architecture:** Work only in the server-side Git worktree. Keep business-authoritative checks in FastAPI, expose structured data through purpose-specific endpoints, and keep UI changes limited to the applicable page. Use the existing smoke script for API proof and production builds for UI proof.

**Tech Stack:** FastAPI, SQLAlchemy, React + TypeScript + Ant Design, Docker Compose, CodeGraph.

## Global Constraints

- Worktree: `/opt/sunhold-oa/worktrees/codex-resume-20260731` on branch `codex/resume-20260731`.
- Never edit `/opt/sunhold-oa/current` directly; deploy only after all selected tasks pass verification.
- Use CodeGraph before cross-file code navigation; `app/main.py` is over CodeGraph's 1 MB limit and may be read only at the precisely located endpoints.
- Preserve `admin` full permission and all existing data-scope checks.
- Do not create unbounded test data; smoke fixtures must use existing cleanup paths.
- Commit each independently verified task with a conventional, scoped commit message.

---

### Task 1: Explain HR deletion blocking and account availability

**Files:**
- Modify: `apps/api-server/app/main.py` at the HR employee delete logic and add `GET /hr/employees/{employee_id}/deletion-impact`.
- Modify: `apps/admin-web/src/HrCenterPage.tsx` at employee-row actions and availability column.
- Modify: `scripts/smoke-api.py` in the HR lifecycle fixture group.

**Interfaces:**
- Produces `GET /hr/employees/{employee_id}/deletion-impact` with `{deletable:boolean, blockers:[{kind:string,count:number,records:string[]}]}`.
- `DELETE /hr/employees/{employee_id}` continues enforcing the same blockers and returns the same structured blocker payload on HTTP 409.

- [ ] **Step 1: Write failing API assertions**

```python
impact = request("GET", f"/hr/employees/{employee_id}/deletion-impact", token=admin_token)
assert impact.status_code == 200
assert impact.json()["deletable"] is False
assert any(item["kind"] == "关联系统账号" for item in impact.json()["blockers"])
assert request("DELETE", f"/hr/employees/{employee_id}", token=admin_token).status_code == 409
```

- [ ] **Step 2: Run the focused smoke group and confirm failure**

Run: `python scripts/smoke-api.py --group hr_lifecycle`

Expected: the new endpoint is absent or its payload cannot explain the delete block.

- [ ] **Step 3: Implement a shared blocker collector**

```python
def employee_deletion_blockers(db: Session, employee: BusinessRecord) -> list[dict[str, object]]:
    # return stable kind/count/record identifiers for account, child records, attachments and business references
    ...
```

Use this collector in both the preflight endpoint and delete command. Keep conservative blocks for ambiguous JSON references and label them `可能业务关联`.

- [ ] **Step 4: Render the impact before confirmation**

```tsx
const impact = await api.get<DeletionImpact>(`/hr/employees/${row.id}/deletion-impact`);
Modal.confirm({ title: "删除员工", content: <DeletionImpactSummary impact={impact.data} /> });
```

Add an explicit employee-row link to the existing system-user page and relabel the existing availability column to `登录账号可用` with a tooltip that distinguishes account access from employment status.

- [ ] **Step 5: Run focused proof and commit**

Run: `python scripts/smoke-api.py --group hr_lifecycle`; `pnpm --dir apps/admin-web build`; `git diff --check`.

Commit: `git commit -am "fix(hr): explain employee deletion blockers"`.

### Task 2: Make communication log layout readable and add a true view action

**Files:**
- Modify: `apps/admin-web/src/CommunicationLogPage.tsx`.
- Modify: the communication-log stylesheet imported by that page.
- Modify: `scripts/audit-menu-coverage.py` only if it has static checks for communication actions.

**Interfaces:**
- Produces a read-only `viewCommunication(row)` UI path distinct from editable `editCommunication(row)`.
- Keeps the existing `/communications` API and its current server-side visibility rules unchanged.

- [ ] **Step 1: Add a failing static assertion**

```python
assert "查看" in source
assert "readOnly" in source
assert "客户编号" in source and "客户名称" in source
```

- [ ] **Step 2: Run the affected audit and confirm it fails**

Run: `python scripts/audit-menu-coverage.py`

Expected: the new communication-view requirement is absent.

- [ ] **Step 3: Implement separate view state and columns**

```tsx
const [viewing, setViewing] = useState<Communication | null>(null);
// action column: 查看 -> setViewing(row), 编辑 -> startEdit(row), 删除 -> deleteCommunication(row)
```

Use a read-only Drawer or Modal with no save/delete control. Give customer ID and customer name explicit min widths, ellipsis and responsive spacing; retain their existing values and links.

- [ ] **Step 4: Run UI verification and commit**

Run: `pnpm --dir apps/admin-web build`; `python scripts/audit-menu-coverage.py`; `git diff --check`.

Commit: `git commit -am "fix(communication): add read-only view and readable customer columns"`.

### Task 3: Restore customer personnel search suggestions

**Files:**
- Modify: `apps/admin-web/src/CustomerCenterPage.tsx` at create and edit customer forms.
- Modify: `scripts/audit-menu-coverage.py` only if it validates customer form controls.

**Interfaces:**
- Reuses `GET /users/directory` and stores immutable usernames rather than display-name strings for customer source person, managers and linked account selections.

- [ ] **Step 1: Add a failing static assertion**

```python
assert 'showSearch' in customer_source_form_source
assert 'filterOption' in customer_source_form_source
assert '/users/directory' in customer_source_form_source
```

- [ ] **Step 2: Run the audit and confirm it fails**

Run: `python scripts/audit-menu-coverage.py`

Expected: the existing plain Input or free-text tag controls fail the requirement.

- [ ] **Step 3: Implement one reusable directory selector**

```tsx
const directoryOptions = directoryUsers.map(user => ({ value: user.username, label: `${user.display_name}（${user.username}）` }));
<Select showSearch optionFilterProp="label" filterOption options={directoryOptions} />
```

Use it in create and edit forms. Preserve external contacts as plain text only where the field is explicitly not a system account.

- [ ] **Step 4: Run verification and commit**

Run: `pnpm --dir apps/admin-web build`; `python scripts/audit-menu-coverage.py`; `git diff --check`.

Commit: `git commit -am "fix(customer): add personnel directory suggestions"`.

### Task 4: Correct customer list actions, recycle filtering and shared-recipient visibility

**Files:**
- Modify: `apps/api-server/app/main.py` at the `/customers` scope query and customer dictionary.
- Modify: `apps/admin-web/src/CustomerCenterPage.tsx` at mine/company/shared columns and actions.
- Modify: `scripts/smoke-api.py` in customer scope fixtures.

**Interfaces:**
- `scope=company` excludes `已回收` customer records; only the recycle scope returns them.
- Shared-customer responses expose `shared_with` only to authorized shared viewers and administrators.
- Mine scope has no customer recycle action in the UI; company actions remain server-authorized.

- [ ] **Step 1: Add failing API assertions**

```python
company = request("GET", "/customers", params={"scope": "company"}, token=admin_token).json()["items"]
assert recycled_customer_id not in {item["id"] for item in company}
shared = request("GET", "/customers", params={"scope": "shared"}, token=shared_user_token).json()["items"]
assert shared[0]["data"]["shared_with"] == [shared_username]
```

- [ ] **Step 2: Run the focused customer smoke group and confirm failure**

Run: `python scripts/smoke-api.py --group customer_scope`

Expected: a recycled customer remains in the company list or shared recipients are not returned.

- [ ] **Step 3: Implement scope-consistent serialization and UI actions**

```python
if scope == "company":
    query = query.where(BusinessRecord.status.not_in(["公海", "已回收"]))
```

Add a `被共享人` column only in the shared list, using directory labels. Remove delete/recycle from mine actions without removing the server-side, role-protected company operation.

- [ ] **Step 4: Run focused proof and commit**

Run: `python scripts/smoke-api.py --group customer_scope`; `pnpm --dir apps/admin-web build`; `git diff --check`.

Commit: `git commit -am "fix(customer): align list actions and recycle visibility"`.

### Task 5: Tidy the customer query toolbar without changing behavior

**Files:**
- Modify: `apps/admin-web/src/CustomerCenterPage.tsx` only if a semantic trigger is needed.
- Modify: the customer-center stylesheet imported by that page.

**Interfaces:**
- Preserves current query parameters and API calls.
- Any collapsed/expanded control uses a labelled button and `aria-expanded`.

- [ ] **Step 1: Add a failing visual-contract assertion**

```python
assert "aria-expanded" in customer_toolbar_source
assert "DownOutlined" in customer_toolbar_source
```

- [ ] **Step 2: Run the audit and confirm it fails**

Run: `python scripts/audit-menu-coverage.py`

Expected: the toolbar has no semantic expansion affordance.

- [ ] **Step 3: Implement the smallest layout change**

```tsx
<Button type="text" aria-expanded={filtersOpen} icon={<DownOutlined rotate={filtersOpen ? 180 : 0} />} onClick={() => setFiltersOpen(v => !v)} />
```

Use CSS grid gaps and responsive breakpoints to move the search field right only when the filter panel is visible; do not alter filter data or defaults.

- [ ] **Step 4: Build, render-check in browser and commit**

Run: `pnpm --dir apps/admin-web build`; `git diff --check`.

Commit: `git commit -am "fix(customer): clarify query toolbar layout"`.

## Final Verification

- [ ] Run `docker compose --env-file .env.production -f docker-compose.yml -f compose.prod.yml -f compose.test-server.yml config -q` in the worktree.
- [ ] Run the selected smoke groups, `python scripts/audit-menu-coverage.py`, `python scripts/audit-client-api-coverage.py`, Python compilation and `pnpm --dir apps/admin-web build`.
- [ ] Run `codegraph sync` followed by `codegraph status`; record that `main.py` remains excluded by the 1 MB CodeGraph limit.
- [ ] Update `docs/迁移交接与当前状态.md` with CodeGraph query topics, each row's completed/verified/unproven status, and deployment status.
- [ ] Commit docs and verification evidence with `git commit -am "docs: record first priority corrections"`.
