import os
import logging
import time
import requests
from datetime import datetime, timedelta, timezone
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

# Telegram limits
TG_MAX_MESSAGE_CHARS = 4096


def _split_message(message: str, limit: int = TG_MAX_MESSAGE_CHARS):
    """Split message into chunks not exceeding `limit`, preferring paragraph boundaries."""
    if len(message) <= limit:
        return [message]

    paragraphs = message.split("\n\n")
    chunks = []
    current = []
    cur_len = 0

    for p in paragraphs:
        piece = p + "\n\n"
        if cur_len + len(piece) <= limit:
            current.append(piece)
            cur_len += len(piece)
        else:
            if current:
                chunks.append("".join(current).rstrip())
            # paragraph itself might be larger than limit
            if len(piece) > limit:
                # hard split the paragraph
                for i in range(0, len(piece), limit):
                    chunks.append(piece[i : i + limit])
                current = []
                cur_len = 0
            else:
                current = [piece]
                cur_len = len(piece)

    if current:
        chunks.append("".join(current).rstrip())

    return chunks


def _send_document(bot_token: str, chat_id: str, text: str):
    """Send long text as a .txt document via sendDocument endpoint."""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    files = {"document": ("summary.txt", text.encode("utf-8"))}
    data = {"chat_id": chat_id}
    resp = requests.post(url, data=data, files=files, timeout=30)
    try:
        return resp.json()
    except Exception:
        return {"ok": False, "error": "invalid-json-response", "status_code": resp.status_code}


def send_telegram_message(bot_token, chat_id, message, max_retries: int = 3):
    """Send message to Telegram with retries, chunking and fallback to document.

    Returns the last Telegram response JSON.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    chunks = _split_message(message, TG_MAX_MESSAGE_CHARS)
    last_resp = None

    for idx, chunk in enumerate(chunks):
        attempt = 0
        while attempt < max_retries:
            payload = {"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"}
            try:
                resp = requests.post(url, data=payload, timeout=30)
            except requests.RequestException as e:
                logging.warning(
                    f"Network error sending Telegram message (attempt {attempt + 1}): {e}"
                )
                attempt += 1
                continue

            last_resp = None
            try:
                last_resp = resp.json()
            except Exception:
                last_resp = {
                    "ok": False,
                    "error": "invalid-json-response",
                    "status_code": resp.status_code,
                }

            # Handle common cases
            if resp.status_code == 200 and last_resp.get("ok"):
                break  # success for this chunk

            # Bad Request - message too long or malformed -> try fallback
            if resp.status_code == 400:
                descr = last_resp.get("description", "")
                logging.error(f"Telegram 400: {descr}")
                # If message too long, fallback to sending as document for remaining content
                if "message is too long" in descr.lower() or len(chunk) > TG_MAX_MESSAGE_CHARS:
                    remaining = "\n\n".join(chunks[idx:])
                    return _send_document(bot_token, chat_id, remaining)
                else:
                    return last_resp

            # Unauthorized
            if resp.status_code == 401:
                logging.error("Telegram 401 Unauthorized - check TG_API_KEY")
                return last_resp

            # Too many requests - respect retry-after
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 5))
                logging.warning(f"Telegram rate limited, retrying after {retry_after}s")
                time.sleep(retry_after)
                attempt += 1
                continue

            # Server errors - backoff and retry
            if 500 <= resp.status_code < 600:
                backoff = 2**attempt
                logging.warning(f"Telegram server error {resp.status_code}, backing off {backoff}s")
                time.sleep(backoff)
                attempt += 1
                continue

            # If response contains ok:false with description, log and stop
            if last_resp and not last_resp.get("ok"):
                logging.error(f"Telegram error: {last_resp}")
                return last_resp

            attempt += 1

    return last_resp or {"ok": False, "error": "no-response"}


def get_daily_summaries(db: Session):
    # Use timezone-aware UTC to compute yesterday
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()
    summaries = db.query(DailySummary).filter(DailySummary.date == yesterday).all()
    return [
        {
            "id": summary.id,
            "date": summary.date,
            "category": summary.category,
            "country": summary.country,
            "text_summary": summary.text_summary,
            "articles_count": summary.articles_count,
            "main_events": summary.main_events,
            "key_themes": summary.key_themes,
            "detailed_summary": summary.detailed_summary,
            "top_articles": summary.top_articles,
        }
        for summary in summaries
    ]


def format_summary(summary):
    # Ensure the date is formatted correctly
    if isinstance(summary["date"], datetime):
        formatted_date = summary["date"].strftime("%B %d, %Y")
    else:
        formatted_date = datetime.strptime(summary["date"], "%Y-%m-%d %H:%M:%S").strftime(
            "%B %d, %Y"
        )

    formatted = (
        f"📅 Date: {formatted_date}\n"
        f"📂 Category: {summary['category']}\n"
        f"🌍 Country: {summary['country']}\n"
        f"📰 Articles Count: {summary['articles_count']}\n\n"
        f"📝 Summary:\n{summary['text_summary']}\n\n"
        f"🔑 Main Events:\n"
    )
    for key, event in summary["main_events"].items():
        formatted += f"  - {event}\n"
    formatted += "\n💡 Key Themes:\n"
    for key, theme in summary["key_themes"].items():
        formatted += f"  - {theme}\n"
    # Detailed summary (raw)
    detailed = summary.get("detailed_summary") or ""
    formatted += f"\n📖 Detailed Summary:\n{detailed}\n"

    # Add top articles as clickable hyperlinks
    top_articles = summary.get("top_articles") or []
    if top_articles:
        formatted += "\n🔗 Top Articles:\n"
        for idx, article in enumerate(top_articles[:10], 1):
            title = article.get("title", "Article")
            source = article.get("source", "Unknown")
            link = article.get("link", "")
            if link:
                # Format as Markdown hyperlink: [text](url)
                formatted += f"  {idx}. [{title} - {source}]({link})\n"
            else:
                formatted += f"  {idx}. {title} - {source}\n"

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
