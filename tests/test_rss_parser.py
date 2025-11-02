import unittest
from unittest.mock import patch, MagicMock
from parser.rss_parser import parse_feed


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


if __name__ == "__main__":
    unittest.main()
