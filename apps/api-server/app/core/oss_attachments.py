"""识别已核实的 OSS 附件路径，不将远程对象当作本地文件。"""

import re

from fastapi import HTTPException


def oss_attachment_location(item) -> tuple[str, str] | None:
    path = str(item.path or "")
    if not path.startswith("oss://"):
        return None
    bucket, separator, key = path.removeprefix("oss://").partition("/")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]", bucket) or not separator or not key:
        raise HTTPException(status_code=409, detail="附件 OSS 路径无效，请核对迁移记录")
    return bucket, key


def require_oss_attachment_download(item) -> None:
    if oss_attachment_location(item) is not None:
        raise HTTPException(
            status_code=503,
            detail="附件已关联 OSS 路径；尚未配置签名读取凭据，暂不能下载或预览",
        )
