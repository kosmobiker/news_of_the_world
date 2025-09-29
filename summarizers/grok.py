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
from .prompt_builder import SummarySchema, build_summarization_prompt, get_default_api_params

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        # Use shared prompt builder
        prompt = build_summarization_prompt(articles)

        try:
            api_params = get_default_api_params()
            chat = self.client.chat.create(**api_params)
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
