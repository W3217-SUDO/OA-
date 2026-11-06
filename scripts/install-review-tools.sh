#!/bin/sh
# 安装代码审查报告用的工具（mypy、vulture、coverage）。
# 单独一个环境：门禁会校验自己的 Python 环境没有变化，工具不能装进去。没装也能推送，只是报告少几项。
# 用法：sh scripts/install-review-tools.sh
set -eu
root=$(cd -- "$(dirname -- "$0")/.." && pwd -P)
python=${OA_QUALITY_PYTHON:-python3.12}
target="$HOME/.local/share/oa/review-tools"
"$python" -m venv "$target"
"$target/bin/python" -m pip install --quiet --require-hashes -r "$root/requirements-review.lock"
echo "审查工具已装到 $target"
