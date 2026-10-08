---
name: oa-fast-deploy
description: Fast, safe deployment workflow for the Sunhold OA repository. Use whenever an OA remediation session needs to publish tested work, update the shared dev branch, allocate a formal 1.1.x version, deploy to port 8089, apply a database migration, roll back a failed release, or record online browser acceptance.
---

# OA Fast Deploy

Use a linear shared `dev` branch to remove unnecessary integration-session handoffs while keeping each editing session isolated in its own worktree. A problem session that finishes implementation, verification, and build may register itself as the unique release-coordination session and publish from the same conversation. Serialize only version allocation and formal activation.

## Invariants

- Keep each session in its own branch/worktree while editing and testing. Never let two sessions edit one working directory.
- Treat `dev` as the only integration branch. Keep its history linear; do not create merge commits.
- Remote roles are fixed: `origin` is the Tencent server Git remote used by the production worktree; `github` is `https://github.com/W3217-SUDO/OA-.git` used for durable source synchronization. Never infer a remote's role from its name alone: verify `git remote -v` before every push.
- The only permanent development/release branches are `dev`, `main` on GitHub, and the server-managed `production-current` pointer where it already exists. Formal releases are preserved by annotated tags, not by accumulating `release-*`, `deploy-*`, `ready-*`, or issue branches.
- Feature branches are local by default. Push a temporary feature branch only when another session must fetch that exact commit and `dev` cannot yet accept it. Record its purpose and delete it from both remotes immediately after integration or abandonment.
- Never force-push during ordinary integration, reset away another session's commit, upload a source directory, reuse an occupied version, or replace the online database. The only exception is the controlled divergent-baseline reconciliation defined below.
- Deploy only from the fixed server worktree `/opt/sunhold-oa/worktrees/production-current`.
- Build the frontend production artifact on the local tested worktree, archive it, and record its SHA256 before upload. Never run `npm run build`, `vite build`, or TypeScript compilation on the resource-constrained OA server.
- Do not back up the whole database for ordinary releases. When a release changes database schema or data, back up only the affected tables plus the minimum related rows needed to verify and restore their relationships; store those scoped backups off-server on the local workstation or approved external storage. Pure application-code releases do not require a database backup. Never retain database dumps or release backup archives under `/opt/sunhold-oa/backups`.
- Excel-row releases require the local verification defined by `problem-remediation`. Direct user-stated issues may be released without local or online business tests; the production build and operational activation checks remain required. Do not mark an Excel row `1` before the user explicitly confirms it passed.
- Continue the existing active release unchanged. The next new release train starts at `1.1.1`; subsequent formal releases use `1.1.2`, `1.1.3`, and so on. Failed and rolled-back numbers remain occupied.

## 1. Prepare A Tested Change

1. Read the complete problem row and follow `problem-remediation` through focused tests, production build, persistence/API verification where applicable, and test-data cleanup.
2. Commit only owned files on the session branch. Exclude unrelated dirty files and temporary artifacts.
3. Record the commit, Excel row(s), tests, automated evidence, database patch, and rollback requirements.
4. Do not change the formal package version or create a formal tag in a feature commit.

## 2. Submit Readiness Before Shared Dev

Keep the tested feature commit on the session's local branch and send the readiness receipt in section 3. Do not create or push a remote feature branch merely as a checkpoint. If cross-session handoff genuinely requires a remote ref, use one short-lived `codex/<issue>` branch, report its exact commit, and mark it for deletion after integration. Do not update `dev` until the primary task assigns this session the release slot.

When the primary task says the session is next, immediately before updating `dev` run:

```powershell
git fetch --all --prune --tags
git rebase origin/dev
```

Rerun affected tests and the production build after a non-trivial rebase. Then push the exact tested HEAD as a fast-forward:

```powershell
git push origin HEAD:dev
```

If rejected, another session won the race. Fetch, rebase onto the new `origin/dev`, resolve only owned files, rerun affected tests/build, and retry. Do not merge and do not force-push.

After the push, report the exact remote `dev` commit to the primary task. Do not choose a version yet. No permanent integration or coordinator worktree is required.

Mirror the same fast-forward `dev` commit to GitHub after verifying both remotes' current heads:

