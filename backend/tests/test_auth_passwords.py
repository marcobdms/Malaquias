import unittest

import bcrypt

from app.auth import PASSWORD_HASH_PREFIX, hash_password, verify_password


class AuthPasswordTests(unittest.TestCase):
    def test_password_hash_roundtrip(self):
        hashed = hash_password("Marco23.")

        self.assertTrue(hashed.startswith(PASSWORD_HASH_PREFIX))
        self.assertTrue(verify_password("Marco23.", hashed))
        self.assertFalse(verify_password("wrong-password", hashed))

    def test_long_password_does_not_raise_or_truncate(self):
        password = "clave-larga-" * 20
        hashed = hash_password(password)

        self.assertTrue(verify_password(password, hashed))
        self.assertFalse(verify_password(password + "x", hashed))

    def test_legacy_bcrypt_hashes_still_verify(self):
        password = "legacy-password"
        legacy_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        self.assertTrue(verify_password(password, legacy_hash))
        self.assertFalse(verify_password("wrong-password", legacy_hash))


if __name__ == "__main__":
    unittest.main()
