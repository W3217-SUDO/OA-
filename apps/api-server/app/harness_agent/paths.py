"""区分 Python 文件访问和原生 SDK 模块解析所需的 Windows 路径表示。"""

import os
from pathlib import Path


def filesystem_path(path: Path) -> Path:
    resolved = path.resolve()
    value = str(resolved)
    if os.name != "nt" or value.startswith("\\\\?\\"):
        return resolved
    return Path("\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value)


def native_path(path: Path) -> str:
    value = str(path)
    if value.startswith("\\\\?\\UNC\\"):
        return "\\\\" + value[8:]
    return value[4:] if value.startswith("\\\\?\\") else value
