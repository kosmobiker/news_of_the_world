"""Command-line interface for running news summarization."""
from datetime import datetime
import argparse
from db.database import SessionLocal
from summarizers.daily_processor import process_daily_summary

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
            print(f"Created summary for {summary.date} with {summary.articles_count} articles")
        else:
            print("No articles found to summarize for the specified date")
    finally:
        db.close()

if __name__ == "__main__":
    main()
