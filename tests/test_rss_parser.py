import unittest
from unittest.mock import patch, MagicMock
from parser.rss_parser import parse_feed, process_feed_entries, update_feed_status
from models.models import FeedStatus, Article


class TestRSSParser(unittest.TestCase):
    @patch("parser.rss_parser.feedparser.parse")
    def test_parse_feed(self, mock_parse):
        # Given
        mock_feed = MagicMock()
        mock_feed.status = 200
        mock_feed.entries = [
            {
                "title": "Sample Article",
                "description": "Sample Description",
                "link": "http://example.com/article",
                "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Sample Content"}],
            }
        ]
        mock_parse.return_value = mock_feed

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.side_effect = (
            lambda *args, **kwargs: None
        )
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None
        db.refresh.side_effect = lambda article: None

        feed_config = MagicMock(
            url="http://example.com/rss",
            name="Sample Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = parse_feed(db, feed_config)

        # Then
        self.assertEqual(result.processed, 1)
        self.assertEqual(result.errors, 0)
        mock_parse.assert_called_once_with("http://example.com/rss")

    @patch("parser.rss_parser.feedparser.parse")
    def test_parse_feed_http_error_400(self, mock_parse):
        """Test handling of HTTP 400 error."""
        # Given
        mock_feed = MagicMock()
        mock_feed.status = 404
        mock_parse.return_value = mock_feed

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None
        db.refresh.side_effect = lambda article: None

        feed_config = MagicMock(
            url="http://example.com/rss",
            name="Dead Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = parse_feed(db, feed_config)

        # Then
        self.assertEqual(result.processed, 0)
        self.assertEqual(result.errors, 1)

    @patch("parser.rss_parser.feedparser.parse")
    def test_parse_feed_bozo_error_no_entries(self, mock_parse):
        """Test handling of bozo error with no entries."""
        # Given
        mock_feed = MagicMock()
        mock_feed.status = 200
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("XML parsing error")
        mock_feed.entries = []
        mock_parse.return_value = mock_feed

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None
        db.refresh.side_effect = lambda article: None

        feed_config = MagicMock(
            url="http://example.com/rss",
            name="Broken Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = parse_feed(db, feed_config)

        # Then
        self.assertEqual(result.processed, 0)
        self.assertEqual(result.errors, 1)

    @patch("parser.rss_parser.feedparser.parse")
    def test_parse_feed_bozo_error_with_entries(self, mock_parse):
        """Test handling of bozo error but still has entries (non-fatal)."""
        # Given
        mock_feed = MagicMock()
        mock_feed.status = 200
        mock_feed.bozo = True
        mock_feed.bozo_exception = Exception("Minor XML issue")
        mock_feed.entries = [
            {
                "title": "Article Despite Error",
                "description": "Still parseable",
                "link": "http://example.com/article",
                "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Content"}],
            }
        ]
        mock_parse.return_value = mock_feed

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.side_effect = (
            lambda *args, **kwargs: None
        )
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None
        db.refresh.side_effect = lambda article: None

        feed_config = MagicMock(
            url="http://example.com/rss",
            name="Resilient Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = parse_feed(db, feed_config)

        # Then
        self.assertEqual(result.processed, 1)
        self.assertEqual(result.errors, 0)

    @patch("parser.rss_parser.feedparser.parse")
    def test_parse_feed_exception(self, mock_parse):
        """Test exception handling during parsing."""
        # Given
        mock_parse.side_effect = Exception("Network error")

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None
        db.refresh.side_effect = lambda article: None

        feed_config = MagicMock(
            url="http://example.com/rss",
            name="Unreachable Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = parse_feed(db, feed_config)

        # Then
        self.assertEqual(result.processed, 0)
        self.assertEqual(result.errors, 1)

    def test_process_feed_entries_duplicate_detection(self):
        """Test that duplicate articles are skipped."""
        # Given
        entries = [
            {
                "title": "Duplicate Article",
                "description": "Description",
                "link": "http://example.com/article",
                "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Content"}],
            }
        ]

        db = MagicMock()
        # Simulate existing article
        db.query.return_value.filter_by.return_value.first.return_value = MagicMock(
            id=1
        )

        feed_config = MagicMock(
            name="Test Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = process_feed_entries(db, entries, feed_config)

        # Then
        self.assertEqual(len(result), 0)  # No new articles added
        db.add.assert_not_called()

    @patch("parser.rss_parser.langdetect.detect")
    def test_process_feed_entries_language_detection(self, mock_detect):
        """Test language detection for articles."""
        # Given
        mock_detect.return_value = "fr"
        entries = [
            {
                "title": "Article en Français",
                "description": "Ceci est une description",
                "link": "http://example.com/article",
                "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Contenu complet"}],
            }
        ]

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None

        feed_config = MagicMock(
            name="French Feed",
            language="fr",
            category="News",
            country="FR",
        )

        # When
        result = process_feed_entries(db, entries, feed_config)

        # Then
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].language, "fr")

    @patch("parser.rss_parser.langdetect.detect")
    def test_process_feed_entries_language_detection_fallback(self, mock_detect):
        """Test fallback to feed language when detection fails."""
        # Given
        mock_detect.side_effect = Exception("Detection failed")
        entries = [
            {
                "title": "Article",
                "description": "Description",
                "link": "http://example.com/article",
                "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Content"}],
            }
        ]

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None

        feed_config = MagicMock(
            name="Test Feed",
            language="de",
            category="News",
            country="DE",
        )

        # When
        result = process_feed_entries(db, entries, feed_config)

        # Then
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].language, "de")

    def test_process_feed_entries_missing_published_date(self):
        """Test handling of entries without published date."""
        # Given
        entries = [
            {
                "title": "No Date Article",
                "description": "Description",
                "link": "http://example.com/article",
                # No published_parsed
                "content": [{"value": "Content"}],
            }
        ]

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None

        feed_config = MagicMock(
            name="Test Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = process_feed_entries(db, entries, feed_config)

        # Then
        self.assertEqual(len(result), 1)
        self.assertIsNotNone(result[0].published_at)

    def test_process_feed_entries_entry_exception_handling(self):
        """Test that exception in one entry doesn't break processing."""
        # Given
        entries = [
            {
                "title": "First Article",
                "description": "Description",
                "link": "http://example.com/article1",
                "published_parsed": (2025, 11, 2, 12, 0, 0, 0, 0, 0),
                "content": [{"value": "Content"}],
            },
            {
                # This will cause an issue
                "title": None,
                "description": "Description",
                "link": "http://example.com/article2",
                "published_parsed": "invalid",  # Invalid date format
                "content": [{"value": "Content"}],
            },
        ]

        db = MagicMock()
        db.query.return_value.filter_by.return_value.first.return_value = None
        db.add.side_effect = lambda article: None
        db.commit.side_effect = lambda: None

        feed_config = MagicMock(
            name="Test Feed",
            language="en",
            category="News",
            country="US",
        )

        # When
        result = process_feed_entries(db, entries, feed_config)

        # Then - First article should be processed, second should be skipped
        self.assertEqual(len(result), 1)


if __name__ == "__main__":
    unittest.main()
