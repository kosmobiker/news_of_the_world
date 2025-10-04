"""Shared prompt building functionality for news summarization."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field


class SummarySchema(BaseModel):
    text_summary: str = Field(description="A concise one-sentence summary of the key points")
    detailed_summary: str = Field(description="A comprehensive multi-paragraph analysis")
    main_events: Dict[str, str] = Field(description="Key events in order of importance (max 5)")
    key_themes: Dict[str, str] = Field(description="Recurring themes or patterns (max 3)")
    impacted_regions: Dict[str, str] = Field(description="Countries/regions affected")
    timeline: Dict[str, str] = Field(description="Chronological events")


def format_articles_text(articles: List[Dict[str, Any]]) -> str:
    """Format a list of articles into a standardized text format."""
    return "\n\n".join(
        [
            f"Title: {article.get('headline', article.get('title', 'No title'))}\n"
            f"Source: {article.get('website', article.get('source', 'Unknown'))}\n"
            f"Content: {article.get('content', article.get('summary', 'No content'))}\n"
            for article in articles
        ]
    )


def build_summarization_prompt(articles: List[Dict[str, Any]]) -> str:
    """Build a standardized prompt for news summarization."""
    articles_text = format_articles_text(articles)

    prompt = f"""You are a news analyst tasked with summarizing multiple news articles. 
Think through this step by step:

1. First, identify the main events from each article
2. Look for common themes or patterns across articles
3. Note which regions or countries are mentioned
4. Create a chronological timeline if relevant
5. Write both a short and detailed summary

Articles to analyze:
{articles_text}

Provide your analysis in this exact JSON format:
{SummarySchema.schema_json(indent=2)}"""

    return prompt


def get_default_api_params() -> Dict[str, Any]:
    """Get the default API parameters for Grok."""
    return {"model": "grok-4-fast", "temperature": 0.3, "max_tokens": 4096}
