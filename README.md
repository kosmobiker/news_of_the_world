# News of the World

**News of the World** is a Python-based project designed to parse RSS feeds and summarize news articles. It includes scheduled tasks for periodic RSS parsing and daily summarization.

## Features
- Parse RSS feeds every 4 hours.
- Summarize news articles once per day.
- Easily configurable with environment variables.

## Requirements
- Python 3.13
- `uv` for dependency management

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/kosmobiker/news_of_the_world.git
   cd news_of_the_world
   ```
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Set up environment variables in a `.env` file:
   ```env
   DATABASE_URL=<your_database_url>
   XAI_API_KEY=<your_api_key>
   PYTHONPATH=.
   ```

## Usage
- Run the RSS parser:
  ```bash
  uv run parser/rss_parser.py
  ```
- Run the summarization script:
  ```bash
  uv run summarizers/cli.py
  ```

## GitHub Actions
This repository includes a GitHub Actions workflow to automate tasks:
- **RSS Parsing**: Runs every 4 hours.
- **Summarization**: Runs daily at midnight.
