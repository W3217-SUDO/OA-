"""BUG20261031002：部门旧审计来源对不上时，部门列表照常返回，只是不显示旧来源。"""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.core import department_audit


class DepartmentActorSourcesFallbackTest(unittest.TestCase):
    def test_conflict_returns_no_sources_instead_of_409(self):
        strict = AsyncMock(side_effect=HTTPException(status_code=409, detail="未匹配部门的已存旧主键不一致，旧审计来源冲突"))
        with patch.object(department_audit, "_strict_department_actor_sources", strict):
            self.assertEqual(asyncio.run(department_audit._department_actor_sources([], None)), {})

    def test_sources_pass_through(self):
        strict = AsyncMock(return_value={1: {"created_by": {"source": "x"}}})
        with patch.object(department_audit, "_strict_department_actor_sources", strict):
            self.assertEqual(asyncio.run(department_audit._department_actor_sources([], None)), {1: {"created_by": {"source": "x"}}})


if __name__ == "__main__":
    unittest.main()
