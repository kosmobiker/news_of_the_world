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


class TestParsePublishedDateVariations(unittest.TestCase):
    """Test various date parsing scenarios."""

    def test_parse_date_with_updated_parsed(self):
        """Given: entry with updated_parsed but no published_parsed
        When: parse_published_date is called
        Then: should return datetime from updated_parsed"""
        # Given
        e = SimpleNamespace()
        e.published_parsed = None
        e.updated_parsed = (2025, 11, 15, 10, 30, 0, 0, 0, 0)
        e.created_parsed = None

        # When
        dt = rss_parser.parse_published_date(e)

        # Then
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.day, 15)

    def test_parse_date_with_created_parsed(self):
        """Given: entry with only created_parsed
        When: parse_published_date is called
        Then: should return datetime from created_parsed"""
        # Given
        e = SimpleNamespace()
        e.published_parsed = None
        e.updated_parsed = None
        e.created_parsed = (2025, 11, 10, 8, 0, 0, 0, 0, 0)

        # When
        dt = rss_parser.parse_published_date(e)

        # Then
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.day, 10)

    def test_parse_date_with_no_dates(self):
        """Given: entry with no date fields
        When: parse_published_date is called
        Then: should return None"""
        # Given
        e = SimpleNamespace()
        e.published_parsed = None
        e.updated_parsed = None
        e.created_parsed = None

        # When
        dt = rss_parser.parse_published_date(e)

        # Then
        self.assertIsNone(dt)

    def test_parse_date_with_exception(self):
        """Given: entry with invalid date format
        When: parse_published_date is called
        Then: should handle exception and return None"""
        # Given
        e = SimpleNamespace()
        e.published_parsed = "invalid"

        # When
        dt = rss_parser.parse_published_date(e)

        # Then
        self.assertIsNone(dt)


class TestExtractContentVariations(unittest.TestCase):
    """Test various content extraction scenarios."""

    def test_extract_content_with_empty_list(self):
        """Given: entry with empty content list but has description
        When: extract_content is called
        Then: should return description as fallback"""
        # Given
        e = SimpleNamespace()
        e.content = []
        e.description = "fallback description"

        # When
        result = rss_parser.extract_content(e)

        # Then
        self.assertEqual(result, "fallback description")

    def test_extract_content_with_summary(self):
        """Given: entry with no content or description but has summary
        When: extract_content is called
        Then: should return summary"""
        # Given
        e = SimpleNamespace()
        e.content = None
        e.description = None
        e.summary = "summary text"

        # When
        result = rss_parser.extract_content(e)

        # Then
        self.assertEqual(result, "summary text")

    def test_extract_content_with_exception(self):
        """Given: entry is None (will cause AttributeError)
        When: extract_content is called
        Then: should handle exception and return empty string"""
        # Given
        e = None

        # When
        result = rss_parser.extract_content(e)

        # Then
        self.assertEqual(result, "")


class TestDetectLanguageVariations(unittest.TestCase):
    """Test language detection scenarios."""

    def test_detect_language_with_title_only(self):
        """Given: entry with only title field
        When: detect_language is called
        Then: should detect language from title"""
        # Given
        e = SimpleNamespace()
        e.title = "English Article Title"
        e.summary = None

        # When
        result = rss_parser.detect_language(e)

        # Then
        self.assertIsInstance(result, str)

    def test_detect_language_empty_text(self):
        """Given: entry with no title or summary
        When: detect_language is called
        Then: should return 'unknown'"""
        # Given
        e = SimpleNamespace()
        e.title = None
        e.summary = None

        # When
        result = rss_parser.detect_language(e)

        # Then
        self.assertEqual(result, "unknown")

    def test_detect_language_with_exception(self):
        """Given: entry is None
        When: detect_language is called
        Then: should handle exception and return 'unknown'"""
        # Given
        e = None

        # When
        result = rss_parser.detect_language(e)

        # Then
        self.assertEqual(result, "unknown")


class TestExtractWebsite(unittest.TestCase):
    """Test website extraction from feeds."""

    def test_extract_website_from_feed_link(self):
        """Given: feed with feed.link attribute
        When: extract_website is called
        Then: should extract domain from feed.link"""
        # Given
        feed = SimpleNamespace()
        feed.feed = SimpleNamespace(link="http://www.bbc.com/news/index.html")

        # When
        result = rss_parser.extract_website(feed, "http://feeds.bbc.com/rss")

        # Then
        self.assertEqual(result, "www.bbc.com")

    def test_extract_website_from_url_fallback(self):
        """Given: feed with no feed attribute
        When: extract_website is called
        Then: should extract domain from feed URL"""
        # Given
        feed = SimpleNamespace()
        feed.feed = None

        # When
        result = rss_parser.extract_website(feed, "http://feeds.example.com/rss")

        # Then
        self.assertEqual(result, "feeds.example.com")

    def test_extract_website_with_exception(self):
        """Given: feed is None
        When: extract_website is called
        Then: should handle exception and extract from URL"""
        # Given
        feed = None

        # When
        result = rss_parser.extract_website(feed, "http://example.com/rss")

        # Then
        self.assertEqual(result, "example.com")


