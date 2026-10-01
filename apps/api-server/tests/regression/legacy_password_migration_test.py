import hashlib
import unittest

from app.security import hash_password, password_needs_rehash, verify_password


class LegacyPasswordMigrationTest(unittest.TestCase):
    def test_legacy_md5_password_is_verified_without_exposing_plaintext(self):
        password = "Legacy-Password-123"
        encoded = f"legacy-md5${hashlib.md5(password.encode('utf-8')).hexdigest()}"

        self.assertTrue(verify_password(password, encoded))
        self.assertFalse(verify_password("wrong-password", encoded))
        self.assertTrue(password_needs_rehash(encoded))

    def test_argon_passwords_remain_compatible(self):
        encoded = hash_password("Current-Password-123")

        self.assertTrue(verify_password("Current-Password-123", encoded))
        self.assertFalse(password_needs_rehash(encoded))

    def test_malformed_legacy_digest_is_rejected(self):
        self.assertFalse(verify_password("anything", "legacy-md5$not-a-digest"))


if __name__ == "__main__":
    unittest.main()
