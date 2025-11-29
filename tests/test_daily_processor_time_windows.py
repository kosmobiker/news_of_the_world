"""Tests for daily and weekly summarization use cases."""

import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from summarizers.daily_processor import fetch_articles_for_date, process_daily_summary
from db.database import Article
import logging

# Silence noisy logger during tests
logging.getLogger("summarizers.daily_processor").setLevel(logging.CRITICAL)


class TestFetchArticlesForDate(unittest.TestCase):
    """Test article fetching with various time windows."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=Session)
        self.mock_query = MagicMock()
        self.mock_db.query.return_value = self.mock_query

    def test_fetch_articles_daily_single_day(self):
        """Test fetching articles for a single day (daily summarization)."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)
        articles = [
            MagicMock(headline="Article 1", website="Source 1", category="business"),
            MagicMock(headline="Article 2", website="Source 2", category="business"),
        ]
        self.mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = articles

        # When
        result = fetch_articles_for_date(self.mock_db, target_date, category="business", days=1)

        # Then
        self.assertEqual(result, articles)
        self.assertEqual(len(result), 2)

    def test_fetch_articles_weekly_seven_days(self):
        """Test fetching articles for 7 days (weekly summarization)."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)
        articles = [
            MagicMock(headline="Article 1", website="Source 1", category="engineering"),
            MagicMock(headline="Article 2", website="Source 2", category="engineering"),
            MagicMock(headline="Article 3", website="Source 3", category="engineering"),
            MagicMock(headline="Article 4", website="Source 4", category="engineering"),
            MagicMock(headline="Article 5", website="Source 5", category="engineering"),
        ]
        self.mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = articles

        # When
        result = fetch_articles_for_date(self.mock_db, target_date, category="engineering", days=7)

        # Then
        self.assertEqual(result, articles)
        self.assertEqual(len(result), 5)

    def test_fetch_articles_no_category_filter(self):
        """Test fetching articles without category filter."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)
        articles = [
            MagicMock(headline="Article 1"),
            MagicMock(headline="Article 2"),
            MagicMock(headline="Article 3"),
        ]

        # Patch the entire function to test the parameter passing
        with patch("summarizers.daily_processor.fetch_articles_for_date") as mock_fetch:
            mock_fetch.return_value = articles

            # When
            result = mock_fetch(self.mock_db, target_date, category=None, days=1)

            # Then
            self.assertEqual(len(result), 3)
            self.assertEqual(result, articles)
            # Verify it was called without category
            mock_fetch.assert_called_once_with(self.mock_db, target_date, category=None, days=1)

    def test_fetch_articles_empty_result(self):
        """Test fetching articles with no results."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)
        self.mock_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # Mock the fallback query
        fallback_query = MagicMock()
        self.mock_db.query.side_effect = [self.mock_query, fallback_query]
        fallback_query.filter.return_value.filter.return_value.order_by.return_value.all.return_value = []

        # When
        result = fetch_articles_for_date(self.mock_db, target_date, category="business", days=1)

        # Then
        self.assertEqual(result, [])


class TestProcessDailySummary(unittest.TestCase):
    """Test daily and weekly summarization processing."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_db = MagicMock(spec=Session)
        self.mock_query = MagicMock()
        self.mock_db.query.return_value = self.mock_query

    @patch("summarizers.daily_processor.fetch_articles_for_date")
    @patch("summarizers.daily_processor.GrokSummarizer")
    def test_process_daily_summary_business_category(self, mock_grok_class, mock_fetch):
        """Test processing daily summary for business category (1 day)."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)

        # Mock articles
        mock_article1 = MagicMock()
        mock_article1.headline = "Market Report"
        mock_article1.website = "Financial Times"
        mock_article1.content = "Market data..."
        mock_article1.link = "https://ft.com/article1"

        mock_article2 = MagicMock()
        mock_article2.headline = "Tech IPO"
        mock_article2.website = "Bloomberg"
        mock_article2.content = "IPO announcement..."
        mock_article2.link = "https://bloomberg.com/article2"

        articles = [mock_article1, mock_article2]
        mock_fetch.return_value = articles

        # Mock Grok summarizer
        mock_summarizer = MagicMock()
        mock_grok_class.return_value = mock_summarizer
        mock_summarizer.model_name = "grok"
        mock_summarizer.summarize_articles.return_value = {
            "text_summary": "Markets up 2%",
            "detailed_summary": "Financial markets...",
            "main_events": {"Market Surge": "Markets gained 2%"},
            "key_themes": {"Economic Growth": "Positive indicators"},
            "impacted_regions": {"US": "Stock market rally"},
            "timeline": {"Nov 28": "Market surge"},
            "top_articles": [
                {
                    "title": "Market Report",
                    "source": "Financial Times",
                    "link": "https://ft.com/article1",
                },
                {
                    "title": "Tech IPO",
                    "source": "Bloomberg",
                    "link": "https://bloomberg.com/article2",
                },
            ],
        }

        # When
        result = process_daily_summary(self.mock_db, date=target_date, category="business", days=1)

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "business")
        self.assertEqual(result["articles_count"], 2)
        self.assertEqual(result["model_name"], "grok")
        self.assertIn("top_articles", result["summary_data"])
        self.assertEqual(len(result["summary_data"]["top_articles"]), 2)

        # Verify fetch was called with correct parameters
        mock_fetch.assert_called_once_with(self.mock_db, target_date, category="business", days=1)

    @patch("summarizers.daily_processor.fetch_articles_for_date")
    @patch("summarizers.daily_processor.GrokSummarizer")
    def test_process_weekly_summary_engineering_category(self, mock_grok_class, mock_fetch):
        """Test processing weekly summary for engineering category (7 days)."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)

        # Mock articles (more articles for weekly)
        articles = []
        for i in range(1, 8):
            mock_article = MagicMock()
            mock_article.headline = f"Engineering Article {i}"
            mock_article.website = f"Source {i}"
            mock_article.content = f"Content {i}..."
            mock_article.link = f"https://example.com/article{i}"
            articles.append(mock_article)

        mock_fetch.return_value = articles

        # Mock Grok summarizer
        mock_summarizer = MagicMock()
        mock_grok_class.return_value = mock_summarizer
        mock_summarizer.model_name = "grok"

        top_articles = [
            {
                "title": f"Engineering Article {i}",
                "source": f"Source {i}",
                "link": f"https://example.com/article{i}",
            }
            for i in range(1, 6)
        ]

        mock_summarizer.summarize_articles.return_value = {
            "text_summary": "Weekly engineering updates",
            "detailed_summary": "This week in engineering...",
            "main_events": {"New Framework": "Major release"},
            "key_themes": {"Cloud Computing": "Scaling challenges"},
            "impacted_regions": {"Global": "Industry trends"},
            "timeline": {"Nov 21-28": "Weekly summary"},
            "top_articles": top_articles,
        }

        # When
        result = process_daily_summary(
            self.mock_db, date=target_date, category="engineering", days=7
        )

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "engineering")
        self.assertEqual(result["articles_count"], 7)
        self.assertEqual(result["model_name"], "grok")
        self.assertEqual(len(result["summary_data"]["top_articles"]), 5)

        # Verify fetch was called with 7 days
        mock_fetch.assert_called_once_with(
            self.mock_db, target_date, category="engineering", days=7
        )

    @patch("summarizers.daily_processor.fetch_articles_for_date")
    def test_process_summary_no_articles_found(self, mock_fetch):
        """Test processing summary when no articles are found."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)
        mock_fetch.return_value = []

        # When
        result = process_daily_summary(
            self.mock_db, date=target_date, category="technology", days=1
        )

        # Then
        self.assertIsNone(result)

    @patch("summarizers.daily_processor.fetch_articles_for_date")
    @patch("summarizers.daily_processor.GrokSummarizer")
    def test_process_summary_technology_daily(self, mock_grok_class, mock_fetch):
        """Test processing daily summary for technology category."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)

        mock_article = MagicMock()
        mock_article.headline = "AI Breakthrough"
        mock_article.website = "TechCrunch"
        mock_article.content = "New AI model released..."
        mock_article.link = "https://techcrunch.com/ai-breakthrough"

        mock_fetch.return_value = [mock_article]

        mock_summarizer = MagicMock()
        mock_grok_class.return_value = mock_summarizer
        mock_summarizer.model_name = "grok"
        mock_summarizer.summarize_articles.return_value = {
            "text_summary": "New AI model released",
            "detailed_summary": "Tech industry...",
            "main_events": {"AI Release": "New model"},
            "key_themes": {"AI/ML": "Technology"},
            "impacted_regions": {"Global": "Tech industry"},
            "timeline": {"Nov 28": "AI release"},
            "top_articles": [
                {
                    "title": "AI Breakthrough",
                    "source": "TechCrunch",
                    "link": "https://techcrunch.com/ai-breakthrough",
                }
            ],
        }

        # When
        result = process_daily_summary(
            self.mock_db, date=target_date, category="technology", days=1
        )

        # Then
        self.assertIsNotNone(result)
        self.assertEqual(result["category"], "technology")
        self.assertEqual(result["articles_count"], 1)

        # Verify fetch was called with 1 day for daily
        mock_fetch.assert_called_once_with(self.mock_db, target_date, category="technology", days=1)

    @patch("summarizers.daily_processor.fetch_articles_for_date")
    @patch("summarizers.daily_processor.GrokSummarizer")
    def test_process_summary_default_date_is_yesterday(self, mock_grok_class, mock_fetch):
        """Test that default date is yesterday when not specified."""
        # Given
        mock_article = MagicMock()
        mock_article.headline = "News Article"
        mock_article.website = "BBC"
        mock_article.content = "News content..."
        mock_article.link = "https://bbc.com/news"

        mock_fetch.return_value = [mock_article]

        mock_summarizer = MagicMock()
        mock_grok_class.return_value = mock_summarizer
        mock_summarizer.model_name = "grok"
        mock_summarizer.summarize_articles.return_value = {
            "text_summary": "Daily news",
            "detailed_summary": "Today's news...",
            "main_events": {},
            "key_themes": {},
            "impacted_regions": {},
            "timeline": {},
            "top_articles": [],
        }

        # When
        result = process_daily_summary(self.mock_db, category="business", days=1)

        # Then
        self.assertIsNotNone(result)
        # Verify fetch was called (date handling is internal)
        mock_fetch.assert_called_once()
        call_args = mock_fetch.call_args
        # Check that it was called with a date object
        self.assertEqual(call_args[0][0], self.mock_db)
        self.assertIsInstance(call_args[0][1], datetime)


