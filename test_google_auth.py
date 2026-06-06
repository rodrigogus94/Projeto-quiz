import unittest
from pathlib import Path

from google_auth import DEFAULT_CLIENT_SECRET_FILE, get_google_oauth_config, load_oauth_from_json


class TestGoogleAuthConfig(unittest.TestCase):
    def test_load_json_from_project(self):
        data = load_oauth_from_json(DEFAULT_CLIENT_SECRET_FILE)
        self.assertIsNotNone(data)
        self.assertIn("apps.googleusercontent.com", data["client_id"])
        self.assertTrue(data["client_secret"].startswith("GOCSPX-"))
        self.assertIn(
            "projeto-quiz-rbbnbrjptykghaaz7bdwwf.streamlit.app",
            data["redirect_uris"][0],
        )

    def test_get_config_merges_json(self):
        cfg = get_google_oauth_config()
        self.assertIn("apps.googleusercontent.com", cfg["client_id"])
        self.assertTrue(cfg["client_secret"])
        self.assertTrue(cfg["redirect_uri"])


if __name__ == "__main__":
    unittest.main()
