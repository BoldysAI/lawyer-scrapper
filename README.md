# Lawyer Scraper

A Python-based web scraper that extracts contact information (phone numbers and emails) for lawyers listed in the Paris Bar Association directory.

## 📋 Overview

This scraper processes a CSV file containing lawyer information and enriches it with contact details by querying the Paris Bar Association API (`https://www.avocatparis.org/annuaire`). It handles 34,000+ lawyer records with robust error handling, rate limiting, and resume capability.

## ✨ Features

- **Automated Token Management** - Automatically extracts and refreshes JWT tokens using Playwright
- **Progressive Output** - Writes results immediately to prevent data loss
- **Resume Capability** - Checkpoint system allows resuming from interruptions
- **Rate Limiting** - Configurable delays between requests to avoid overwhelming the API
- **Error Handling** - Retry logic with exponential backoff for network errors
- **Test Mode** - Process a small batch of lawyers for testing before full scrape
- **Detailed Logging** - Progress tracking and error logging to file and console

## 🚀 Quick Start

### Prerequisites

- Python 3.8+ (tested on Python 3.14)
- macOS, Linux, or Windows
- Internet connection

### Installation

1. **Clone the repository** (or download the files)
   ```bash
   cd lawyer-scrapper
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment**
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Install Playwright browser**
   ```bash
   playwright install chromium
   ```

### Running the Scraper

#### Test Mode (5 lawyers)
```bash
python scraper.py --test
```

#### Custom Test Batch (e.g., 100 lawyers)
```bash
python scraper.py --limit=100
```

#### Full Scrape (all 34,111 lawyers)
```bash
python scraper.py
```

The scraper will:
1. Open a browser to extract the authentication token
2. Start processing lawyers one by one
3. Save progress every 100 lawyers
4. Write results to `data/avocats_enriched.csv`

## 📁 Project Structure

```
lawyer-scrapper/
├── data/                          # Data directory
│   ├── avocats.csv               # Input: Lawyer list (34,111 rows)
│   ├── avocats_enriched.csv      # Output: Enriched with phone/email
│   ├── checkpoint.json           # Progress checkpoint for resuming
│   └── scraper.log               # Detailed execution logs
├── venv/                          # Python virtual environment
├── scraper.py                     # Main scraper script
├── token_manager.py               # JWT token extraction module
├── config.py                      # Configuration settings
├── requirements.txt               # Python dependencies
├── README.md                      # This file
└── .gitignore                     # Git ignore rules
```

## ⚙️ Configuration

Edit `config.py` to customize the scraper behavior:

### API Settings
```python
API_BASE_URL = "https://apiresteannuairemiddleware.avocatparis.org"
SEARCH_ENDPOINT = "/api/GetCombinedAvocatStructureFluxDatas"
ANNUAIRE_URL = "https://www.avocatparis.org/annuaire"
```

### Scraping Parameters
```python
DELAY_MIN = 0.5      # Minimum delay between requests (seconds)
DELAY_MAX = 2.0      # Maximum delay between requests (seconds)
MAX_RETRIES = 3      # Maximum retry attempts per lawyer
BACKOFF_FACTOR = 2   # Exponential backoff multiplier
```

### File Paths
```python
INPUT_CSV = "data/avocats.csv"                # Input file
OUTPUT_CSV = "data/avocats_enriched.csv"      # Output file
CHECKPOINT_FILE = "data/checkpoint.json"      # Checkpoint file
LOG_FILE = "data/scraper.log"                 # Log file
```

### CSV Configuration
```python
CSV_DELIMITER = ";"           # CSV field delimiter
CSV_ENCODING = "ISO-8859-1"   # Character encoding
```

### Progress Tracking
```python
LOG_INTERVAL = 10          # Log progress every N lawyers
CHECKPOINT_INTERVAL = 100  # Save checkpoint every N lawyers
```

### Browser Settings
```python
PLAYWRIGHT_HEADLESS = False    # Set to True for headless mode (no visible browser)
PLAYWRIGHT_TIMEOUT = 30000     # Page load timeout in milliseconds
```

## 📊 Input/Output Format

### Input CSV (`data/avocats.csv`)

23 columns with lawyer information:
```
ID_AVO;NOM;PARTICULE;PRENOM1;PRENOM2;PRENOM3;ADR1;ADR2;ADR3;CP;VILLE;PAYS;
DATE_SERMENT;EXE_ETRANGER;SPECIALITE;ACTIVITE_DOMINANTE;MANDAT;LANGUE;
NATIONALITE;TOQUE;SIREN;BARREAU_ORIGINE;CATEGORIE_PROF
```

### Output CSV (`data/avocats_enriched.csv`)

All 23 original columns + 6 new columns:

| Column | Description | Example |
|--------|-------------|---------|
| **TELEPHONE** | Phone number(s) from API | `01 88 80 36 33` or `01 XX; 06 XX` |
| **EMAIL** | Email address(es) from API | `lisejdf@gmail.com` |
| **SCRAPE_STATUS** | Result status | `FOUND`, `NOT_FOUND`, `MULTIPLE_MATCHES`, `ERROR` |
| **SCRAPE_DATE** | Timestamp of scraping | `2025-10-22 19:17:05` |
| **API_IDENTIFIANT** | Unique identifier from API | `1UO3OzykTjdOy4+4e1Tc0g==` |
| **SCRAPE_NOTES** | Additional details | `Exact match found` |

## 🔄 Resume Functionality

If the scraper is interrupted, it saves progress every 100 lawyers. On restart:

```bash
python scraper.py
```

You'll be prompted:
```
🔄 Resume from row 150? (Y/n):
```

- Press `Y` or Enter to resume from the checkpoint
- Press `n` to start fresh (previous progress will be lost)

## 📈 Performance

### Estimated Time
- **Small test (5 lawyers)**: ~15 seconds
- **Medium test (100 lawyers)**: ~3-5 minutes
- **Full scrape (34,111 lawyers)**: ~10-19 hours

### Rate Limiting
- Random delay of 0.5-2 seconds between requests
- Exponential backoff on rate limit errors (HTTP 429)
- Automatic token refresh every ~70 minutes

## 🔧 Troubleshooting

### SSL Certificate Error

If you encounter SSL certificate verification errors:
```
SSLError(SSLCertVerificationError...
```

The scraper is configured to use `verify=False` for macOS compatibility. This is safe for this specific use case.

### Browser Not Opening

If Playwright fails to open the browser:
```bash
# Reinstall Chromium
playwright install chromium
```

### Missing Input File

Ensure `data/avocats.csv` exists:
```bash
ls -l data/avocats.csv
```

### Token Extraction Failed

If token extraction fails:
1. Check your internet connection
2. Verify the annuaire website is accessible: https://www.avocatparis.org/annuaire
3. Try running in non-headless mode (set `PLAYWRIGHT_HEADLESS = False` in `config.py`)

### Rate Limiting (HTTP 429)

The scraper automatically handles rate limiting with exponential backoff. If it occurs frequently:
1. Increase `DELAY_MIN` and `DELAY_MAX` in `config.py`
2. The scraper will automatically slow down when rate limited

## 📝 Logging

Logs are written to both console and `data/scraper.log`:

```
2025-10-22 19:17:05 - INFO - 🔍 [1] Searching: Lise JEANNE DIT FOUQUE
2025-10-22 19:17:05 - INFO -    ✓ Found - Phone: 01 88 80 36 33, Email: lisejdf@gmail.com
```

Progress summary every 10 lawyers:
```
======================================================================
📊 PROGRESS: 100 processed
   ✓ Found: 95 (95.0%)
   ✗ Not found: 3 (3.0%)
   ⚠ Multiple matches: 2 (2.0%)
   ❌ Errors: 0 (0.0%)
======================================================================
```

## 🛡️ Error Handling

The scraper handles various error scenarios:

| Error Type | Handling Strategy |
|------------|------------------|
| **Network timeout** | Retry up to 3 times with exponential backoff |
| **Rate limiting (429)** | Automatic backoff and retry |
| **Token expiration (401)** | Automatic token refresh and retry |
| **Server error (500)** | Log error and continue with next lawyer |
| **Invalid response** | Mark as ERROR and continue |
| **Script interruption** | Save checkpoint, resume on restart |

## 📋 Status Values

| Status | Meaning |
|--------|---------|
| **FOUND** | Successfully found contact information |
| **NOT_FOUND** | No results returned from API |
| **MULTIPLE_MATCHES** | Multiple lawyers with same name (took first match) |
| **ERROR** | HTTP error or exception occurred |

## 🎯 Usage Examples

### Run test with first 5 lawyers
```bash
python scraper.py --test
```

### Run full scrape (unattended)
```bash
nohup python scraper.py > output.log 2>&1 &
```

### Monitor progress in real-time
```bash
tail -f data/scraper.log
```

### Check current progress
```bash
# Count lines in output (subtract 1 for header)
wc -l data/avocats_enriched.csv
```

## 🔐 Data Privacy

- The scraper only accesses publicly available information from the Paris Bar Association directory
- No authentication or login is required beyond the automatic JWT token extraction
- All data is stored locally in the `data/` directory

## 📚 Dependencies

- **playwright** (>=1.48.0) - Browser automation for token extraction
- **requests** (>=2.31.0) - HTTP client for API calls
- **pandas** (>=2.2.0) - CSV processing
- **PyJWT** (>=2.8.0) - JWT token decoding
- **colorlog** (>=6.8.2) - Enhanced logging (optional)

## 🤝 Contributing

This is a private scraping tool. If you need to make changes:

1. Test changes with `--test` mode first
2. Update configuration in `config.py` rather than hardcoding values
3. Check logs in `data/scraper.log` for debugging

## ⚠️ Disclaimer

This scraper is designed for educational and research purposes. Please:
- Respect the Paris Bar Association's terms of service
- Use reasonable rate limiting (configured by default)
- Do not use scraped data for commercial purposes without permission

## 📞 Support

For issues or questions:
1. Check `data/scraper.log` for detailed error messages
2. Review the **Troubleshooting** section above
3. Verify configuration in `config.py`

## 📊 Expected Results

Based on test runs:
- **Success rate**: ~90-95% of lawyers found
- **Not found**: ~3-5% (may not be in directory or name mismatch)
- **Errors**: <1% (network issues, API errors)
- **Multiple matches**: ~1-2% (common names)

## 🚦 Status Tracking

The scraper provides real-time status updates:

```
🔍 [1] Searching: Lise JEANNE DIT FOUQUE
   ✓ Found - Phone: 01 88 80 36 33, Email: lisejdf@gmail.com

🔍 [2] Searching: Paul GEFFROY
   ✓ Found - Phone: 01 86 64 06 70, Email: paul.geffroy@coudercdinh.fr
```

## 📁 Output Management

- Output is written progressively (each row saved immediately)
- Can monitor output file while scraper is running
- Safe to interrupt - checkpoint allows resuming

---

**Last Updated**: October 22, 2025  
**Version**: 1.0

