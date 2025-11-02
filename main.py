from utils.logging_config import configure_logging
from utils.env_validation import settings

# Configure logging at the entry point
configure_logging()

# Ensure environment variables are validated at startup
print("Environment variables loaded successfully.")


def main():
    print("Hello from news-of-the-world!")


if __name__ == "__main__":
    main()
