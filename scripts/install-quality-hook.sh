#!/bin/sh
# 在 macOS/Linux 安装 OA pre-push 门禁，行为与 setup-local.ps1 的 Install-QualityPrePushHook 一致：
# 只安装本仓库默认 hooks，不改全局配置，也不覆盖用户原有 hook。
# 用法：sh scripts/install-quality-hook.sh [仓库根目录]
set -eu

fail() { echo "$1" >&2; exit 1; }

root=${1:-$(cd -- "$(dirname -- "$0")/.." && pwd -P)}
root=$(cd -- "$root" && pwd -P) || fail '无法确认当前项目 Git 根目录，拒绝安装 hook。'
top=$(git -C "$root" rev-parse --show-toplevel 2>/dev/null) || fail '无法确认当前项目 Git 根目录，拒绝安装 hook。'
[ "$(cd -- "$top" && pwd -P)" = "$root" ] || fail '无法确认当前项目 Git 根目录，拒绝安装 hook。'

status=0
git -C "$root" config --get core.hooksPath >/dev/null 2>&1 || status=$?
case $status in
    0) fail '已有 core.hooksPath 配置，请由其维护者集成 OA pre-push；本脚本不会覆盖。' ;;
    1) ;;
    *) fail '无法读取 Git hooksPath。' ;;
esac

hooks=$(git -C "$root" rev-parse --git-path hooks) || fail '无法定位当前仓库的 hooks 目录。'
case $hooks in /*) ;; *) hooks="$root/$hooks" ;; esac
[ ! -L "$hooks" ] || fail '默认 hooks 目录是链接，拒绝修改未知外部目录。'

source="$root/.githooks/pre-push"
destination="$hooks/pre-push"
[ -f "$source" ] || fail '缺少仓库 pre-push hook。'

# Git 的自动换行可能把仓库文件转为 CRLF；shell hook 必须安装为无 BOM 的 LF。
staged=$(mktemp "${TMPDIR:-/tmp}/oa-pre-push-XXXXXX")
trap 'rm -f "$staged"' EXIT
awk '{ sub(/\r$/, ""); print }' "$source" > "$staged"
[ "$(sed -n 1p "$staged")" = '#!/bin/sh' ] && [ "$(sed -n 2p "$staged")" = '# OA_MANAGED_PRE_PUSH_V1' ] \
    || fail '仓库 pre-push 缺少受管理模板标记。'

if [ -e "$destination" ] || [ -L "$destination" ]; then
    [ ! -L "$destination" ] || fail '已有 pre-push 是链接，拒绝覆盖。'
    if ! cmp -s "$staged" "$destination"; then
        [ "$(sed -n 2p "$destination")" = '# OA_MANAGED_PRE_PUSH_V1' ] && [ "$(sed -n 1p "$destination")" = '#!/bin/sh' ] \
            || fail '已有外来 pre-push hook，请由其维护者集成；本脚本不会覆盖。'
        cat "$staged" > "$destination"
    fi
else
    mkdir -p "$hooks"
    cat "$staged" > "$destination"
fi

chmod u+x "$destination" || fail '无法设置 pre-push 可执行权限。'
[ -x "$destination" ] || fail 'pre-push 不具备可执行权限。'
echo "已安装 OA pre-push：${destination}；推送 dev/main 必须设置 OA_QUALITY_PYTHON 与 OA_QUALITY_NODE；OA_QUALITY_JOBS 可覆盖并发数，默认按 CPU 自适应（上限 10）。"