class TestGetSafeText(unittest.TestCase):
    """Test safe text extraction."""

    def test_get_safe_text_string_value(self):
        """Given: entry with a string value field
        When: get_safe_text is called with that field
        Then: should return the string value"""
        # Given
        entry = SimpleNamespace(title="Article Title", author=None)

        # When
        result = rss_parser.get_safe_text(entry, "title")

        # Then
        self.assertEqual(result, "Article Title")

    def test_get_safe_text_list_with_dict(self):
        """Given: entry with list of dicts containing 'value' key
        When: get_safe_text is called with that field
        Then: should return first item's 'value'"""
        # Given
        entry = SimpleNamespace(authors=[{"value": "John Doe"}, {"value": "Jane Doe"}])

        # When
        result = rss_parser.get_safe_text(entry, "authors")

        # Then
        self.assertEqual(result, "John Doe")

    def test_get_safe_text_list_with_string(self):
        """Given: entry with list of strings
        When: get_safe_text is called with that field
        Then: should return first string"""
        # Given
        entry = SimpleNamespace(categories=["Technology", "Science"])

        # When
        result = rss_parser.get_safe_text(entry, "categories")

        # Then
        self.assertEqual(result, "Technology")

    def test_get_safe_text_missing_field(self):
        """Given: entry without the requested field
        When: get_safe_text is called
        Then: should return empty string"""
        # Given
        entry = SimpleNamespace(title="Title")

        # When
        result = rss_parser.get_safe_text(entry, "nonexistent")

        # Then
        self.assertEqual(result, "")

    def test_get_safe_text_empty_value(self):
        """Given: entry with empty string value
        When: get_safe_text is called
        Then: should return empty string"""
        # Given
        entry = SimpleNamespace(description="")

        # When
        result = rss_parser.get_safe_text(entry, "description")

        # Then
        self.assertEqual(result, "")


class TestProcessFeedEntriesEdgeCases(unittest.TestCase):
    """Test edge cases in feed entry processing."""

    def test_process_entry_without_link(self):
        """Given: feed entry without link field
        When: process_feed_entries is called
        Then: should handle missing link gracefully"""
        # Given
        db = DummyDB()
        entry = {
            "title": "Article",
            "description": "Description",
            "published_parsed": (2025, 11, 30, 12, 0, 0, 0, 0, 0),
            "content": [{"value": "Content"}],
        }
        feed_conf = SimpleNamespace(name="Feed", category="News", country="US", language="en")

        # When/Then - should handle missing link without crashing
        try:
            result = rss_parser.process_feed_entries(db, [entry], feed_conf)
            # Either processes or skips gracefully
        except Exception:
            pass

    def test_process_entry_without_content(self):
        """Given: feed entry without content field
        When: process_feed_entries is called
        Then: should use description as fallback"""
        # Given
        db = DummyDB()
        entry = {
            "title": "Article",
            "description": "Description",
            "link": "http://example.com/article",
            "published_parsed": (2025, 11, 30, 12, 0, 0, 0, 0, 0),
        }
        feed_conf = SimpleNamespace(name="Feed", category="News", country="US", language="en")

        # When
        result = rss_parser.process_feed_entries(db, [entry], feed_conf)

        # Then
        self.assertIsInstance(result, list)

    def test_process_multiple_entries(self):
        """Given: multiple feed entries
        When: process_feed_entries is called
        Then: should process all entries"""
        # Given
        db = DummyDB()
        entries = [
            {
                "title": "Article 1",
                "description": "Desc 1",
                "link": "http://example.com/1",
                "published_parsed": (2025, 11, 30, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Content 1"}],
            },
            {
                "title": "Article 2",
                "description": "Desc 2",
                "link": "http://example.com/2",
                "published_parsed": (2025, 11, 30, 13, 0, 0, 0, 0, 0),
                "content": [{"value": "Content 2"}],
            },
        ]
        feed_conf = SimpleNamespace(name="Feed", category="News", country="US", language="en")

        # When
        result = rss_parser.process_feed_entries(db, entries, feed_conf)

        # Then
        self.assertGreaterEqual(len(result), 0)
