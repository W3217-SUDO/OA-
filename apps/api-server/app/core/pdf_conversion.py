"""Word、Markdown、文本转 PDF（陶威 11-01 同意在服务器装 LibreOffice）。

转换在一次性临时目录里进行，限并发和时间，低优先级运行，不影响线上请求。
"""
import asyncio
import shutil
import tempfile
from pathlib import Path

from fastapi import HTTPException

PDF_CONVERTIBLE_SUFFIXES = {".docx", ".md", ".txt", ".xlsx"}
PDF_CONTENT_TYPE = "application/pdf"
_SLOTS = asyncio.Semaphore(2)
_TIMEOUT_SECONDS = 60


def pdf_name(name: str) -> str:
    return str(Path(name).with_suffix(".pdf"))


async def _soffice(content: bytes, suffix: str, target: str) -> bytes:
    soffice = shutil.which("soffice")
    if not soffice:
        raise HTTPException(503, "服务器还没有安装文档转换工具")
    async with _SLOTS:
        with tempfile.TemporaryDirectory(prefix="oa-convert-") as work:
            source = Path(work) / ("source" + suffix)
            source.write_bytes(content)
            process = await asyncio.create_subprocess_exec(
                "nice", "-n", "10", soffice, "--headless", "--norestore", "--nologo",
                f"-env:UserInstallation=file://{work}/profile", "--convert-to", target, "--outdir", work, str(source),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                env={"HOME": work, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
            try:
                await asyncio.wait_for(process.wait(), _TIMEOUT_SECONDS)
            except TimeoutError:
                process.kill()
                await process.wait()
                raise HTTPException(504, "文档转换超时，请稍后重试") from None
            output = Path(work) / ("source." + target)
            if process.returncode != 0 or not output.is_file():
                raise HTTPException(502, "文档转换没有成功，请稍后重试")
            return output.read_bytes()


async def convert_to_pdf(name: str, content: bytes) -> bytes:
    from app.core.storage import _docx_bytes

    suffix = Path(name).suffix.lower()
    if suffix not in PDF_CONVERTIBLE_SUFFIXES:
        raise HTTPException(422, "只有 Word、Excel、Markdown 和文本文件可以转成 PDF")
    soffice = shutil.which("soffice")
    if not soffice:
        raise HTTPException(503, "服务器还没有安装 PDF 转换工具")
    if suffix in {".md", ".txt"}:
        # Markdown 和文本先排成 Word，标题、列表、加粗与在线保存的 Word 一致。
        content, suffix = _docx_bytes(Path(name).stem, content.decode("utf-8", errors="replace")), ".docx"
    async with _SLOTS:
        with tempfile.TemporaryDirectory(prefix="oa-pdf-") as work:
            source = Path(work) / ("source" + suffix)
            source.write_bytes(content)
            process = await asyncio.create_subprocess_exec(
                "nice", "-n", "10", soffice, "--headless", "--norestore", "--nologo",
                f"-env:UserInstallation=file://{work}/profile", "--convert-to", "pdf", "--outdir", work, str(source),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                env={"HOME": work, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
            try:
                await asyncio.wait_for(process.wait(), _TIMEOUT_SECONDS)
            except TimeoutError:
                process.kill()
                await process.wait()
                raise HTTPException(504, "PDF 转换超时，请稍后重试") from None
            output = Path(work) / "source.pdf"
            if process.returncode != 0 or not output.is_file():
                raise HTTPException(502, "PDF 转换没有成功，请稍后重试或下载 Word")
            return output.read_bytes()


async def convert_many_to_pdf(files: dict[str, bytes], suffix: str) -> dict[str, bytes] | None:
    """一批同类文件一次 LibreOffice 转成 PDF（结算单压缩包里每案一张个案结算表，501225）。

    返回 {原名: PDF}；没转成的不在结果里，由调用方说明，不影响原文件下载。服务器没装转换工具时返回 None。"""
    soffice = shutil.which("soffice")
    if not soffice:
        return None
    if not files:
        return {}
    async with _SLOTS:
        with tempfile.TemporaryDirectory(prefix="oa-pdf-batch-") as work:
            names = {}
            for index, (name, content) in enumerate(files.items()):
                source = Path(work) / f"f{index}{suffix}"
                source.write_bytes(content)
                names[source.stem] = name
            process = await asyncio.create_subprocess_exec(
                "nice", "-n", "10", soffice, "--headless", "--norestore", "--nologo",
                f"-env:UserInstallation=file://{work}/profile", "--convert-to", "pdf", "--outdir", work,
                *(str(Path(work) / f"{stem}{suffix}") for stem in names),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
                env={"HOME": work, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
            )
            try:
                await asyncio.wait_for(process.wait(), _TIMEOUT_SECONDS + 2 * len(files))
            except TimeoutError:
                process.kill()
                await process.wait()
            return {name: (Path(work) / f"{stem}.pdf").read_bytes() for stem, name in names.items() if (Path(work) / f"{stem}.pdf").is_file()}
