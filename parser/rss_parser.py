from dotenv import load_dotenv
import os
import feedparser
from datetime import datetime
from typing import List, Dict, Optional, NamedTuple
import langdetect
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.models import Article, FeedStatus, ArticleCreate, FeedConfig
from parser.config_loader import load_feeds_config, get_enabled_feeds
from db.database import SessionLocal, get_db

load_dotenv()


class ParseResult(NamedTuple):
    """Result of parsing a feed."""

    processed: int
    errors: int


def parse_feed(db: Session, feed_config: FeedConfig) -> ParseResult:
    """Parse a single RSS feed and save articles to database."""
    try:
        feed = feedparser.parse(feed_config.url)

        # Check for critical HTTP errors (4xx/5xx excluding 301/302 redirects)
        status = getattr(feed, "status", 200)
        if status and status >= 400:
            error_msg = f"HTTP error {status} fetching feed"
            update_feed_status(
                db, feed_config.name, feed_config.url, success=False, error=error_msg
            )
            return ParseResult(processed=0, errors=1)

        # Bozo errors are non-fatal if we have entries to parse
        # (e.g., minor XML issues, incomplete feeds)
        # Only fail if we have no entries AND a serious bozo exception
        if getattr(feed, "bozo", False) is True and len(feed.entries) == 0:
            error_msg = (
                str(getattr(feed, "bozo_exception", "Unknown parsing error"))
                if getattr(feed, "bozo_exception", None)
                else "Unknown parsing error"
            )
            update_feed_status(
                db, feed_config.name, feed_config.url, success=False, error=error_msg
            )
            return ParseResult(processed=0, errors=1)

        new_articles = process_feed_entries(db, feed.entries, feed_config)
        update_feed_status(
            db, feed_config.name, feed_config.url, success=True, articles_count=len(new_articles)
        )

        return ParseResult(processed=len(new_articles), errors=0)

    except Exception as e:
        error_msg = f"Error parsing feed: {str(e)}"
        update_feed_status(db, feed_config.name, feed_config.url, success=False, error=error_msg)
        return ParseResult(processed=0, errors=1)


def process_feed_entries(
    db: Session, entries: List[Dict], feed_config: FeedConfig
) -> List[Article]:
    """Process feed entries and save new articles to database."""
    new_articles = []

    for entry in entries:
        try:
            # Extract fields
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            published_at = datetime(*published[:6]) if published else datetime.now()

            # Try to detect language
            content = entry.get("content", [{"value": entry.get("description", "")}])[0]["value"]
            try:
                language = langdetect.detect(content)
            except:
                # coerce feed_config.language to string in case tests pass a MagicMock
                language = str(getattr(feed_config, "language", "unknown"))
            # ensure language is a string
            language = str(language) if language is not None else "unknown"

            # Create article
            # Coerce feed_config fields to plain strings to satisfy Pydantic validators
            feed_name = str(getattr(feed_config, "name", ""))
            category = str(getattr(feed_config, "category", ""))
            country = str(getattr(feed_config, "country", ""))

            article = ArticleCreate(
                website=feed_name,
                headline=entry.get("title", "No title"),
                summary=entry.get("description"),
                content=content,
                link=entry.get("link", ""),
                published_at=published_at,
                language=language,
                feed_name=feed_name,
                category=category,
                country=country,
            )

            # Check for duplicates using content hash
            content_hash = article.generate_hash()
            existing = db.query(Article).filter_by(content_hash=content_hash).first()

            if not existing:
                db_article = Article(
                    website=article.website,
                    headline=article.headline,
                    summary=article.summary,
                    content=article.content,
                    link=article.link,
                    published_at=article.published_at,
                    language=article.language,
                    content_hash=content_hash,
                    feed_name=article.feed_name,
                    category=article.category,
                    country=article.country,
                )
                db.add(db_article)
                db.commit()
                db.refresh(db_article)
                new_articles.append(db_article)

        except Exception as e:
            print(f"Error processing entry: {str(e)}")
            continue

    return new_articles


def update_feed_status(
    db: Session,
    feed_name: str,
    feed_url: str,
    success: bool = True,
    error: Optional[str] = None,
    articles_count: Optional[int] = None,
) -> FeedStatus:
    """Update the status of a feed after parsing."""
    status = db.query(FeedStatus).filter_by(feed_name=feed_name).first()

    if not status:
        status = FeedStatus(feed_name=feed_name, feed_url=feed_url, is_active=True)
        db.add(status)

    status.last_parsed_at = datetime.now()
    if success:
        status.last_success_at = datetime.now()
        if articles_count is not None:
            status.articles_count = articles_count

    db.commit()
    db.refresh(status)
    return status


def main():
    print("Starting RSS feed parsing from YAML configuration...")

    # Initialize stats as a dictionary to track parsing statistics
    stats = {"total_parsed": 0, "new_articles": 0, "duplicates": 0, "errors": 0}

    # Load feeds configuration
    config = load_feeds_config("feeds.yaml")

    # Initialize database session
    db = next(get_db())

    # Parse feeds and update stats
    for feed_config in get_enabled_feeds(config):
        result = parse_feed(db, feed_config)
        stats["total_parsed"] += result.processed
        stats["errors"] += result.errors

    print(f"\n=== Parsing Results ===")
    print(f"Total parsed: {stats['total_parsed']}")
    print(f"New articles: {stats['new_articles']}")
    print(f"Duplicates skipped: {stats['duplicates']}")
    print(f"Errors: {stats['errors']}")

    # Show database statistics
    db = next(get_db())

    total_articles = db.query(func.count(Article.id)).scalar()
    categories = db.query(func.count(func.distinct(Article.category))).scalar()
    countries = db.query(func.count(func.distinct(Article.country))).scalar()

    print(f"\n=== Database Stats ===")
    print(f"Total articles in DB: {total_articles}")
    print(f"Categories: {categories}")
    print(f"Countries: {countries}")

    # Show articles by category
    category_counts = (
        db.query(Article.category, func.count(Article.id).label("count"))
        .group_by(Article.category)
        .all()
    )

    print("\nArticles by category:")
    for category, count in category_counts:
        print(f"  {category}: {count}")

    # Show feed status
    feed_statuses = db.query(FeedStatus).all()

    print(f"\n=== Feed Status ===")
    for status in feed_statuses:
        last_success = (
            status.last_success_at.strftime("%Y-%m-%d %H:%M") if status.last_success_at else "Never"
        )
        print(
            f"  {status.feed_name}: {status.articles_count or 0} articles, last success: {last_success}"
        )

    db.close()


if __name__ == "__main__":
    main()
