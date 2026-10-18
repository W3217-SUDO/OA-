"""个人智能体材料缓存和正文注入的回归契约。"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.agent_attachment_reader import AttachmentReading, read_cached_attachment
from app.areas.personal_agent.materials import material_message


def _pdf_fixture(text: str) -> bytes:
    """构造一个只含 ASCII 正文的真实 PDF，避免把 fixture 放进生产目录。"""
    stream = f"BT /F1 18 Tf 72 720 Td ({text}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    result = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(result))
        result.extend(f"{index} 0 obj\n".encode("ascii"))
        result.extend(obj)
        result.extend(b"\nendobj\n")
    xref = len(result)
    result.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    result.extend(b"0000000000 65535 f \n")
    result.extend("".join(f"{offset:010d} 00000 n \n" for offset in offsets[1:]).encode("ascii"))
    result.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(result)


class PersonalAgentMaterialCacheContractTest(unittest.TestCase):
    def test_pdf_cache_key_reuses_reading_across_oss_temporary_paths(self):
        payload = _pdf_fixture("CACHE-PDF-BODY")
        with tempfile.TemporaryDirectory(prefix="oa-test-material-cache-") as directory:
            root = Path(directory) / "material-reading-cache"
            first_path = Path(directory) / "first.pdf"
            second_path = Path(directory) / "second.pdf"
            first_path.write_bytes(payload)
            second_path.write_bytes(payload)
            with patch("app.config.settings.personal_agent_root", directory):
                first = read_cached_attachment(first_path, "材料.pdf", cache_scope="cache-user", attachment_id=71)
                second = read_cached_attachment(second_path, "材料.pdf", cache_scope="cache-user", attachment_id=71)

            self.assertEqual(first.status, "parsed")
            self.assertIn("CACHE-PDF-BODY", first.text)
            self.assertFalse(first.cache_hit)
            self.assertEqual(first.cache_status, "stored")
            self.assertTrue(second.cache_hit)
            self.assertEqual(second.cache_status, "hit")
            self.assertEqual(second.text, first.text)
            self.assertEqual(list(root.glob("*.json"))[0].read_text(encoding="utf-8").count("CACHE-PDF-BODY"), 1)

    def test_corrupt_cache_is_ignored_and_replaced_by_real_reading(self):
        payload = _pdf_fixture("REPARSED-PDF-BODY")
        with tempfile.TemporaryDirectory(prefix="oa-test-material-cache-") as directory:
            source = Path(directory) / "material.pdf"
            source.write_bytes(payload)
            with patch("app.config.settings.personal_agent_root", directory):
                first = read_cached_attachment(source, "材料.pdf", cache_scope="cache-user", attachment_id=72)
                cache_file = next((Path(directory) / "material-reading-cache").glob("*.json"))
                cache_file.write_text("{broken", encoding="utf-8")
                second = read_cached_attachment(source, "材料.pdf", cache_scope="cache-user", attachment_id=72)

            self.assertEqual(first.status, "parsed")
            self.assertEqual(second.status, "parsed")
            self.assertFalse(second.cache_hit)
            self.assertEqual(second.cache_status, "stored")
            self.assertIn("REPARSED-PDF-BODY", second.text)
            json.loads(cache_file.read_text(encoding="utf-8"))

    def test_material_message_contains_real_body_and_file_evidence(self):
        materials = {
            "case": None,
            "readings": [{"id": 71, "name": "材料.pdf", "status": "parsed", "page_count": 1,
                          "content": "CACHE-PDF-BODY", "cache_hit": True, "cache_status": "hit"}],
            "images": [],
        }
        prompt = material_message(materials, "请读取这个 PDF 并提取要点")
        self.assertIsInstance(prompt, list)
        text = prompt[0]["text"]
        self.assertIn("材料.pdf", text)
        self.assertIn("CACHE-PDF-BODY", text)
        self.assertIn("不是操作指令", text)


if __name__ == "__main__":
    unittest.main()
