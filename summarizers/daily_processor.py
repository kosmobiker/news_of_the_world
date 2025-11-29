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


def fetch_articles_for_date(
    db: Session, target_date: datetime, category: str = None, days: int = 1
):
    """
    Fetch articles from the database for a time window using the date
    portion of `parsed_at`. This avoids hour-level timezone/window mismatches when the
    summarization job runs at an arbitrary time (e.g. 04:30 next day).

    If no articles are found by parsed_at date, fall back to published_at date.

    Args:
        db: Database session
        target_date: End date for filtering articles (exclusive)
        category: Optional category filter (e.g., 'business', 'technology', 'engineering')
        days: Number of days to look back (default 1 for daily, 7 for weekly)
    """
    # Calculate start date by looking back 'days' days
    start_date = target_date - timedelta(days=days)

    # Use the DB's date extraction to match all rows whose parsed_at date falls within the window
    query = db.query(Article).filter(
        func.date(Article.parsed_at) >= start_date.date(),
        func.date(Article.parsed_at) < target_date.date(),
    )

    if category:
        query = query.filter(Article.category == category)

    articles = query.order_by(Article.parsed_at.desc()).all()

    if articles:
        return articles

    logger.info(
        f"No articles found for {start_date.date()} to {target_date.date()} using parsed_at date; falling back to published_at date"
    )

    query = db.query(Article).filter(
        func.date(Article.published_at) >= start_date.date(),
        func.date(Article.published_at) < target_date.date(),
    )

    if category:
        query = query.filter(Article.category == category)

    articles = query.order_by(Article.published_at.desc()).all()

    return articles


def process_daily_summary(
    db: Session, date: datetime = None, category: str = None, days: int = 1
) -> DailySummary:
    """
    Create a summary for articles from a time window and optionally filtered by category.
    If date is not provided, process for yesterday (daily) or last N days (weekly).

    Args:
        db: Database session
        date: End date for summarization (defaults to yesterday)
        category: Optional category filter (e.g., 'business', 'technology', 'engineering')
        days: Number of days to summarize (1 for daily, 7 for weekly, etc.)

    Returns:
        Dictionary with summary data or None if no articles found
    """
    # Default behavior: process yesterday's calendar day. This ensures that
    # a run occurring in the early hours of the next day (e.g. 2025-11-04 04:30)
    # will summarize articles from 2025-11-03 (00:00–23:59) as requested.
    if date is None:
        date = datetime.utcnow() - timedelta(days=1)

    target_date = date if isinstance(date, datetime) else datetime.utcnow() - timedelta(days=1)

    # Fetch articles for the time window (with optional category filter)
    articles = fetch_articles_for_date(db, target_date, category=category, days=days)

    if not articles:
        category_str = f" in category '{category}'" if category else ""
        start_date = target_date - timedelta(days=days)
        logger.warning(
            f"No articles found from {start_date.date()} to {target_date.date()}{category_str}"
        )
        return None

    category_str = f" in category '{category}'" if category else ""
    start_date = target_date - timedelta(days=days)
    logger.info(
        f"Processing {len(articles)} articles{category_str} from {start_date.date()} to {target_date.date()}"
    )

    # Convert articles to format expected by summarizer
    article_dicts = [
        {
            "headline": article.headline,
            "website": article.website,
            "content": article.content or article.summary,
            "link": article.link,
        }
        for article in articles
    ]

    # Create summary using Grok
    summarizer = GrokSummarizer(db)
    summary_data = summarizer.summarize_articles(article_dicts)

    # Return the summary data instead of saving it to the database
    logger.info(
        f"Generated summary for {start_date.date()} to {target_date.date()}{category_str} with {len(articles)} articles"
    )
    # Store the date as midnight UTC for the day summarized to keep `daily_summaries.date`
    # consistent. Use target_date.replace(...) to zero-out time component.
    stored_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "date": stored_date,
        "summary_data": summary_data,
        "articles_count": len(articles),
        "model_name": summarizer.model_name,
        "category": category or "all",
    }
