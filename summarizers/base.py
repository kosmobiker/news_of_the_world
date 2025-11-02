"""Base interface for all summarizer implementations."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from datetime import datetime


class NewsSummarizer(ABC):
    """Abstract base class for news summarizers."""

    @abstractmethod
    def summarize_articles(self, articles: List[Dict[str, Any]]) -> str:
        """
        Generate a summary for a list of articles.

        Args:
            articles: List of article dictionaries with headline, website, and content

        Returns:
            str: Generated summary
        """
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the name of the summarization model."""
        pass
