"""Shared prompt building functionality for news summarization."""

from typing import List, Dict, Any
from pydantic import BaseModel, Field
import json


class SummarySchema(BaseModel):
    text_summary: str = Field(description="A concise one-sentence summary of the key points")
    detailed_summary: str = Field(description="A comprehensive multi-paragraph analysis")
    main_events: Dict[str, str] = Field(description="Key events in order of importance (max 5)")
    key_themes: Dict[str, str] = Field(description="Recurring themes or patterns (max 3)")
    impacted_regions: Dict[str, str] = Field(description="Countries/regions affected")
    timeline: Dict[str, str] = Field(description="Chronological events")
    top_articles: List[Dict[str, str]] = Field(
        description="Top 10 most relevant articles with title, source, and link"
    )


def format_articles_text(articles: List[Dict[str, Any]]) -> str:
    """Format a list of articles into a standardized text format with links."""
    return "\n\n".join(
        [
            f"Title: {article.get('headline', article.get('title', 'No title'))}\n"
            f"Source: {article.get('website', article.get('source', 'Unknown'))}\n"
            f"Link: {article.get('link', 'No link available')}\n"
            f"Content: {article.get('content', article.get('summary', 'No content'))}\n"
            for article in articles
        ]
    )


def build_summarization_prompt(articles: List[Dict[str, Any]]) -> str:
    """Build a standardized prompt for news summarization."""
    articles_text = format_articles_text(articles)

    # More explicit and constrained prompt to improve LLM output quality.
    prompt = f"""
You are a professional, neutral, and concise news analyst. Your job is to read the provided articles and produce a structured JSON report describing the reportage's facts, interpretation, and key metadata.

Rules and constraints (MUST follow exactly):
1) Output: Return ONLY a single JSON object and nothing else. Do not include backticks, explanation, preamble, or trailing text.
2) Schema: The JSON must conform to the following Pydantic schema exactly (field names and types). Use empty strings or empty objects where information is missing.
3) Length and style:
   - `text_summary`: one sentence, maximum 30 words, objective and non-opinionated.
   - `detailed_summary`: 2–5 paragraphs. Each paragraph should be 2–5 sentences long. Use neutral, factual language and cite article titles in parentheses when summarizing where appropriate.
   - `main_events`: up to 5 key events, ordered by importance. Each key is a short label (10 words max) and the value is a concise description (1–3 sentences).
   - `key_themes`: up to 3 themes. Each key is a short phrase and the value is a short explanation linking evidence from the articles.
   - `impacted_regions`: list countries/regions mentioned, with one-line notes about the nature of impact.
   - `timeline`: chronological map with short date or relative time keys and 1–2 sentence descriptions.
   - `top_articles`: a list of up to 10 most relevant articles. Each entry is an object with keys "title" (headline), "source" (website), and "link" (URL). Order by relevance to the key events and themes.

Instructions for analysis (stepwise):
1. Quickly extract the factual claims (who, what, when, where) from each article.
2. Normalize named entities (countries, organizations) to a canonical short form.
3. Detect and collapse near-duplicate events across articles into a single `main_events` entry and note sources in the description.
4. Identify recurring themes across articles (political, economic, humanitarian, security, engineering, environmental).
5. Construct a simple chronological `timeline` using explicit dates when present; otherwise use relative markers (e.g., "Day 1", "Earlier this week").
6. Identify the top 10 most relevant articles by relevance to main events and key themes. Extract their title, source, and link. Preserve the exact links provided in the input.
7. Produce `text_summary` then `detailed_summary` using only the facts and aggregated evidence from the articles.

If a field cannot be populated, return an empty string for text fields, an empty object/dict for mapping fields, or an empty array for `top_articles`.

Articles to analyze (do not modify article text):
{articles_text}

Return JSON conforming exactly to this schema:
{json.dumps(SummarySchema.model_json_schema(), indent=2)}
"""

    return prompt


def get_default_api_params() -> Dict[str, Any]:
    """Get the default API parameters for Grok."""
    return {"model": "grok-4-1-fast-reasoning", "temperature": 0.3, "max_tokens": 4096}
