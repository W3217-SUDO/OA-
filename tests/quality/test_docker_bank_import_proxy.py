"""验证 Docker Web 对大文件银行流水导入保留独立代理限额。"""

import re
import unittest
from pathlib import Path

CONFIG = Path(__file__).resolve().parents[2] / "apps/admin-web/nginx.conf"
IMPORT_ROUTE = "/api/v1/finance/incoming-payments/import"


class DockerBankImportProxyTest(unittest.TestCase):
    def test_import_has_exact_large_upload_location(self):
        config = CONFIG.read_text(encoding="utf-8")
        exact = re.findall(rf"location = {re.escape(IMPORT_ROUTE)}\s*\{{([^}}]*)\}}", config, re.DOTALL)
        self.assertEqual(len(exact), 1)
        directives = exact[0]
        for value in (
            "client_max_body_size 101m;", "client_body_timeout 600s;",
            "proxy_pass http://api:8000;", "proxy_connect_timeout 5s;",
            "proxy_read_timeout 600s;", "proxy_send_timeout 600s;",
        ):
            self.assertIn(value, directives)
        generic = re.search(r"location /api/\s*\{([^}]*)\}", config, re.DOTALL)
        self.assertIsNotNone(generic)
        self.assertIn("client_max_body_size 21m;", config)
        self.assertIn("proxy_read_timeout 120s;", generic.group(1))


if __name__ == "__main__":
    unittest.main()
