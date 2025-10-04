"""Simple script to preview prompts that would be sent to Grok API."""

from datetime import datetime, timedelta
from db.database import SessionLocal, Article
from sqlalchemy import func
import json
from dotenv import load_dotenv

# Use shared prompt builder
from prompt_builder import build_summarization_prompt, get_default_api_params


def get_articles_for_date(db, date):
    """Get articles for a specific date."""
    return (
        db.query(Article)
        .filter(func.date(Article.published_at) == date.date(), Article.content.isnot(None))
        .all()
    )


def articles_to_dicts(articles):
    """Convert ORM Article objects to plain dicts for the prompt builder."""
    result = []
    for a in articles:
        result.append(
            {
                "headline": getattr(a, "headline", None) or getattr(a, "title", None),
                "website": getattr(a, "website", getattr(a, "source", None)),
                "content": getattr(a, "content", None) or getattr(a, "summary", None),
            }
        )
    return result


def format_prompt(articles):
    """Format articles into a prompt using the shared prompt builder."""
    article_dicts = articles_to_dicts(articles)
    return build_summarization_prompt(article_dicts)


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
        print("\n")
        prompt = format_prompt(articles)
        print(prompt)
        print("\n")

        # Print example API parameters (from shared defaults)
        api_params = get_default_api_params()
        # add response_format for preview
        api_params["response_format"] = {"type": "json_object"}
        print("\nAPI Parameters:")
        print(json.dumps(api_params, indent=2))
    finally:
        db.close()


if __name__ == "__main__":
    load_dotenv()

    # Preview prompt for today
    print("Today's prompt:")
    print_prompt_preview()

    # Preview prompt for yesterday
    print("\nYesterday's prompt:")
    print_prompt_preview(datetime.now() - timedelta(days=1))
