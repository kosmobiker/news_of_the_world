import os
import logging
import requests
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from db.database import get_db
from models.models import DailySummary

# Initialize bot token
API_TOKEN = os.getenv("TG_API_KEY")
if not API_TOKEN:
    raise ValueError("TG_API_KEY is not set in the environment variables.")

CHAT_ID = os.getenv("CHAT_ID")
if not CHAT_ID:
    raise ValueError("CHAT_ID is not set in the environment variables.")

logging.basicConfig(level=logging.INFO)

def send_telegram_message(bot_token, chat_id, message):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message
    }
    response = requests.post(url, data=payload)
    return response.json()

def get_daily_summaries(db: Session):
    yesterday = datetime.utcnow().date() - timedelta(days=1)
    summaries = (
        db.query(DailySummary)
        .filter(DailySummary.date == yesterday)
        .all()
    )
    return [
        {
            'id': summary.id,
            'date': summary.date,
            'category': summary.category,
            'country': summary.country,
            'text_summary': summary.text_summary,
            'articles_count': summary.articles_count,
            'main_events': summary.main_events,
            'key_themes': summary.key_themes,
            'impacted_regions': summary.impacted_regions,
            'detailed_summary': summary.detailed_summary
        }
        for summary in summaries
    ]

def format_summary(summary):
    # Ensure the date is formatted correctly
    if isinstance(summary['date'], datetime):
        formatted_date = summary['date'].strftime("%B %d, %Y")
    else:
        formatted_date = datetime.strptime(summary['date'], "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y")

    formatted = (
        f"📅 Date: {formatted_date}\n"
        f"📂 Category: {summary['category']}\n"
        f"🌍 Country: {summary['country']}\n"
        f"📰 Articles Count: {summary['articles_count']}\n\n"
        f"📝 Summary:\n{summary['text_summary']}\n\n"
        f"🔑 Main Events:\n"
    )
    for key, event in summary['main_events'].items():
        formatted += f"  - {event}\n"
    formatted += "\n💡 Key Themes:\n"
    for key, theme in summary['key_themes'].items():
        formatted += f"  - {theme}\n"
    formatted += "\n🌎 Impacted Regions:\n"
    for key, region in summary.get('impacted_regions', {}).items():
        formatted += f"  - {region}\n"
    formatted += f"\n📖 Detailed Summary:\n{summary['detailed_summary']}\n"
    return formatted

def send_daily_summary():
    db = next(get_db())
    summaries = get_daily_summaries(db)
    if summaries:
        for summary in summaries:
            formatted_summary = format_summary(summary)
            response = send_telegram_message(API_TOKEN, CHAT_ID, formatted_summary)
            logging.info(f"Message sent: {response}")
    else:
        logging.info("No summaries available to send.")

if __name__ == "__main__":
    send_daily_summary()
