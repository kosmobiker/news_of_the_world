"""Command-line interface for running news summarization."""

from datetime import datetime
import argparse
from db.database import SessionLocal
from summarizers.daily_processor import process_daily_summary
from models.models import DailySummary  # Import the DailySummary model

# Default time window (in days) for each category
DEFAULT_TIME_WINDOWS = {
    "business": 1,      # Daily
    "technology": 1,    # Daily
    "engineering": 7,   # Weekly
}


def save_summary_to_db(db, summary, category):
    """Helper function to save a summary to the database."""
    # Check if a summary already exists for the same date, category, and country
    existing_summary = (
        db.query(DailySummary)
        .filter(DailySummary.date == summary["date"])
        .filter(DailySummary.category == category)
        .filter(DailySummary.country == "global")  # Default country
        .first()
    )

    if existing_summary:
        print(f"Summary for {summary['date']} in category '{category}' already exists in the database.")
        return False
    else:
        # Insert the new summary into the database
        new_summary = DailySummary(
            date=summary["date"],
            text_summary=summary["summary_data"].get("text_summary", ""),
            detailed_summary=summary["summary_data"].get("detailed_summary", ""),
            main_events=summary["summary_data"].get("main_events", {}),
            key_themes=summary["summary_data"].get("key_themes", {}),
            impacted_regions=summary["summary_data"].get("impacted_regions", {}),
            timeline=summary["summary_data"].get("timeline", {}),
            top_articles=summary["summary_data"].get("top_articles", []),
            articles_count=summary["articles_count"],
            generated_at=datetime.utcnow(),
            model_name=summary["model_name"],
            raw_json=summary["summary_data"],
            category=category,
            country="global",
        )

        db.add(new_summary)
        db.commit()
        db.refresh(new_summary)
        print(f"✓ Inserted {category.upper()} summary for {summary['date']} into the database.")
        return True


def main():
    """Process summaries for articles with configurable time windows."""
    parser = argparse.ArgumentParser(description="Process news summaries by category with configurable time windows")
    parser.add_argument(
        "--date",
        type=str,
        help="Date to process (YYYY-MM-DD format). Defaults to yesterday.",
        required=False,
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        help="Categories to process (e.g., business technology engineering). If not specified, processes: business (daily), technology (daily), engineering (weekly).",
        required=False,
        default=["business", "technology", "engineering"],
    )
    parser.add_argument(
        "--days",
        type=int,
        nargs="+",
        help="Time window in days for each category (e.g., --days 1 1 7 for business:daily, technology:daily, engineering:weekly). Must match number of categories.",
        required=False,
    )
    args = parser.parse_args()

    # Validate days argument if provided
    if args.days:
        if len(args.days) != len(args.categories):
            print(f"Error: Number of --days values ({len(args.days)}) must match number of --categories ({len(args.categories)})")
            return
        time_windows = dict(zip(args.categories, args.days))
    else:
        # Use default time windows
        time_windows = {cat: DEFAULT_TIME_WINDOWS.get(cat, 1) for cat in args.categories}

    # Parse date if provided, otherwise use yesterday
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d")
        except ValueError:
            print("Error: Date must be in YYYY-MM-DD format")
            return

    # Display configuration
    config_str = ", ".join([f"{cat} ({time_windows[cat]}d)" for cat in args.categories])
    print(f"Starting news summarization for: {config_str}...")

    try:
        db = SessionLocal()
        
        summaries_created = 0
        for category in args.categories:
            days = time_windows[category]
            window_type = "daily" if days == 1 else f"weekly ({days}d)"
            print(f"\n--- Processing {category.upper()} category ({window_type}) ---")
            summary = process_daily_summary(db, target_date, category=category, days=days)
            
            if summary:
                if save_summary_to_db(db, summary, category):
                    summaries_created += 1
            else:
                print(f"No articles found to summarize for {category} category.")
        
        if summaries_created > 0:
            print(f"\n✓ Successfully created {summaries_created} summaries.")
        else:
            print("\nNo summaries were created.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
