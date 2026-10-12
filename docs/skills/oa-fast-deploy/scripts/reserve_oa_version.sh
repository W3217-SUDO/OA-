#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 3 ]] || { echo "usage: $0 <target-commit> <session-id> <scope>" >&2; exit 2; }
: "${OA_RELEASE_PYTHON:?set the verified absolute production Python path}"
[[ $OA_RELEASE_PYTHON == /* && -x $OA_RELEASE_PYTHON ]] || exit 2
script_dir=$(cd -- "$(dirname -- "$0")" && pwd)
export PYTHONDONTWRITEBYTECODE=1
exec "$OA_RELEASE_PYTHON" -B "$script_dir/release_queue.py" reserve "$@"
