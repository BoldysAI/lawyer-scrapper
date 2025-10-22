"""
Configuration constants for the lawyer scraper
"""

# API Configuration
API_BASE_URL = "https://apiresteannuairemiddleware.avocatparis.org"
SEARCH_ENDPOINT = "/api/GetCombinedAvocatStructureFluxDatas"
TOKEN_ENDPOINT = "/api/GetAllCriteriaList"
ANNUAIRE_URL = "https://www.avocatparis.org/annuaire"

# Scraping Parameters
DELAY_MIN = 0.5  # Minimum delay between requests (seconds)
DELAY_MAX = 2.0  # Maximum delay between requests (seconds)
MAX_RETRIES = 3  # Maximum retry attempts per lawyer
BACKOFF_FACTOR = 2  # Exponential backoff multiplier
TOKEN_REFRESH_MARGIN = 300  # Refresh token 5 min before expiry (seconds)

# File Paths
INPUT_CSV = "avocats.csv"
OUTPUT_CSV = "avocats_enriched.csv"
CHECKPOINT_FILE = "checkpoint.json"
LOG_FILE = "scraper.log"

# CSV Configuration
CSV_DELIMITER = ";"
CSV_ENCODING = "ISO-8859-1"  # Or "Windows-1252"

# Progress Configuration
LOG_INTERVAL = 10  # Log progress every N lawyers
CHECKPOINT_INTERVAL = 100  # Save checkpoint every N lawyers

# Playwright Configuration
PLAYWRIGHT_HEADLESS = False  # Set to True for production
PLAYWRIGHT_BROWSER = "chromium"  # Options: chromium, firefox, webkit
PLAYWRIGHT_TIMEOUT = 30000  # Timeout in milliseconds (30 seconds)

