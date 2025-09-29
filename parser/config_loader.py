import yaml
from typing import List, Dict, Any
from models.models import FeedsConfig, FeedConfig, ParserSettings
import os

def load_feeds_config(config_path: str = "feeds.yaml") -> FeedsConfig:
    """Load RSS feeds configuration from YAML file."""
    try:
        # Convert to absolute path if it's relative
        if not os.path.isabs(config_path):
            config_path = os.path.join(os.path.dirname(__file__), config_path)
        
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file {config_path} not found")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        # Parse feeds
        feeds_dict = {}
        for category, feeds_list in data['feeds'].items():
            feeds_dict[category] = [FeedConfig(**feed) for feed in feeds_list]
        
        # Parse settings
        settings = ParserSettings(**data.get('settings', {}))
        
        return FeedsConfig(feeds=feeds_dict, settings=settings)
    
    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise

def get_enabled_feeds(config: FeedsConfig) -> List[FeedConfig]:
    """Get all enabled feeds from configuration."""
    enabled_feeds = []
    
    for category, feeds in config.feeds.items():
        for feed in feeds:
            if feed.enabled:
                enabled_feeds.append(feed)
    
    return enabled_feeds

def get_feeds_by_category(config: FeedsConfig, category: str) -> List[FeedConfig]:
    """Get feeds filtered by category."""
    return [feed for feed in config.feeds.get(category, []) if feed.enabled]

def get_feeds_by_language(config: FeedsConfig, language: str) -> List[FeedConfig]:
    """Get feeds filtered by language."""
    enabled_feeds = get_enabled_feeds(config)
    return [feed for feed in enabled_feeds if feed.language == language]

def update_feed_status(config_path: str, feed_name: str, enabled: bool):
    """Update feed enabled status in YAML file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
        
        # Find and update the feed
        for category, feeds in data['feeds'].items():
            for feed in feeds:
                if feed['name'] == feed_name:
                    feed['enabled'] = enabled
                    break
        
        # Write back to file
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(data, file, default_flow_style=False, allow_unicode=True)
            
        print(f"Updated {feed_name} enabled status to {enabled}")
        
    except Exception as e:
        print(f"Error updating feed status: {e}")