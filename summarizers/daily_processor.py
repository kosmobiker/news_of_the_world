"""Process daily summaries using the Grok API."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from db.database import Article
from models.models import DailySummary
from summarizers.grok import GrokSummarizer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def fetch_articles_for_date(db: Session, target_date: datetime):
    """
    Fetch articles from the database for the calendar day of `target_date` using the date
    portion of `parsed_at`. This avoids hour-level timezone/window mismatches when the
    summarization job runs at an arbitrary time (e.g. 04:30 next day).

    If no articles are found by parsed_at date, fall back to published_at date.
    """
    # Use the DB's date extraction to match all rows whose parsed_at date equals target_date.date()
    articles = (
        db.query(Article)
        .filter(func.date(Article.parsed_at) == target_date.date())
        .order_by(Article.parsed_at.desc())
        .all()
    )

    if articles:
        return articles

    logger.info(
        f"No articles found for {target_date.date()} using parsed_at date; falling back to published_at date"
    )

    articles = (
        db.query(Article)
        .filter(func.date(Article.published_at) == target_date.date())
        .order_by(Article.published_at.desc())
        .all()
    )

    return articles


def process_daily_summary(db: Session, date: datetime = None) -> DailySummary:
    """
    Create a summary for all articles from a specific date.
    If date is not provided, process for today.
    """
    # Default behavior: process yesterday's calendar day. This ensures that
    # a run occurring in the early hours of the next day (e.g. 2025-11-04 04:30)
    # will summarize articles from 2025-11-03 (00:00–23:59) as requested.
    if date is None:
        date = datetime.utcnow() - timedelta(days=1)

    target_date = date if isinstance(date, datetime) else datetime.utcnow() - timedelta(days=1)

    # Fetch articles for the calendar date
    articles = fetch_articles_for_date(db, target_date)

    if not articles:
        logger.warning(f"No articles found for {target_date.date()}")
        return None

    logger.info(f"Processing {len(articles)} articles for {target_date.date()}")

    # Convert articles to format expected by summarizer
    article_dicts = [
        {
            "headline": article.headline,
            "website": article.website,
            "content": article.content or article.summary,
        }
        for article in articles
    ]

    # Create summary using Grok
    summarizer = GrokSummarizer(db)
    summary_data = summarizer.summarize_articles(article_dicts)

    # Return the summary data instead of saving it to the database
    logger.info(f"Generated summary for {target_date.date()} with {len(articles)} articles")
    # Store the date as midnight UTC for the day summarized to keep `daily_summaries.date`
    # consistent. Use target_date.replace(...) to zero-out time component.
    stored_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "date": stored_date,
        "summary_data": summary_data,
        "articles_count": len(articles),
        "model_name": summarizer.model_name,
    }
