import unittest
import tempfile
import os
import yaml
from parser.config_loader import (
    load_feeds_config,
    get_enabled_feeds,
    get_feeds_by_category,
    get_feeds_by_language,
    update_feed_status,
)
from types import SimpleNamespace


class TestConfigLoaderExtra(unittest.TestCase):
    def test_load_missing_file_raises(self):
        path = os.path.join(tempfile.gettempdir(), "definitely-not-exists-12345.yaml")
        if os.path.exists(path):
            os.remove(path)
        with self.assertRaises(FileNotFoundError):
            load_feeds_config(path)

    def test_load_and_filters_and_update(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = os.path.join(tmpdir, "feeds.yaml")

            data = {
                "feeds": {
                    "News": [
                        {
                            "name": "Sample Feed",
                            "url": "http://example.com/rss",
                            "language": "en",
                            "category": "News",
                            "country": "US",
                            "enabled": True,
                        }
                    ]
                },
                "settings": {"delay_between_feeds": 0.5},
            }

            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)

            config = load_feeds_config(cfg_path)
            enabled = get_enabled_feeds(config)
            self.assertEqual(len(enabled), 1)
            self.assertEqual(enabled[0].name, "Sample Feed")

            by_cat = get_feeds_by_category(config, "News")
            self.assertEqual(len(by_cat), 1)

            by_lang = get_feeds_by_language(config, "en")
            self.assertEqual(len(by_lang), 1)

            # Update the feed to disabled and ensure file on disk is updated
            update_feed_status(cfg_path, "Sample Feed", False)
            with open(cfg_path, "r", encoding="utf-8") as f:
                read = yaml.safe_load(f)
            self.assertFalse(read["feeds"]["News"][0]["enabled"])