```powershell
git push origin HEAD:dev
git push github HEAD:dev
```

Both pushes must resolve to the same commit. A successful push to only one remote is an incomplete synchronization, not a completed release candidate.

## 2.5 CI Quality Gate Before Release

Do not reserve a version, create a release tag, activate the server, or move GitHub `main` until the exact candidate commit has passed the repository quality workflow. This gate exists to prevent a release from being published while the later `quality` job is still failing.

1. Run `scripts/quality_gate.py` against the exact candidate with Python 3.12 and Node.js 22, matching `.github/workflows/quality.yml`. A different local runtime is not an acceptable substitute; if the required runtimes are unavailable locally, rely on the GitHub workflow and do not claim local quality-gate completion.
2. After pushing the candidate to both `origin/dev` and `github/dev`, query the GitHub Actions run for that exact SHA. Wait until the `quality` job is `completed` with conclusion `success`; `queued`, `in_progress`, a different SHA, or a partial step result is a release blocker.
3. Read the uploaded `quality-evidence` artifact and confirm `quality-gate.json` has `passed: true` and every recorded step has exit code `0`. If the artifact is unavailable or any step failed, keep the version unallocated, leave `main` unchanged, and return to diagnosis.
4. Only after this gate passes may the release proceed to version allocation and server activation. After fast-forwarding GitHub `main`, wait for its Actions run on the same release SHA and require the same `quality` success before reporting synchronization complete.

When a quality failure is caused by a changed business rule, update the affected regression fixture or implementation together with a focused test, rerun the exact failing test locally, and rerun the full CI quality gate. Never skip or weaken a regression assertion merely to make the workflow green.

## 3. Formal Release Gate

For a direct standalone OA issue, the user's request includes authorization to release immediately after the code change and required production build; do not run local or online business tests and do not wait for a second "deploy" message. For an Excel batch, wait until every included row passes the local verification defined by `problem-remediation`, then release the batch once. Browser testing is left to the user. Immediately before every release, read all of the following from authoritative sources:

- remote `dev` HEAD and selected target commit;
- server `production-current` HEAD and exact active tag;
- frontend package version and served static asset version;
- all occupied `v1.1.*` tags and the deployment ledger;
- effective systemd working directories and health status;
- pending database migrations and explicit local-data merge manifest.

If these disagree, stop activation and repair the baseline first.

Before publishing, the owning session records this readiness receipt. If no other session owns the formal release lock or an earlier reserved slot, the current session may claim the next release slot and continue without handing off to another conversation. If another coordinator or reservation is active, send the receipt to that coordinator and wait:

```text
READY TO RELEASE
rows/issues: ...
dev commit: ...
owned files: ...
backend tests: ...
frontend tests: ...
production build: ...
automated verification evidence: ...
database migration/data patch: none | ...
rollback notes: ...
```

The session holding the release slot validates the receipt, current `dev`, active server baseline, occupied versions, and release lock. When that session is also the issue-owning session, it may reserve the next unique version and perform the release directly. A problem session must not update `dev` outside its claimed or assigned release slot, and it must yield if the authoritative queue shows an earlier active reservation.

The active-baseline check must compare all three values independently: the fixed production worktree `HEAD`, `refs/heads/production-current`, and the tag recorded as active in the release queue. A stale `production-current` ref is a release blocker even when the worktree happens to contain the right files. Under the formal release lock, repair it only after verifying the old ref is the recorded baseline and is an ancestor of the worktree/tag commit, using an exact old-value `git update-ref`; record the old ref, new ref, and verification result in the activation evidence. Never silently continue with a worktree/ref mismatch.

The same baseline receipt must require git status --porcelain=v1 to be empty in the fixed production worktree. Untracked files count as dirty state; move them outside the worktree or remove only after their owner and retention need are confirmed. Do not activate, package, or silently ignore a worktree that contains test scripts, fixtures, mocks, debug files, temporary archives, or other untracked artifacts.

## 4. Allocate The Version

