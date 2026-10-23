"""法院收文文件存储：放在 OSS 独立目录“法院收文/”，按“送达原件 / 已入库”分目录，写元数据并用标签标记入库状态。

OSS 未配置（本地开发、测试）时退回本机附件目录，接口行为一致。
"""

from datetime import datetime
from pathlib import Path
import re
from uuid import uuid4

from starlette.concurrency import run_in_threadpool

from app.config import settings
from app.core.constants import UPLOAD_ROOT
from app.models import FileAttachment

SOURCE_DIR = "送达原件"
RECEIVED_DIR = "已入库"
_UNSAFE = re.compile(r'[\\:*?"<>|\x00-\x1f]+')


def oss_enabled() -> bool:
    return bool(settings.ai_oss_bucket.strip() and settings.ai_oss_credentials_file.strip() and settings.court_intake_oss_prefix.strip())


def _segment(value: object) -> str:
    return _UNSAFE.sub("_", str(value or "").replace("/", "／")).strip(" .") or "未命名"


def object_key(*parts: object) -> str:
    return "/".join([settings.court_intake_oss_prefix.strip().strip("/"), *(_segment(part) for part in parts)])


async def store(content: bytes, *, key: str, filename: str, content_type: str,
                metadata: dict[str, object], tags: dict[str, object]) -> tuple[str, str]:
    """保存文件，返回 (附件 path, stored_name)。OSS 上禁止覆盖，同名已存在时换一个对象名。"""
    suffix = Path(filename).suffix.lower()
    if not oss_enabled():
        stored_name = f"{uuid4().hex}{suffix}"
        target = UPLOAD_ROOT / stored_name
        await run_in_threadpool(target.write_bytes, content)
        return str(target), stored_name
    from app.core.oss_attachments import oss_put_object
    bucket = settings.ai_oss_bucket.strip()
    for attempt in range(3):
        candidate = key if attempt == 0 else f"{key.rsplit('.', 1)[0]}-{uuid4().hex[:8]}{suffix}"
        created = await oss_put_object(bucket, candidate, content, content_type,
                                       credentials_file=settings.ai_oss_credentials_file, endpoint=settings.ai_oss_endpoint,
                                       metadata={**metadata, "stored-at": datetime.now().isoformat(timespec="seconds")}, tags=tags)
        if created:
            return f"oss://{bucket}/{candidate}", f"oss-{uuid4().hex}{suffix}"
    raise RuntimeError("OSS 对象名连续冲突")


async def read_bytes(item: FileAttachment) -> bytes:
    from app.core.oss_attachments import oss_attachment_bytes, oss_attachment_location
    from app.core.storage import _attachment_storage_path
    if oss_attachment_location(item) is not None:
        return await oss_attachment_bytes(item)
    path = _attachment_storage_path(item)
    if path is None:
        raise FileNotFoundError(item.original_name)
    return await run_in_threadpool(path.read_bytes)


async def mark(item: FileAttachment, tags: dict[str, object]) -> None:
    """更新 OSS 对象标签；本机文件没有标签，忽略。"""
    from app.core.oss_attachments import oss_attachment_location, oss_put_tags
    location = oss_attachment_location(item)
    if location is None or not oss_enabled():
        return
    await oss_put_tags(*location, tags, credentials_file=settings.ai_oss_credentials_file, endpoint=settings.ai_oss_endpoint)
