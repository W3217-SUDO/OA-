"""PDF、WPS、旧版 Word 转成 Word（.docx）（陶国南 11-01：免费法规原文下载后整理成 Word）。

PDF 取出文字后按段落重新排版，章、节、条另起一段；WPS、.doc 等用服务器上的 LibreOffice 转换。
原文件不变，转出的是一个新文件。扫描件（只有图片、没有文字）不支持。
"""
import asyncio
import re
from pathlib import Path

from fastapi import HTTPException

WORD_CONVERTIBLE_SUFFIXES = {".pdf", ".wps", ".doc", ".rtf", ".odt", ".wpt", ".dot"}
_HEADING = re.compile(r"^(第[一二三四五六七八九十百千零〇两\d]+[编章节条]|目\s*录|附\s*则|总\s*则)")
_PAGE_MARK = re.compile(r"^[-—－\s]*\d{1,4}[-—－\s]*$|^第\s*\d+\s*页")
_SENTENCE_END = "。；：！？」』）)"


def word_name(name: str) -> str:
    return str(Path(name).with_suffix(".docx"))


def _pdf_lines(content: bytes) -> list[str]:
    import pypdfium2 as pdfium

    from app.pdf_runtime import serialized_pdfium

    @serialized_pdfium
    def extract():
        document = pdfium.PdfDocument(content)
        try:
            lines = []
            for index in range(len(document)):
                page = document[index]
                try:
                    text_page = page.get_textpage()
                    try:
                        lines.extend((text_page.get_text_range() or "").splitlines())
                    finally:
                        text_page.close()
                finally:
                    page.close()
            return lines
        finally:
            document.close()

    return extract()


def rebuild_paragraphs(lines: list[str]) -> str:
    """把 PDF 里按版面断开的行接回段落：句末标点或下一行是章节条开头时才分段，去掉页码行。"""
    paragraphs: list[str] = []
    for raw in lines:
        line = raw.strip().replace("　", " ").strip()
        if not line or _PAGE_MARK.match(line):
            continue
        if not paragraphs or _HEADING.match(line) or paragraphs[-1].endswith(tuple(_SENTENCE_END)) or len(paragraphs[-1]) < 16:
            paragraphs.append(line)
        else:
            paragraphs[-1] += line
    return "\n\n".join(paragraphs)


async def convert_to_word(name: str, content: bytes) -> bytes:
    from app.core.pdf_conversion import _soffice
    from app.core.storage import _docx_bytes

    suffix = Path(name).suffix.lower()
    if suffix not in WORD_CONVERTIBLE_SUFFIXES:
        raise HTTPException(422, "只有 PDF、WPS 和旧版 Word（.doc）文件可以转成 Word")
    if suffix != ".pdf":
        return await _soffice(content, suffix, "docx")
    try:
        lines = await asyncio.to_thread(_pdf_lines, content)
    except Exception:
        raise HTTPException(422, "PDF 文件打不开，可能已损坏或加密") from None
    text = rebuild_paragraphs(lines)
    if len(text.strip()) < 20:
        raise HTTPException(422, "这个 PDF 是扫描件（只有图片、没有文字），暂不能转成 Word")
    return _docx_bytes(Path(name).stem, text)


async def _require_owner(item_owner_id, identity, db):
    from sqlalchemy import select

    from app.models import User

    owner_id = await db.scalar(select(User.id).where(User.username == identity["username"]))
    if owner_id is None or item_owner_id != owner_id:
        raise HTTPException(403, "只能转换本人的文件")


async def _save_word(identity, db, *, name, content, conversation_id=None):
    from app.core.constants import WORD_DOCUMENT_CONTENT_TYPE
    from app.core.generated_file_storage import save_generated_file

    word = await convert_to_word(name, content)
    saved = await save_generated_file(db, identity, name=word_name(name), content=word, content_type=WORD_DOCUMENT_CONTENT_TYPE,
                                      source_kind="personal_document", conversation_id=conversation_id)
    return saved["file"]


async def personal_file_to_word(file_id, identity, db):
    """个人空间里的 PDF/WPS/.doc 转成 Word，存为个人空间的新文件。"""
    from app.areas.personal_agent.ai_space_service import space_file_bytes

    item, content = await space_file_bytes(file_id, identity, db)
    await _require_owner(item["owner_user_id"], identity, db)
    await db.rollback()
    return await _save_word(identity, db, name=item["name"], content=content, conversation_id=item.get("conversation_id"))


async def material_to_word(attachment_id, identity, db, *, conversation_id=None):
    """对话里本人上传的材料（如从国家法律法规数据库下载的 PDF/WPS）转成 Word，存到个人空间。"""
    from app.areas.personal_agent.materials import PERSONAL_MATERIAL_CATEGORY
    from app.core.oss_attachments import oss_attachment_bytes, oss_attachment_location
    from app.core.storage import _attachment_storage_path
    from app.models import FileAttachment

    item = await db.get(FileAttachment, attachment_id)
    if item is None or item.uploader != identity["username"] or item.category != PERSONAL_MATERIAL_CATEGORY:
        raise HTTPException(404, "没有找到你上传的这份材料")
    if item.size and item.size > 20 * 1024 * 1024:
        raise HTTPException(413, "文件超过 20MB，不能转换")
    path = _attachment_storage_path(item)
    if path is not None and path.is_file():
        content = await asyncio.to_thread(path.read_bytes)
    elif oss_attachment_location(item) is not None:
        content = await oss_attachment_bytes(item)
    else:
        raise HTTPException(404, "材料文件已不可读取，请重新上传")
    name = item.original_name
    await db.rollback()
    return await _save_word(identity, db, name=name, content=content, conversation_id=conversation_id)
