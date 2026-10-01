"""Regression coverage for 8.31 row 6 role permission payload size."""

import unittest

from app.main import JobRolePermissionUpdate


class OrganizationRolePermissionScaleRow6Test(unittest.TestCase):
    def test_complete_permission_tree_can_exceed_legacy_two_hundred_item_limit(self):
        permissions = [f"menu-or-action-{index}" for index in range(395)]

        payload = JobRolePermissionUpdate(permissions=permissions)

        self.assertEqual(payload.permissions, permissions)


if __name__ == "__main__":
    unittest.main()
