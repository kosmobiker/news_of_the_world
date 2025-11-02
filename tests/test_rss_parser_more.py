import unittest
from types import SimpleNamespace
import parser.rss_parser as rss
import builtins
from unittest.mock import patch


class FakeStatus:
    def __init__(self):
        self.feed_name = ""
        self.feed_url = ""
        self.is_active = True
        self.articles_count = 0
        self.last_parsed_at = None
        self.last_success_at = None


class FakeDB:
    def __init__(self):
        self.status = None
        self.committed = False
        self.rolled_back = False
        self.added = []

    def query(self, *args, **kwargs):
        """A flexible FakeDB.query that accepts various call patterns used in production code.

        It supports:
        - query(Model).filter_by(...).first()
        - query(func.count(Model.id)).scalar()
        - query(Model.field, func.count(Model.id)).group_by(...).all()
        """
        db = self

        class Q:
            def filter_by(self, **kw):
                class F:
                    def first(inner):
                        return db.status

                return F()

            def filter(self, *a, **kw):
                class F:
                    def first(inner):
                        return db.status

                return F()

            def all(self):
                # Return empty list for group_by().all() calls by default
                return []

            def scalar(self):
                # For count queries return 0
                return 0

            def group_by(self, *a, **kw):
                return self

        return Q()

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        pass

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


class TestRSSParserMore(unittest.TestCase):
    def test_update_feed_status_creates_and_updates(self):
        db = FakeDB()
        status = rss.update_feed_status(db, "F", "http://x", success=True, articles_count=2)
        # status object returned should have articles_count set
        self.assertIsNotNone(status)

    def test_update_feed_status_db_parsing_started_and_success(self):
        db = FakeDB()
        cfg = SimpleNamespace(name="F", url="http://x", enabled=True)
        # parsing_started path
        rss.update_feed_status_db(db, cfg, parsing_started=True)
        # success path
        rss.update_feed_status_db(db, cfg, parsing_started=False, success=True, articles_count=3)

    def test_update_feed_status_db_failure_path(self):
        # make db that raises on commit to hit except block
        class BadDB(FakeDB):
            def commit(self):
                raise Exception("boom")

        db = BadDB()
        cfg = SimpleNamespace(name="F", url="http://x", enabled=True)
        # should not raise
        rss.update_feed_status_db(db, cfg, parsing_started=False, success=False, error="err")

    def test_utils_extracts_and_parses(self):
        # extract_website with missing feed.feed.link
        class Feed:
            pass

        f = Feed()
        self.assertIn("example.com", rss.extract_website(f, "http://example.com/rss"))

        # get_safe_text with list of dict
        e = SimpleNamespace()
        e.field = [{"value": "v"}]
        self.assertEqual(rss.get_safe_text(e, "field"), "v")

        # parse_published_date when none
        e2 = SimpleNamespace()
        self.assertIsNone(rss.parse_published_date(e2))

        # extract_content fallbacks
        e3 = SimpleNamespace()
        e3.summary = "s"
        self.assertEqual(rss.extract_content(e3), "s")

        # detect_language returns unknown on empty
        self.assertEqual(rss.detect_language(SimpleNamespace()), "unknown")

    @patch("parser.rss_parser.load_feeds_config")
    @patch("parser.rss_parser.get_enabled_feeds")
    @patch("parser.rss_parser.get_db")
    def test_main_runs_without_errors(self, mock_get_db, mock_get_enabled, mock_load):
        # Setup mocks for main() to exercise printing/stat paths
        mock_load.return_value = SimpleNamespace()
        cfg = SimpleNamespace()
        feed_cfg = SimpleNamespace(
            name="Feed", url="http://x", category="News", country="US", language="en", enabled=True
        )
        mock_get_enabled.return_value = [feed_cfg]
        fake_db = FakeDB()
        # get_db yields a generator — simulate with iterable; return a fresh iterator each call
        mock_get_db.side_effect = lambda: iter([fake_db])

        # Patch parse_feed to avoid network calls
        with patch("parser.rss_parser.parse_feed") as p:
            p.return_value = SimpleNamespace(processed=0, errors=0)
            # Calling main should not raise
            rss.main()
