#!/usr/bin/env bash
set -Eeuo pipefail

fail() { printf 'ONLYOFFICE_CONFIG_FAILED: %s\n' "$1" >&2; exit 1; }
json=/var/www/onlyoffice/documentserver/npm/json
defaults=/etc/onlyoffice/documentserver/default.json
local_config=/etc/onlyoffice/documentserver/local.json
official_entrypoint=/app/ds/run-document-server.sh
[[ -x "$json" && -r "$defaults" && -f "$local_config" && -x "$official_entrypoint" ]] || fail 'official configuration tools or entrypoint are missing'
schema_value="$("$json" -q -f "$defaults" services.CoAuthoring.autoAssembly.enable)"
[[ "$schema_value" == 'false' || "$schema_value" == 'true' ]] || fail 'autoAssembly.enable is not supported by the installed schema'

verify() {
  [[ "$("$json" -q -f "$local_config" services.CoAuthoring.autoAssembly.enable)" == 'false' ]] || fail 'autoAssembly.enable must be explicitly false'
  printf 'ONLYOFFICE_CONFIG_VERIFIED: autoAssembly.enable=false\n'
}

if [[ "$#" -eq 1 && "$1" == 'verify' ]]; then
  verify
  [[ -n "${JWT_SECRET:-}" ]] || fail 'persistent JWT secret is missing'
  for key in browser request.inbox request.outbox; do
    [[ "$("$json" -q -f "$local_config" "services.CoAuthoring.token.enable.$key")" == true ]] || fail 'JWT must be enabled for browser, inbox and outbox'
  done
  for key in browser inbox outbox session; do
    [[ "$("$json" -q -f "$local_config" "services.CoAuthoring.secret.$key.string")" == "$JWT_SECRET" ]] || fail 'running JWT secret differs from private environment'
  done
  for key in inbox outbox; do
    [[ "$("$json" -q -f "$local_config" "services.CoAuthoring.token.$key.header")" == Authorization ]] || fail 'JWT header must be Authorization'
    [[ "$("$json" -q -f "$local_config" "services.CoAuthoring.token.$key.inBody")" == false ]] || fail 'JWT transport configuration mismatch'
  done
  printf 'ONLYOFFICE_SECURITY_VERIFIED: JWT enabled; persistent secret matches; Authorization header\n'
  exit 0
fi
[[ "$#" -eq 0 ]] || fail 'unsupported entrypoint argument'

# 使用官方 local.json 覆盖已存在的 schema，保留其他配置；每次启动均锁定此项。
"$json" -q -f "$local_config" -I -e 'this.services.CoAuthoring.autoAssembly = Object.assign({}, this.services.CoAuthoring.autoAssembly, {enable: false})' >/dev/null
verify
exec "$official_entrypoint"
