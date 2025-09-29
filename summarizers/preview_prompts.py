"""Simple script to preview prompts that would be sent to Grok API."""
from datetime import datetime, timedelta
from db.database import SessionLocal, Article
from sqlalchemy import func
import json

def get_articles_for_date(db, date):
    """Get articles for a specific date."""
    return db.query(Article).filter(
        func.date(Article.published_at) == date.date(),
        Article.content.isnot(None)
    ).all()

def format_prompt(articles):
    """Format articles into a prompt that would be sent to Grok."""
    articles_text = "\n\n".join([
        f"Title: {article.headline}\n"
        f"Source: {article.website}\n"
        f"Content: {article.content or article.summary}\n"
        for article in articles
    ])
    
    prompt = f"""Analyze and summarize the following news articles.

Articles:
{articles_text}

Provide a structured summary in the following JSON format:
{{
    "main_events": [
        // List of major events or developments, max 5 items
    ],
    "key_themes": [
        // Common themes or trends across articles, max 3 items
    ],
    "detailed_summary": "A comprehensive paragraph summarizing the key points",
    "impacted_regions": [
        // List of affected countries/regions mentioned
    ],
    "timeline": {{
        // Optional timeline of events if relevant
    }}
}}

Ensure the response is valid JSON and follows these guidelines:
- main_events: Key events in order of importance (max 5)
- key_themes: Recurring themes or patterns (max 3)
- detailed_summary: One paragraph overview
- impacted_regions: Countries/regions affected
- timeline: Optional chronological events"""

    return prompt

def print_prompt_preview(date=None):
    """Print a preview of the prompt that would be sent to Grok."""
    if date is None:
        date = datetime.now()
    
    db = SessionLocal()
    try:
        articles = get_articles_for_date(db, date)
        
        if not articles:
            print(f"No articles found for date: {date.date()}")
            return
        
        print(f"\nFound {len(articles)} articles for {date.date()}")
        print("\nPrompt that would be sent to Grok:")
        print("=" * 80)
        print(format_prompt(articles))
        print("=" * 80)
        
        # Print example API parameters
        api_params = {
            "model": "grok-4-fast",
            "max_tokens": 2048,
            "temperature": 0.3,
            "response_format": { "type": "json_object" }
        }
        print("\nAPI Parameters:")
        print(json.dumps(api_params, indent=2))
        
    finally:
        db.close()

if __name__ == "__main__":
    # Preview prompt for today
    print("Today's prompt:")
    print_prompt_preview()
    
    # Preview prompt for yesterday
    print("\nYesterday's prompt:")
    print_prompt_preview(datetime.now() - timedelta(days=1))
