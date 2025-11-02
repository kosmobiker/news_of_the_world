import unittest
from parser import rss_parser
from types import SimpleNamespace
from datetime import datetime


class DummyDB:
    def __init__(self):
        self.added = []

    def query(self, *args, **kwargs):
        class Q:
            def __init__(self, outer):
                self.outer = outer

            def filter_by(self, **kw):
                class F:
                    def first(self):
                        return None

                return F()

        return Q(self)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass


class TestRSSParserExtra(unittest.TestCase):
    def test_parse_published_date_and_extract_content(self):
        e = SimpleNamespace()
        e.published_parsed = (2025, 11, 2, 12, 0, 0, 0, 0, 0)
        dt = rss_parser.parse_published_date(e)
        self.assertIsInstance(dt, datetime)

        e2 = SimpleNamespace()
        e2.content = [{"value": "full"}]
        self.assertEqual(rss_parser.extract_content(e2), "full")

        e3 = SimpleNamespace()
        e3.description = "desc"
        self.assertEqual(rss_parser.extract_content(e3), "desc")

        e4 = SimpleNamespace()
        e4.summary = "sum"
        self.assertEqual(rss_parser.extract_content(e4), "sum")

    def test_get_safe_text_and_extract_website(self):
        e = SimpleNamespace()
        e.title = "T"
        self.assertEqual(rss_parser.get_safe_text(e, "title"), "T")

        # feed with feed.link attribute
        feed = SimpleNamespace()
        feed.feed = SimpleNamespace()
        feed.feed.link = "http://example.com/path"
        self.assertIn("example.com", rss_parser.extract_website(feed, "http://x"))

    def test_detect_language_unknown(self):
        e = SimpleNamespace()
        self.assertEqual(rss_parser.detect_language(e), "unknown")

    def test_process_feed_entries_creates_article(self):
        db = DummyDB()
        entry = {
            "title": "Sample",
            "description": "desc",
            "link": "http://example.com/a",
            "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
            "content": [{"value": "content text"}],
        }

        feed_conf = SimpleNamespace(name="Feed", category="News", country="US", language="en")

        res = rss_parser.process_feed_entries(db, [entry], feed_conf)
        # db should have added one article object
        self.assertEqual(len(db.added), 1)
        self.assertEqual(len(res), 1)

    def test_parse_feed_http_error(self):
        # Mock feedparser.parse to return an object with status != 200
        class FeedObj:
            status = 500
            entries = []

        def fake_parse(url):
            return FeedObj()

        db = DummyDB()
        feed_conf = SimpleNamespace(
            name="Feed", url="http://x", category="News", country="US", language="en"
        )

        original = rss_parser.feedparser.parse
        rss_parser.feedparser.parse = fake_parse
        try:
            res = rss_parser.parse_feed(db, feed_conf)
            self.assertEqual(res.processed, 0)
            self.assertEqual(res.errors, 1)
        finally:
            rss_parser.feedparser.parse = original

    def test_parse_feed_bozo_error(self):
        # Mock feedparser.parse to return an object with bozo True
        class FeedObj:
            status = 200
            bozo = True
            bozo_exception = Exception("boom")
            entries = []

        def fake_parse(url):
            return FeedObj()

        db = DummyDB()
        feed_conf = SimpleNamespace(
            name="Feed", url="http://x", category="News", country="US", language="en"
        )

        original = rss_parser.feedparser.parse
        rss_parser.feedparser.parse = fake_parse
        try:
            res = rss_parser.parse_feed(db, feed_conf)
            self.assertEqual(res.processed, 0)
            self.assertEqual(res.errors, 1)
        finally:
            rss_parser.feedparser.parse = original

    def test_process_feed_entries_duplicate_skipped(self):
        # DB that returns an existing article so process_feed_entries skips
        class DBDup(DummyDB):
            def query(self, *args, **kwargs):
                class Q:
                    def filter_by(self, **kw):
                        class F:
                            def first(self):
                                return SimpleNamespace(id=1)

                        return F()

                return Q()

        db = DBDup()
        entry = {
            "title": "Sample",
            "description": "desc",
            "link": "http://example.com/a",
            "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
            "content": [{"value": "content text"}],
        }

        feed_conf = SimpleNamespace(name="Feed", category="News", country="US", language="en")
        res = rss_parser.process_feed_entries(db, [entry], feed_conf)
        # No new article should be added
        self.assertEqual(len(db.added), 0)
        self.assertEqual(len(res), 0)
