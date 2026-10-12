# Production Authority Handover

The user retired Tencent on 2026-10-12. GitHub now owns source history; the actual production server owns the release queue, counter, allocation lock and activation lock. Do not reconnect to Tencent or use its outage as a required workflow step.

## Verify The Target

- Resolve the existing production SSH alias with `ssh -G oa-production`; verify its hostname and port against the latest operational receipt. The last verified target was `47.93.166.123`, public entry `https://huzhilawfirm.com`.
- Use a bounded direct SSH check. Do not route through the retired Tencent host. A banner-exchange timeout happens before authentication; changing the Git source does not repair that network/SSH failure. Read the physical NIC dynamically, excluding the VPN adapter. Git for Windows SSH with `-4 -o BindAddress=<LAN-IP>` was verified. Native OpenSSH source binding alone returned `Invalid argument`; explicitly select the physical-interface proxy below when using that client.
- Confirm effective systemd units, runtime interpreter, `current` manifest, public build metadata and health. In the established enterprise layout, activation moves `/opt/sunhold-oa/runtime/enterprise/current` to a new sealed package; it does not build or pull application source on production.

## Preserve The Queue

Before installing or invoking an allocator, compare the production `releases/queue.tsv` and `ledger.tsv` with the active runtime receipt, published GitHub tags and available local receipts of the retired authority. Export a small copy of the affected release metadata outside the deployment tree before modifying it; no business database backup is needed for this metadata-only handover.

Carry forward occupied, failed and pending versions with their exact commits and owners. Preserve the original assigned timestamp when available; if it was not retained, record `unknown` and put the handover time in a separate receipt. Never substitute a readiness or transfer timestamp for the missing original time. Do not mark a pending release successful merely because its tag exists. Do not delete another session's reservation, reuse its version or invent a new counter. If an earlier owner is still active, coordinate with that owner before activation; cross-chat messages require the user's authorization.

The last local observation before retirement was active `1.1.335` at `d7372dc3a6be64d056476899efa3da4484a412e0`, with `1.1.336` reserved by `D-mobile-pdf-render-20261012` and not activated. These are handover clues, not current facts: re-read GitHub and production before allocating. If the only available queue cannot account for an outstanding version, stop allocation and resolve that exact record rather than bypassing it.

## Physical Interface Connection

When using native Windows OpenSSH, the bundled Python TCP proxy selects the physical outgoing interface with Windows `IP_UNICAST_IF` and binds the same NIC's IPv4 address. OpenSSH still performs authentication and known-host verification. Invoke it explicitly; do not change global routes, disable the VPN or copy credentials. The interface option's index uses network byte order ([Microsoft socket documentation](https://learn.microsoft.com/en-us/windows/win32/winsock/ipproto-ip-socket-options)).

```powershell
$lan = @(Get-NetIPConfiguration | Where-Object {
    $_.InterfaceAlias -ne 'singbox_tun' -and $_.NetAdapter.Status -eq 'Up' -and
    $_.IPv4DefaultGateway -and $_.IPv4Address
})
if ($lan.Count -ne 1) { throw 'Physical interface is ambiguous' }
# $Python and $ProxyScript are resolved absolute paths, not machine constants.
$proxy = '"{0}" -B "{1}" --bind {2} --interface {3} --host %h --port %p' -f
    $Python, $ProxyScript, $lan[0].IPv4Address.IPAddress, $lan[0].InterfaceIndex
ssh -o "ProxyCommand=$proxy" -o BatchMode=yes -o ConnectTimeout=10 oa-production hostname
# Use the same -o ProxyCommand option for scp.
```

## Install The Production Allocator

Use the production server's scripts directory outside immutable runtime packages. Inspect any installed script and its callers before replacing it. Install `reserve_oa_version.sh`, `reassign_oa_version.sh`, `release_queue.py` and `github_release_refs.py` together, with hash verification. The wrappers preserve their original positional parameters and use:

- `OA_RELEASE_SOURCE_URL`: required, the previously verified GitHub remote URL; use configured authentication, never a token embedded in the URL.
- `OA_RELEASE_ROOT`: deployment root, default `/opt/sunhold-oa`.
- `OA_RELEASE_PYTHON`: required absolute executable path from the effective production runtime preflight.
- `OA_RELEASE_REFS_FILE`, `OA_RELEASE_REFS_SHA256`: required transferred reference JSON and independently verified SHA256.
- Production `locks/version-allocation.lock` and `releases/queue.tsv`.

Production GitHub reads were observed failing with a GnuTLS receive error. The selected transport is therefore an explicit workstation snapshot, not a network retry or fallback on production. The capture helper queries the exact configured GitHub HTTPS source using `git ls-remote` with a 45-second bound, reads `dev`, `main` and all occupied `v1.1.*` refs, and refuses to overwrite an existing snapshot file. It requires neither a source checkout on production nor copied GitHub credentials.

```powershell
& $Python -B "$SkillRoot/scripts/github_release_refs.py" capture `
    --repository $OwnedWorktree --remote github --output $UniqueRefsFile
# Record the returned SHA256/dev/time; verify Get-FileHash, then transfer.
```

On production the allocator requires the expected source URL, SHA256 and snapshot age no greater than 5 minutes, matching published `dev`, matching released baseline tag, complete occupied-version handover and no unresolved reservation. Refresh the snapshot immediately before allocation and before activation if its age exceeds the limit. Missing access, invalid/stale snapshots or incomplete queue metadata are explicit errors. All refs come from GitHub; no alternate source or empty-success response is allowed. Keep the snapshot and its hash in the off-server release receipt; remove the exact server staging path after use.

For a Codex conflict batch or separately authorized combined release, import each outstanding original reservation under the production metadata lock with its exact original target, owner, scope and timestamp before invoking the allocator. The coordinator alone may set `OA_RELEASE_CONSOLIDATE_VERSIONS=1.1.336` (or an exact comma-separated set) for already imported, assigned, tagged candidates. The allocator records `consolidates=` on the new reservation and leaves every original row untouched. After healthy activation, append `consolidated` to each original version, retaining its original commit and owner plus `consolidated_into=<new-version>`; on failure leave it unresolved. Never change an activating version into a consolidation candidate. Waiting in a Claude conflict queue is not consolidation and must not produce these records.

Normal releases follow the actual production queue serially. Push candidate branches normally to the verified GitHub remote before formal integration, and verify their exact remote SHAs. Concurrent development or another unfinished candidate does not justify combining releases or delaying ready work. Only when ready owners actually request the same formal release/version-switch slot may they agree to consolidate compatible, authorized, already-pushed Codex candidates; otherwise preserve the serial queue. Conflicts involving Claude remain serial. Explicit user instructions for a standalone release take precedence. Preserve reservations and active releases; no lock deletion, slot bypass or forced consolidation.

The current sole publisher holds the actual formal mutex for shared dev updates, version allocation and activation, runs existing exact-HEAD checks, builds locally, seals and activates one immutable package, verifies operation, records the receipt and fast-forwards GitHub main. After complete integration, delete the exact redundant temporary remote branches, fetch/prune and verify their absence; retain formal branches/tags and unfinished or still-needed candidates. Frozen releases exclude new changes.
