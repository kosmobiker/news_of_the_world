from pydantic import BaseModel, validator
from datetime import datetime
from typing import Optional, List, Dict
import hashlib
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    website = Column(String(255), nullable=False, index=True)
    headline = Column(String(500), nullable=False)
    published_at = Column(DateTime, nullable=True, index=True)
    parsed_at = Column(DateTime, default=datetime.now, nullable=False)
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    language = Column(String(10), default="unknown", index=True)
    link = Column(String(1000), nullable=False)
    content_hash = Column(String(32), unique=True, index=True)

    # New fields from YAML config
    feed_name = Column(String(255), nullable=True, index=True)
    category = Column(String(100), nullable=True, index=True)
    country = Column(String(10), nullable=True, index=True)

    __table_args__ = (
        Index("idx_website_published", "website", "published_at"),
        Index("idx_published_language", "published_at", "language"),
        Index("idx_category_country", "category", "country"),
    )


class FeedStatus(Base):
    __tablename__ = "feed_status"

    id = Column(Integer, primary_key=True, index=True)
    feed_name = Column(String(255), nullable=False, unique=True)
    feed_url = Column(String(1000), nullable=False)
    last_parsed_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    articles_count = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=True)
    # error_count = Column(Integer, nullable=True)
    # last_error = Column(Text, nullable=True)

    def __repr__(self):
        return f"<FeedStatus(feed_name={self.feed_name}, last_success={self.last_success_at})>"


class DailySummary(Base):
    __tablename__ = "daily_summaries"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    category = Column(String(100), index=True)
    country = Column(String(10), index=True)
    text_summary = Column(Text, nullable=False)
    articles_count = Column(Integer, nullable=False)
    generated_at = Column(DateTime, nullable=False)
    model_name = Column(String(50), nullable=False)
    main_events = Column(JSONB)
    key_themes = Column(JSONB)
    detailed_summary = Column(Text)
    impacted_regions = Column(JSONB)
    timeline = Column(JSONB)
    top_articles = Column(JSONB)
    raw_json = Column(JSONB)
    error_count = Column(Integer)
    last_error = Column(Text)

    __table_args__ = (
        Index("idx_daily_summaries_impacted_regions", "impacted_regions", postgresql_using="gin"),
        Index("idx_daily_summaries_key_themes", "key_themes", postgresql_using="gin"),
        Index("idx_daily_summaries_main_events", "main_events", postgresql_using="gin"),
        Index("idx_date_category_country", "date", "category", "country", unique=True),
    )

    def __repr__(self):
        return f"<DailySummary(id={self.id}, date={self.date}, category={self.category}, country={self.country})>"


class FeedConfig(BaseModel):
    name: str
    url: str
    category: str
    country: str
    language: str
    enabled: bool = True


class ParserSettings(BaseModel):
    delay_between_feeds: float = 1.0
    max_articles_per_feed: int = 100
    timeout: int = 30
    retry_attempts: int = 3
    user_agent: str = "RSS Parser Bot 1.0"


class FeedsConfig(BaseModel):
    feeds: Dict[str, List[FeedConfig]]
    settings: ParserSettings


class ArticleCreate(BaseModel):
    website: str
    headline: str
    published_at: Optional[datetime] = None
    summary: Optional[str] = None
    content: Optional[str] = None
    language: str = "unknown"
    link: str
    feed_name: Optional[str] = None
    category: Optional[str] = None
    country: Optional[str] = None
    parsed_at: datetime = datetime.now()

    @validator("content", "summary")
    def truncate_long_text(cls, v):
        if v and len(v) > 10000:
            return v[:10000] + "..."
        return v

    def generate_hash(self) -> str:
        """Generate unique hash for duplicate detection"""
        content = f"{self.website}{self.headline}{self.link}"
        return hashlib.md5(content.encode()).hexdigest()
