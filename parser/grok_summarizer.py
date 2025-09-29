from typing import List, Optional
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from db.database import Article, DailySummary

load_dotenv()

class GrokAPI:
    def __init__(self):
        self.api_key = os.getenv("GROK_API_KEY")
        if not self.api_key:
            raise ValueError("GROK_API_KEY environment variable is not set")
        
        self.base_url = "https://api.grok.com/v1"  # Replace with actual Grok API URL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def summarize_articles(self, articles: List[dict]) -> str:
        """
        Send articles to Grok API for summarization.
        """
        # Format articles for the prompt
        articles_text = "\n\n".join([
            f"Title: {article['headline']}\n"
            f"Source: {article['website']}\n"
            f"Content: {article.get('content', article.get('summary', 'No content'))}\n"
            for article in articles
        ])
        
        prompt = f"""Please provide a comprehensive summary of the following news articles. 
        Focus on main events, key developments, and common themes across articles.
        Include the most important details and any significant trends. Also provide 3 links to the
        most interesting articles if possible.

        Articles:
        {articles_text}
        
        Summary:"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "messages": [{"role": "user", "content": prompt}],
                        "model": "grok-4-fast",
                        "max_tokens": 2000
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"Failed to get summary from Grok API: {str(e)}")

def get_articles_for_date(db: Session, date: datetime, category: Optional[str] = None, country: Optional[str] = None) -> List[Article]:
    """Get articles for a specific date, optionally filtered by category and country."""
    query = db.query(Article).filter(
        and_(
            func.date(Article.published_at) == date.date(),
            Article.content.isnot(None)
        )
    )
    
    if category:
        query = query.filter(Article.category == category)
    if country:
        query = query.filter(Article.country == country)
    
    return query.all()

def get_dates_without_summaries(db: Session, start_date: datetime, end_date: datetime) -> List[datetime]:
    """Get dates that don't have summaries yet."""
    existing_summaries = db.query(
        func.date(DailySummary.date)
    ).filter(
        DailySummary.date.between(start_date, end_date)
    ).distinct().all()
    
    existing_dates = {summary[0] for summary in existing_summaries}
    all_dates = [start_date.date() + timedelta(days=x) for x in range((end_date.date() - start_date.date()).days + 1)]
    
    return [datetime.combine(d, datetime.min.time()) for d in all_dates if d not in existing_dates]

async def create_daily_summaries(db: Session, date: datetime, grok_api: GrokAPI):
    """Create summaries for a specific date."""
    # Get all articles for the date
    articles = get_articles_for_date(db, date)
    if not articles:
        return
    
    # Group articles by category and country
    categories = {a.category for a in articles if a.category}
    countries = {a.country for a in articles if a.country}
    
    # Create overall summary
    all_articles = [{
        'headline': a.headline,
        'website': a.website,
        'content': a.content or a.summary,
    } for a in articles]
    
    overall_summary = await grok_api.summarize_articles(all_articles)
    
    # Create and save the summary
    summary = DailySummary(
        date=date,
        category=None,  # Overall summary
        country=None,  # Overall summary
        summary=overall_summary,
        articles_count=len(articles),
        model_name="grok"
    )
    db.add(summary)
    
    # Create summaries for each category
    for category in categories:
        if not category:
            continue
        
        category_articles = [{
            'headline': a.headline,
            'website': a.website,
            'content': a.content or a.summary,
        } for a in articles if a.category == category]
        
        category_summary = await grok_api.summarize_articles(category_articles)
        
        summary = DailySummary(
            date=date,
            category=category,
            country=None,
            summary=category_summary,
            articles_count=len(category_articles),
            model_name="grok"
        )
        db.add(summary)
    
    # Create summaries for each country
    for country in countries:
        if not country:
            continue
        
        country_articles = [{
            'headline': a.headline,
            'website': a.website,
            'content': a.content or a.summary,
        } for a in articles if a.country == country]
        
        country_summary = await grok_api.summarize_articles(country_articles)
        
        summary = DailySummary(
            date=date,
            category=None,
            country=country,
            summary=country_summary,
            articles_count=len(country_articles),
            model_name="grok"
        )
        db.add(summary)
    
    db.commit()
