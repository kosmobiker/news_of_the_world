"""Grok-based implementation of news summarization."""
from typing import List, Dict, Any
import os
import json
from dotenv import load_dotenv
from xai_sdk import Client
from xai_sdk.chat import user, system
from .base import NewsSummarizer
from sqlalchemy.orm import Session
from models.models import GrokInteraction
import logging
from pydantic import BaseModel, Field

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SummarySchema(BaseModel):
    text_summary: str = Field(description="A concise one-sentence summary of the key points")
    detailed_summary: str = Field(description="A comprehensive multi-paragraph analysis")
    main_events: Dict[str, str] = Field(description="Key events in order of importance (max 5)")
    key_themes: Dict[str, str] = Field(description="Recurring themes or patterns (max 3)")
    impacted_regions: Dict[str, str] = Field(description="Countries/regions affected")
    timeline: Dict[str, str] = Field(description="Chronological events")

class GrokSummarizer(NewsSummarizer):
    """Grok-based implementation of news summarization."""
    
    def __init__(self, db: Session):
        self.api_key = os.getenv("XAI_API_KEY")
        if not self.api_key:
            raise ValueError("XAI_API_KEY environment variable is not set")
        
        self.client = Client(api_key=self.api_key)
        self.db = db
    
    @property
    def model_name(self) -> str:
        return "grok"
    
    def summarize_articles(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Send articles to Grok API for summarization using structured reasoning approach.
        """
        articles_text = "\n\n".join([
            f"Title: {article['headline']}\n"
            f"Source: {article['website']}\n"
            f"Content: {article.get('content', article.get('summary', 'No content'))}\n"
            for article in articles
        ])

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

        try:
            chat = self.client.chat.create(model="grok-4")
            chat.append(system("You are a news analyst expert at structured summarization. Be concise and focus on key points."))
            chat.append(user(prompt))

            response, parsed_summary = chat.parse(SummarySchema)
            return parsed_summary.dict()
        except Exception as e:
            error_msg = f"Failed to get summary from Grok API: {str(e)}"
            logger.error(error_msg)
            return {
                "text_summary": "",
                "detailed_summary": "Error processing response",
                "main_events": {},
                "key_themes": {},
                "impacted_regions": {},
                "timeline": {},
                "error": error_msg
            }