The primary task uploads and runs `scripts/reserve_oa_version.sh <target-commit> <session-id> <scope>` on the server. The script locks `/opt/sunhold-oa/locks/version-allocation.lock`, combines occupied Git tags with `/opt/sunhold-oa/releases/queue.tsv`, reserves the next number, and prints it. It returns `1.1.1` when no `1.1.x` release exists and otherwise increments the greatest occupied patch number by one. Use `scripts/next_oa_version.py` only for local preview; the server reservation is authoritative.

Allocate late, after tests/build pass. After the primary task assigns a version, the owning session updates the package version, commits it on top of the selected `dev` commit, creates the matching annotated tag, and pushes the commit and tag. A rejected branch/tag push means the allocation lost a race: stop, report to the primary task, fetch, receive a new unused number, rebuild, and retry. Never reuse the failed number.

The package version, release commit, Git tag, build artifact, deployment ledger, and served version must match exactly.

Push the release commit and annotated tag to both authoritative remotes. Do not create a release branch:

```powershell
git push origin <release-commit>:dev refs/tags/<tag>
git push github <release-commit>:dev refs/tags/<tag>
```

## 5. Serialize Server Activation

Before taking the activation lock, inspect the migration and data-patch manifest. If there is no database change, record `database backup: not required (no database change)` and continue without a dump. If schema or data changes are present, export only every affected table and the minimum related rows required to verify and restore foreign-key or soft-link relationships into a versioned local directory. Record the source database, table/row scope, release version, target commit, and snapshot time, then verify every scoped backup is non-empty and its SHA256 matches a separately captured digest. A missing affected table, relationship scope, transfer, or checksum blocks the release. Whole-database dumps are prohibited unless the user explicitly authorizes disaster-recovery work.

If a required scoped export cannot be streamed directly, it may exist only as short-lived staging under `/tmp`; transfer and verify it locally, then delete the server staging file before activation. Never leave database exports, frontend archives, or release backup directories on the server after the transfer.

Only server activation is locked. Upload one standalone Linux release script and execute the complete critical section under:

```bash
flock -x /opt/sunhold-oa/locks/formal-release.lock -c '/tmp/activate-oa-release.sh <commit> <tag>'
```

The script must, while holding the lock:

1. Re-read the active commit/tag and remote `dev` HEAD.
2. Abort unless the target is the expected tested commit and can fast-forward the active baseline.
3. Confirm either that the release has no database change, or that the verified scoped table/relationship backup manifest belongs to this target release and was completed immediately before activation.
4. Apply only repeatable migrations and explicitly listed data merges; verify keys and relations.
5. Fetch and fast-forward `/opt/sunhold-oa/worktrees/production-current` to the target commit.
6. Verify the uploaded frontend archive SHA256 against the locally recorded value, extract it into the fixed worktree without running any server-side frontend build, confirm both systemd services point to the fixed worktree, restart them, and poll API/Web health for up to 60 seconds.
7. Check API health, static assets, package/tag/commit consistency, and critical database counts.
8. Remove any server-side temporary backup staging and verify that no release database export remains on the server.

Complex Windows-to-Linux commands must be written to a `.sh` file and uploaded. Do not embed pipelines, heredocs, nested quoting, or JSON inside a PowerShell SSH string.

## 6. Online Acceptance And Rollback

Do not open or control a browser after deployment unless the user explicitly requests it for the current issue. Verify the deployed commit/tag/package, static assets, service working directories, API/Web health and logs, then report the issue as `awaiting user acceptance`.

On failure:

- keep the failed version occupied;
- roll the fixed production worktree and services back to the last proven active tag;
- reverse only migrations with an explicitly tested down path; otherwise restore the verified affected-table/related-row backup according to the migration plan;
- leave the Excel row incomplete and fix forward under a new version.

After healthy activation, update the deployment ledger and leave affected Excel rows as `待用户验收`. Only after the user explicitly confirms a row passed may it be marked `1`, preserving workbook media and formatting. Report active commit/tag/version, backups, migrations, tests, health evidence, user acceptance state, and rollback point.

Then synchronize GitHub `main` by a strict fast-forward from the exact released commit and verify `github/main`, `github/dev`, the release tag, and the active server commit are identical:

```powershell
git push github <release-commit>:main
git ls-remote github refs/heads/main refs/heads/dev refs/tags/<tag>^{}
```

