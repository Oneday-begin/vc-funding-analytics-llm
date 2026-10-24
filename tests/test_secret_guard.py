"""Synthetic detector fixtures are assembled in memory, never stored as real keys."""
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("secret_guard", Path(__file__).parents[1] / "scripts" / "check_secrets.py")
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class SecretGuardTests(unittest.TestCase):
    def test_provider_key_pattern_is_detected_without_echoing_value(self):
        value = b"gsk_" + b"A" * 32
        matches = guard.inspect_content(value, set())
        self.assertTrue(any(rule == "Groq API key" for rule, _ in matches))
        self.assertNotIn(value.decode(), str(matches))

    def test_private_local_value_is_detected(self):
        value = b"private-" + b"fixture" * 3
        self.assertIn(("Exact match to a local private value", 2), guard.inspect_content(b"first\n" + value, {value}))

    def test_placeholder_and_runtime_url_are_not_credentials(self):
        data = b'DB_PASSWORD="your_mysql_password_here"\nurl="mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}"'
        self.assertEqual(guard.inspect_content(data, set()), [])

    def test_dummy_key_with_spaces_is_a_fixture(self):
        self.assertEqual(guard.inspect_content(b'{"GROQ_API_KEY": "  test-key  "}', set()), [])

    def test_private_files_are_blocked_but_examples_are_allowed(self):
        for path in (".env", ".env.production", "private/server.pem", ".aws/credentials", "cloud.db"):
            self.assertTrue(guard.forbidden_path(path), path)
        self.assertFalse(guard.forbidden_path(".env.example"))

    def test_compressed_content_is_scanned(self):
        import gzip
        value = b"gsk_" + b"B" * 32
        self.assertTrue(guard.inspect_content(gzip.compress(value), set()))


if __name__ == "__main__":
    unittest.main()
