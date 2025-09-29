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

def fetch_articles_for_date(db: Session, start_date: datetime, end_date: datetime):
    """
    Fetch articles from the database within the specified date range.
    """
    return (
        db.query(Article)
        .filter(Article.published_at >= start_date)
        .filter(Article.published_at < end_date)
        .order_by(Article.published_at.desc())
        .all()
    )

def process_daily_summary(db: Session, date: datetime = None) -> DailySummary:
    """
    Create a summary for all articles from a specific date.
    If date is not provided, process for today.
    """
    if date is None:
        date = datetime.utcnow()

    # Get the date range for the entire day
    start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    # Fetch articles for the date
    articles = fetch_articles_for_date(db, start_date, end_date)

    if not articles:
        logger.warning(f"No articles found for {start_date.date()}")
        return None

    logger.info(f"Processing {len(articles)} articles for {start_date.date()}")

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
    logger.info(f"Generated summary for {start_date.date()} with {len(articles)} articles")
    return {
        "date": start_date,
        "summary_data": summary_data,
        "articles_count": len(articles),
        "model_name": summarizer.model_name
    }