Finally delete any temporary feature branch created for this release from both remotes. Never delete `dev`, GitHub `main`, `production-current`, formal tags, active safety refs, or an unmerged branch. A branch cleanup is complete only after `git fetch --all --prune` and `git ls-remote --heads` confirm removal.

## 7. Deterministic Release Order

Every ordinary release follows this exact order; do not interleave branch creation or optional pushes:

1. Verify `git remote -v`, clean owned worktree state, remote `dev` heads, active server commit/tag, queue and release lock.
2. Rebase the local tested commit onto the latest authoritative `dev`; rerun affected checks when the base changed.
3. Fast-forward the identical commit to `origin/dev` and `github/dev`; verify both hashes.
4. Reserve one version under the queue lock, change only the package version files, build locally, create one release commit and one annotated tag.
5. Push the same release commit/tag to both remotes. Do not create a release/deploy/ready branch.
6. Activate only the fixed server worktree under `formal-release.lock`; verify health, assets, services, logs and database scope.
7. Fast-forward `github/main` to the released commit, record the ledger, and delete any short-lived handoff branch.

Stop immediately on any hash mismatch, non-fast-forward rejection, occupied version, active lock, build failure, migration uncertainty, or health failure. Preserve the local commit and report the exact mismatch; do not improvise another branch or version.

## 8. Scope And Concurrency

- Multiple sessions may edit/test concurrently and push their tested commits to their own branches. Only the session holding the release slot may fast-forward `dev`.
- The primary task assigns versions and deployment order; owning sessions deploy only after receiving an assignment.
- Multiple sessions must not allocate versions or activate the server concurrently; the release queue and `flock` are mandatory.
- A later release must contain the current active commit and all already published `dev` commits. Never deploy an older `dev` snapshot over a newer release.
- If a session's change depends on another unfinished change, wait for that commit on `dev` or explicitly include and retest both scopes.
- A direct standalone issue must enter formal release automatically after its code change and required production build. Do not require local or online business tests; treat the original fix request as release authorization and do not wait for a separate `deploy` message.
- An Excel batch or explicitly grouped set must still release once after every included row passes local acceptance. Do not split that batch into row-by-row deployments unless the user explicitly changes the batch scope.

## 9. Controlled Divergent-Baseline Reconciliation

Use this procedure only when the fixed production worktree's active commit and remote `dev` have diverged, so no candidate can be both a descendant of the active production commit and a fast-forward of `dev`.

Only the unique release-coordination session may perform this procedure, and only after the user explicitly authorizes coordination and publication. The current issue session may become that coordinator when it verifies that no other session owns the active release slot; a separate conversation is not required. If another coordinator is active, the issue session must stop and hand off its tested candidate.

1. Fetch all remote refs and tags. Record the active production commit/tag/package, remote `dev`, merge base, commits unique to each side, working-tree status, and release queue.
2. Create a candidate directly from the active production commit. Reapply every still-required `dev`-only change and the new tested issue commit with cherry-pick or equivalent patch application. Do not omit changes merely because commit messages look duplicated.
3. Compare the candidate tree against both sides, audit every differing file, rerun affected tests and the production build, and confirm the candidate contains all currently served behavior plus the intended new change.
4. Push immutable safety refs before changing `dev`: one ref for the old remote `dev`, one for the active production baseline, and one for the tested reconciliation candidate. Verify all three hashes by `ls-remote`.
5. Re-read remote `dev`. If it changed after step 1, stop and rebuild the candidate. Otherwise, the coordinator may update `dev` exactly once with `git push --force-with-lease=refs/heads/dev:<recorded-old-dev> <candidate>:refs/heads/dev`. Never use plain `--force`.
6. Fetch and verify that remote `dev` equals the candidate and that the active production commit is its ancestor. Record the reconciliation in the release ledger, including all safety-ref hashes and the reason.
7. Resume the normal version reservation and locked activation workflow. Do not deploy until the normal commit/tag/package, artifact, service, health, and rollback checks pass.

This exception repairs branch ancestry only. It does not authorize discarding a unique commit, rewriting tags, deleting safety refs, bypassing the release queue or activation lock, overwriting the database, or skipping tests and build verification.
