import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import site_logins  # noqa: E402
from application_launcher import external_browser_command, external_firefox_profile  # noqa: E402


class SiteLoginStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "cfg", "site-logins.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_is_private_and_public_view_hides_password(self):
        site_logins.update_login(self.path, "default", "khan", username="beni@example.com", password="s3cret!")
        mode = stat.S_IMODE(os.stat(self.path).st_mode)
        self.assertEqual(mode, 0o600)
        view = site_logins.public_logins(self.path, "default")
        self.assertEqual([v["id"] for v in view], ["khan", "teachyourmonster"])
        self.assertEqual(view[0]["username"], "beni@example.com")
        self.assertTrue(view[0]["hasPassword"])
        self.assertNotIn("s3cret!", json.dumps(view))
        self.assertFalse(site_logins.public_logins(self.path, "outra")[0]["hasPassword"])

    def test_empty_password_keeps_saved_one(self):
        site_logins.update_login(self.path, "default", "khan", username="a@example.com", password="one")
        site_logins.update_login(self.path, "default", "khan", username="b@example.com", password=None)
        login = site_logins.get_login(self.path, "default", "khan")
        self.assertEqual(login, {"username": "b@example.com", "password": "one"})

    def test_requires_password_first_time_and_known_site(self):
        with self.assertRaises(ValueError):
            site_logins.update_login(self.path, "default", "khan", username="a@example.com")
        with self.assertRaises(ValueError):
            site_logins.update_login(self.path, "default", "nada", username="a", password="b")

    def test_remove(self):
        site_logins.update_login(self.path, "default", "khan", username="a@example.com", password="x")
        site_logins.update_login(self.path, "default", "khan", remove=True)
        self.assertIsNone(site_logins.get_login(self.path, "default", "khan"))

    def test_site_for_url(self):
        self.assertEqual(site_logins.site_for_url("https://pt.khanacademy.org/"), "khan")
        self.assertEqual(site_logins.site_for_url("https://www.khanacademy.org/math"), "khan")
        self.assertIsNone(site_logins.site_for_url("https://evilkhanacademy.org/"))
        self.assertIsNone(site_logins.site_for_url("https://kleki.com/"))
        self.assertEqual(site_logins.site_for_url("https://www.teachyourmonster.org/account/play"), "teachyourmonster")


class ExternalProfileTest(unittest.TestCase):
    def test_profiles_are_separate_and_seeded_without_cookies(self):
        with tempfile.TemporaryDirectory() as root:
            base = Path(root) / "external-firefox-profile"
            (base / "extensions").mkdir(parents=True)
            (base / "extensions" / "ublock.xpi").write_text("x")
            (base / "user.js").write_text('user_pref("a", 1);\n')
            (base / "cookies.sqlite").write_text("segredo")
            self.assertEqual(external_firefox_profile(root, "default"), str(base))
            other = Path(external_firefox_profile(root, "child-123"))
            self.assertEqual(other.name, "external-firefox-profile-child-123")
            self.assertTrue((other / "extensions" / "ublock.xpi").exists())
            self.assertTrue((other / "user.js").exists())
            self.assertFalse((other / "cookies.sqlite").exists())

    def test_marionette_only_when_asked(self):
        with tempfile.TemporaryDirectory() as root:
            plain = external_browser_command("firefox", "https://x.org/", root, profile_id="default")
            self.assertNotIn("--marionette", plain)
            driven = external_browser_command(
                "firefox", "https://pt.khanacademy.org/", root, profile_id="default", marionette_port=28290,
            )
            self.assertIn("--marionette", driven)
            prefs = (Path(root) / "external-firefox-profile" / "user.js").read_text()
            self.assertIn('user_pref("marionette.port", 28290);', prefs)


if __name__ == "__main__":
    unittest.main()
