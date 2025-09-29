"""Command-line interface for running news summarization."""
from datetime import datetime
import argparse
from db.database import SessionLocal
from summarizers.daily_processor import process_daily_summary
from models.models import DailySummary  # Import the DailySummary model

def main():
    """Process daily summaries for articles."""
    parser = argparse.ArgumentParser(description='Process daily news summaries')
    parser.add_argument('--date', type=str, help='Date to process (YYYY-MM-DD format). Defaults to today.', required=False)
    args = parser.parse_args()

    # Parse date if provided, otherwise use today
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print("Error: Date must be in YYYY-MM-DD format")
            return
    
    print("Starting daily news summarization...")
    
    try:
        db = SessionLocal()
        summary = process_daily_summary(db, target_date)
        if summary:
            # Check if a summary already exists for the same date, category, and country
            existing_summary = (
                db.query(DailySummary)
                .filter(DailySummary.date == summary['date'])
                .filter(DailySummary.category == "news")  # Default category
                .filter(DailySummary.country == "global")  # Default country
                .first()
            )

            if existing_summary:
                print(f"Summary for {summary['date']} already exists in the database.")
            else:
                # Insert the new summary into the database
                new_summary = DailySummary(
                    date=summary['date'],
                    text_summary=summary['summary_data'].get("text_summary", ""),
                    detailed_summary=summary['summary_data'].get("detailed_summary", ""),
                    main_events=summary['summary_data'].get("main_events", {}),
                    key_themes=summary['summary_data'].get("key_themes", {}),
                    impacted_regions=summary['summary_data'].get("impacted_regions", {}),
                    timeline=summary['summary_data'].get("timeline", {}),
                    articles_count=summary['articles_count'],
                    generated_at=datetime.utcnow(),
                    model_name=summary['model_name'],
                    raw_json=summary['summary_data'],
                    category="news",  # Default category
                    country="global"  # Default country
                )

                db.add(new_summary)
                db.commit()
                db.refresh(new_summary)
                print(f"Inserted summary for {summary['date']} into the database.")
        else:
            print("No articles found to summarize for the specified date.")
    finally:
        db.close()

if __name__ == "__main__":
    main()
