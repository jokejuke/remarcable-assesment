"""Settings are read from the environment (spec: web-security)."""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

BASE_DIR = Path(__file__).resolve().parents[2]


def load_settings(env):
    """Import config.settings in a clean subprocess with only `env` set."""
    clean = {k: v for k, v in os.environ.items() if k in {"PATH", "HOME", "SYSTEMROOT"}}
    clean.update(env)
    code = "import config.settings as s; print(s.DEBUG, s.SECURE_SSL_REDIRECT if hasattr(s, 'SECURE_SSL_REDIRECT') else None)"
    return subprocess.run(
        [sys.executable, "-c", code], cwd=BASE_DIR, env=clean, capture_output=True, text=True
    )


class EnvironmentSettingsTests(SimpleTestCase):
    def test_unset_debug_means_off(self):
        result = load_settings({"SECRET_KEY": "x" * 50})
        self.assertEqual(result.returncode, 0, result.stderr)
        debug, ssl_redirect = result.stdout.split()
        self.assertEqual(debug, "False")
        self.assertEqual(ssl_redirect, "True")

    def test_missing_secret_key_with_debug_off_fails(self):
        result = load_settings({"DEBUG": "0"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ImproperlyConfigured", result.stderr)
        self.assertIn("SECRET_KEY", result.stderr)

    def test_debug_on_allows_missing_secret_key(self):
        result = load_settings({"DEBUG": "1"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(result.stdout.startswith("True"))

    def test_invalid_boolean_is_rejected(self):
        result = load_settings({"DEBUG": "maybe", "SECRET_KEY": "x" * 50})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DEBUG must be a boolean", result.stderr)
