import unittest

from app.config import settings


class AuthConfigTests(unittest.TestCase):
    def test_default_core_identity_service_uses_integrated_platform_port(self):
        self.assertEqual(
            settings.core_internal_url.rstrip("/"),
            "http://127.0.0.1:8020",
        )
