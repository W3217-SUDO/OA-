#!/usr/bin/env bash
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive DS_DOCKER_INSTALLATION=true DS_PLUGIN_INSTALLATION=false
fail() { printf 'ONLYOFFICE_PACKAGE_FAILED: %s\n' "$1" >&2; exit 1; }
deb=/tmp/onlyoffice.deb
[[ "$(sha256sum "$deb" | cut -d ' ' -f 1)" == 0860e68c4fecf429b4e13602a4a5ec6945e6ec9f0e9af9867ef0171845aa07df ]] || fail 'GitHub release asset SHA256 mismatch'
[[ "$(dpkg-deb -f "$deb" Version)" == 9.4.0-129 ]] || fail 'package version mismatch'
[[ "$(dpkg-deb -f "$deb" Package)" == onlyoffice-documentserver ]] || fail 'community package required'
[[ "$(dpkg-deb -f "$deb" Architecture)" == amd64 ]] || fail 'amd64 package required'
[[ "$(sha256sum /tmp/logrotate.deb | cut -d ' ' -f 1)" == e609ad80a9cec135b404a84f99d9d87bc304800eb212702444a985527edba70c ]] || fail 'Ubuntu logrotate SHA256 mismatch'
[[ "$(sha256sum /tmp/libpopt0.deb | cut -d ' ' -f 1)" == b3e7ea5192e57c847b77c527d51f5b8d4bce47988d2ba326a5c3193f6d173ded ]] || fail 'Ubuntu libpopt0 SHA256 mismatch'
[[ -x /usr/sbin/policy-rc.d && -f /app/ds/run-document-server.sh && -f /etc/init.d/supervisor ]] || fail 'official isolated dependency base is incomplete'
# 官方依赖层保留复制权限；在隔离容器内恢复正式镜像的可执行位。
chmod 755 /etc/init.d/supervisor /app/ds/run-document-server.sh
if /usr/sbin/policy-rc.d nginx start; then fail 'automatic service start must be blocked'; else [[ "$?" == 101 ]] || fail 'unexpected service policy'; fi

# 只在无网络、无宿主挂载的安装容器执行，完整运行已审查的官方 postinst。
dpkg -i /tmp/libpopt0.deb /tmp/logrotate.deb "$deb"
[[ "$(dpkg-query -W -f='${Version}' onlyoffice-documentserver)" == 9.4.0-129 ]] || fail 'installed version mismatch'
[[ -z "$(dpkg --audit)" ]] || fail 'dpkg audit found incomplete packages'
json=/var/www/onlyoffice/documentserver/npm/json
defaults=/etc/onlyoffice/documentserver/default.json
local_config=/etc/onlyoffice/documentserver/local.json
[[ -x "$json" && -r "$defaults" && -f "$local_config" ]] || fail 'official configuration tools missing'
schema_value="$("$json" -q -f "$defaults" services.CoAuthoring.autoAssembly.enable)"
[[ "$schema_value" == false || "$schema_value" == true ]] || fail '9.4 autoAssembly schema mismatch'
"$json" -q -f "$local_config" -I -e 'this.services.CoAuthoring.autoAssembly = {enable:false}; for (const key of Object.keys(this.services.CoAuthoring.secret || {})) {delete this.services.CoAuthoring.secret[key].string;}' >/dev/null
rm -f -- /etc/supervisor/conf.d/ds-adminpanel.conf
sed -i 's/,adminpanel//' /etc/supervisor/conf.d/ds.conf
sed "s/COMPANY_NAME/${COMPANY_NAME}/g" -i /etc/supervisor/conf.d/*.conf
documentserver-flush-cache.sh -r false
nginx -t
rm -- "$deb" /tmp/libpopt0.deb /tmp/logrotate.deb /tmp/sunhold-onlyoffice-install.sh
printf 'ONLYOFFICE_GITHUB_PACKAGE_INSTALLED: 9.4.0-129; network=none; services not started\n'