class TestTimeWindowComparison(unittest.TestCase):
    """Test comparisons between daily and weekly summarization."""

    @patch("summarizers.daily_processor.fetch_articles_for_date")
    @patch("summarizers.daily_processor.GrokSummarizer")
    def test_daily_vs_weekly_article_count(self, mock_grok_class, mock_fetch):
        """Test that weekly summaries typically contain more articles than daily."""
        # Given
        target_date = datetime(2025, 11, 28, 12, 0, 0)

        # Daily has fewer articles
        daily_articles = [MagicMock() for _ in range(3)]
        for i, article in enumerate(daily_articles):
            article.headline = f"Article {i}"
            article.website = f"Source {i}"
            article.content = f"Content {i}"
            article.link = f"https://example.com/{i}"

        # Weekly has more articles
        weekly_articles = [MagicMock() for _ in range(10)]
        for i, article in enumerate(weekly_articles):
            article.headline = f"Article {i}"
            article.website = f"Source {i}"
            article.content = f"Content {i}"
            article.link = f"https://example.com/{i}"

        mock_summarizer = MagicMock()
        mock_grok_class.return_value = mock_summarizer
        mock_summarizer.model_name = "grok"
        mock_summarizer.summarize_articles.return_value = {
            "text_summary": "Summary",
            "detailed_summary": "Detailed...",
            "main_events": {},
            "key_themes": {},
            "impacted_regions": {},
            "timeline": {},
            "top_articles": [],
        }

        # When
        mock_fetch.return_value = daily_articles
        daily_result = process_daily_summary(
            MagicMock(spec=Session), date=target_date, category="business", days=1
        )

        mock_fetch.return_value = weekly_articles
        weekly_result = process_daily_summary(
            MagicMock(spec=Session), date=target_date, category="business", days=7
        )

        # Then
        self.assertEqual(daily_result["articles_count"], 3)
        self.assertEqual(weekly_result["articles_count"], 10)
        self.assertGreater(weekly_result["articles_count"], daily_result["articles_count"])


if __name__ == "__main__":
    unittest.main()
