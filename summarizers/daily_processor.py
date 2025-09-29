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

    # Create daily summary record
    daily_summary = DailySummary(
        date=start_date,
        text_summary=summary_data.get("text_summary", ""),
        detailed_summary=summary_data.get("detailed_summary", ""),
        main_events=summary_data.get("main_events", {}),
        key_themes=summary_data.get("key_themes", {}),
        impacted_regions=summary_data.get("impacted_regions", {}),
        timeline=summary_data.get("timeline", {}),
        articles_count=len(articles),
        generated_at=datetime.utcnow(),
        model_name=summarizer.model_name,
        raw_json=summary_data,
        category="news",  # Default category
        country="global"  # Default country
    )

    # Check if a summary already exists for the same date, category, and country
    existing_summary = (
        db.query(DailySummary)
        .filter(DailySummary.date == start_date)
        .filter(DailySummary.category == "news")  # Default category
        .filter(DailySummary.country == "global")  # Default country
        .first()
    )

    if existing_summary:
        logger.info(f"Summary for {start_date.date()} already exists")
        return existing_summary

    # Ensure no duplicate insertion
    if db.query(DailySummary).filter_by(date=start_date, category="news", country="global").first():
        logger.warning("Duplicate summary detected. Skipping insertion.")
        return None

    db.add(daily_summary)
    db.commit()
    db.refresh(daily_summary)

    logger.info(f"Created summary for {start_date.date()} with {len(articles)} articles")
    return daily_summary
