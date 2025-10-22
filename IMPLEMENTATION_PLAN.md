# Lawyer Scraper - Implementation Plan

## Project Overview

Scrape contact information (phone numbers and emails) for 34,111 lawyers listed in `avocats.csv` from the Paris Bar Association directory (https://www.avocatparis.org/annuaire).

---

## Step 1: Website Audit ✅

### Architecture
- **Type:** Single Page Application (SPA) with JavaScript rendering
- **API:** REST JSON API at `apiresteannuairemiddleware.avocatparis.org`
- **Authentication:** Bearer JWT token (short-lived, ~1.5 hours)
- **Access:** Public (no login required)
- **CORS:** Enabled (`access-control-allow-origin: *`)

### API Endpoints Discovered

#### 1. Search Endpoint
```
GET https://apiresteannuairemiddleware.avocatparis.org/api/GetCombinedAvocatStructureFluxDatas
Parameters: 
  - page: 0
  - result: 30
  - nom: <URL_ENCODED_FULL_NAME>
Headers:
  - Authorization: Bearer <JWT_TOKEN>
```

**Response Structure:**
```json
{
  "metadata": {
    "totalResult": 1,
    "structure": 0,
    "lawyer": 1,
    "nonExercant": 0,
    "timestamp": 1761150657
  },
  "list": {
    "exact": [
      {
        "identifiant": "1UO3OzykTjdOy4+4e1Tc0g==",
        "nom": "Lise JEANNE DIT FOUQUE",
        "nom_fantaisie_enseigne": "",
        "numero_toque": "D1496",
        "type_structure": "",
        "telephone": ["01 88 80 36 33"],
        "telecopie": "",
        "emails": ["lisejdf@gmail.com"],
        "site_internet": [],
        "adresse_paris": "54 B RUE DE CLICHY 75009 PARIS",
        "adresse_Etranger": "",
        "categorie_professionnelle": "Inscrit",
        "inscr_comm_electro": false,
        "libelle_evenement": "",
        "imgprofil": "https://espacepro.avocatparis.org/imgprofil.php?p=...",
        "tagEtranger": {...}
      }
    ],
    "contient": [],
    "libelle_evenement": []
  }
}
```

**Key Findings:**
- ✅ Phone and email are included directly in search results
- ✅ No need to call detail endpoint for most cases
- ✅ `exact` array contains exact name matches
- ✅ `contient` array contains partial matches

#### 2. Token Acquisition
```
GET https://apiresteannuairemiddleware.avocatparis.org/api/GetAllCriteriaList
```
- Called automatically when `/annuaire` page loads
- Returns Bearer token in response headers
- Token is valid for ~1.5 hours

#### 3. Detail Endpoint (optional - if needed)
```
GET https://apiresteannuairemiddleware.avocatparis.org/api/GetAvocatByCnbf
Parameters:
  - cnbf: <IDENTIFIANT>
```

---

## Step 2: Complexity Assessment ✅

### Complexity Level: **LOW-MEDIUM** ⭐⭐⭐

### Advantages
- ✅ Clean JSON API (no HTML parsing)
- ✅ Contact info in search results (no secondary calls)
- ✅ Simple GET requests
- ✅ No CAPTCHA observed
- ✅ CORS enabled

### Challenges
- 🟡 **Token Management:** JWT expires every ~1.5 hours
- 🟡 **Rate Limiting:** 34K+ requests must be throttled
- 🟡 **Error Handling:** Network issues, missing data, etc.
- 🟡 **Long Runtime:** ~10-19 hours total

### Technology Stack
```
Python 3.8+
├── playwright          # Token extraction (browser automation)
├── requests           # HTTP client for API calls
├── pandas             # CSV reading/writing
├── time / asyncio     # Rate limiting
├── logging            # Progress tracking
├── json               # Response parsing
└── urllib.parse       # URL encoding
```

---

## Step 3: Implementation Plan ✅

### Architecture: **Hybrid Approach**

1. **Token Management** (Playwright) - Extract token from browser
2. **Data Scraping** (Direct API calls) - Fast HTTP requests
3. **Progressive Output** - Write results immediately
4. **Auto-recovery** - Checkpoint system for resumability

---

### Phase 1: Token Management 🔑

**Objective:** Extract and maintain valid Bearer token

**Implementation:**
1. Use Playwright to load `/annuaire` page
2. Intercept network requests
3. Extract Bearer token from `GetAllCriteriaList` call
4. Store token with expiration timestamp
5. Auto-refresh when token expires (~70 minutes)

**Module:** `token_manager.py`

**Functions:**
- `get_fresh_token()` → Extract token using Playwright
- `is_token_valid(token, expiry)` → Check if token is still valid
- `refresh_token_if_needed()` → Auto-refresh logic

---

### Phase 2: CSV Processing 📊

**Objective:** Read input CSV and prepare lawyer data

**Input File:** `avocats.csv` (34,111 rows)

**Key Fields:**
- `ID_AVO` - Unique identifier
- `NOM` - Last name
- `PRENOM1` - First name

**Processing:**
1. Read CSV with proper encoding (ISO-8859-1 or Windows-1252)
2. Extract `NOM` and `PRENOM1`
3. Format search query: `"{PRENOM1} {NOM}"`
4. URL-encode for API calls
5. Skip already-processed rows (from checkpoint)

---

### Phase 3: API Scraping 🚀

**Objective:** Search and extract contact information

**For Each Lawyer:**
1. Format search query: `"{PRENOM1} {NOM}"`
2. Make GET request to search endpoint
3. Parse JSON response
4. Extract from `list.exact[]`:
   - `telephone[]` - Array of phone numbers
   - `emails[]` - Array of emails
   - `identifiant` - Unique API ID
5. Handle multiple results (prioritize first exact match)
6. Handle no results (mark as NOT_FOUND)
7. Append to output CSV immediately

**Module:** `scraper.py`

---

### Phase 4: Error Handling & Rate Limiting ⚠️

**Rate Limiting:**
- Delay: 0.5-2 seconds between requests
- Randomize delays to appear more human
- Backoff on rate limit errors (429)

**Error Handling:**
```python
Try:
  1. Make API request
  2. Parse response
  3. Extract data
Except:
  - HTTP 401 → Refresh token, retry
  - HTTP 429 → Exponential backoff, retry
  - HTTP 500 → Log error, mark as ERROR, continue
  - Network error → Retry 3x, then mark as ERROR
  - JSON parse error → Log, mark as ERROR
```

**Retry Strategy:**
- Max retries: 3 per lawyer
- Backoff: 2^retry_count seconds
- After 3 failures: Mark as ERROR, continue

**Progress Tracking:**
- Log every 10 lawyers processed
- Save checkpoint every 100 lawyers
- Display: "Processed 150/34111 (0.44%) - 145 found, 3 not found, 2 errors"

---

### Phase 5: Output Formatting 💾

**Output File:** `avocats_enriched.csv`

**Structure:** All original fields + 6 new fields

#### Original Fields (23 columns - preserved):
```
ID_AVO;NOM;PARTICULE;PRENOM1;PRENOM2;PRENOM3;ADR1;ADR2;ADR3;CP;VILLE;PAYS;
DATE_SERMENT;EXE_ETRANGER;SPECIALITE;ACTIVITE_DOMINANTE;MANDAT;LANGUE;
NATIONALITE;TOQUE;SIREN;BARREAU_ORIGINE;CATEGORIE_PROF
```

#### New Fields (6 columns - added):
```
TELEPHONE;EMAIL;SCRAPE_STATUS;SCRAPE_DATE;API_IDENTIFIANT;SCRAPE_NOTES
```

#### Field Descriptions:

| Field | Description | Example Values |
|-------|-------------|----------------|
| **TELEPHONE** | Phone number(s) from API | `01 88 80 36 33` or `01 XX; 06 XX` (multiple) |
| **EMAIL** | Email address(es) from API | `lisejdf@gmail.com` or `email1@test.fr; email2@test.fr` |
| **SCRAPE_STATUS** | Status of scraping attempt | `FOUND`, `NOT_FOUND`, `MULTIPLE_MATCHES`, `ERROR`, `PENDING` |
| **SCRAPE_DATE** | Timestamp of scraping | `2025-10-22 16:45:30` |
| **API_IDENTIFIANT** | Unique ID from API | `1UO3OzykTjdOy4+4e1Tc0g==` |
| **SCRAPE_NOTES** | Additional details/errors | `Found 2 exact matches - took first` |

#### Status Values:
- `FOUND` - Successfully found contact info
- `NOT_FOUND` - No results returned from API
- `MULTIPLE_MATCHES` - Multiple exact matches (took first)
- `ERROR` - HTTP error or exception occurred
- `PENDING` - Not yet processed

#### Example Output Row:

**Input:**
```
A99435799;JEANNE DIT FOUQUE;;Lise;Alexandra;Manon;54 B RUE DE CLICHY;;;75009;PARIS;FRANCE;04/11/24;;;Droit des affaires, Droit fiscal;;Anglais, Français;Française;D1496;;Barreau des Hauts-de-Seine;Avocat à la cour
```

**Output:**
```
A99435799;JEANNE DIT FOUQUE;;Lise;Alexandra;Manon;54 B RUE DE CLICHY;;;75009;PARIS;FRANCE;04/11/24;;;Droit des affaires, Droit fiscal;;Anglais, Français;Française;D1496;;Barreau des Hauts-de-Seine;Avocat à la cour;01 88 80 36 33;lisejdf@gmail.com;FOUND;2025-10-22 16:45:30;1UO3OzykTjdOy4+4e1Tc0g==;Exact match found
```

---

### Phase 6: Checkpoint System 🔄

**Purpose:** Allow script to resume after interruption

**Checkpoint File:** `checkpoint.json`

**Structure:**
```json
{
  "last_processed_index": 150,
  "last_processed_id": "A99435799",
  "total_processed": 150,
  "total_rows": 34111,
  "successful": 145,
  "not_found": 3,
  "errors": 2,
  "multiple_matches": 0,
  "last_token_refresh": "2025-10-22T16:45:30",
  "current_token": "eyJhbGc...",
  "token_expires_at": 1761157056,
  "started_at": "2025-10-22T10:00:00",
  "last_updated": "2025-10-22T16:45:30"
}
```

**Resume Logic:**
1. On startup, check if `checkpoint.json` exists
2. If exists, ask user: "Resume from row 150? (Y/n)"
3. If yes, skip to row 151 and continue
4. Update checkpoint every 100 rows

---

## File Structure

```
/lawyer-scrapper/
├── avocats.csv                 # Input data (34,111 lawyers)
├── scraper.py                  # Main scraper script
├── token_manager.py            # Token extraction & refresh
├── config.py                   # Configuration constants
├── avocats_enriched.csv        # Output (progressively written)
├── checkpoint.json             # Resume state
├── scraper.log                 # Detailed logs
├── requirements.txt            # Python dependencies
├── IMPLEMENTATION_PLAN.md      # This document
└── README.md                   # Usage instructions
```

---

## Configuration Constants

**File:** `config.py`

```python
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
TOKEN_REFRESH_MARGIN = 300  # Refresh token 5 min before expiry

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
```

---

## Risk Mitigation

| Risk | Impact | Mitigation Strategy |
|------|--------|-------------------|
| Token expiration mid-scrape | Script fails | Auto-refresh token every 70 min |
| Rate limiting (HTTP 429) | Blocked requests | Exponential backoff + random delays |
| Network errors | Lost data | Retry logic (3x) + checkpoint system |
| Script interruption | Lost progress | Save checkpoint every 100 records |
| Multiple name matches | Wrong data | Take first exact match, log as MULTIPLE_MATCHES |
| No results found | Missing data | Mark as NOT_FOUND, continue processing |
| Encoding issues | Corrupted output | Match input encoding (ISO-8859-1) |
| Memory overflow | Script crash | Stream processing (no full load) |

---

## Performance Estimates

**Total Lawyers:** 34,111

**Processing Speed:**
- Optimistic: 1 req/sec = ~9.5 hours
- Realistic: 0.5-1 req/sec = ~10-19 hours
- Conservative: 0.3 req/sec = ~32 hours

**Includes:**
- API request time (~200-500ms)
- Rate limiting delays (0.5-2 sec)
- Token refresh overhead (~30 sec every 70 min)
- Error retries and backoff

**Checkpoint Frequency:** Every 100 lawyers = ~341 checkpoints

---

## Testing Strategy

### Phase 1: Unit Testing
1. Test token extraction (1 run)
2. Test single lawyer search (5 lawyers)
3. Test error handling (force errors)

### Phase 2: Small Batch
1. Process first 100 lawyers
2. Verify output format
3. Check checkpoint system
4. Monitor for rate limiting

### Phase 3: Medium Batch
1. Process 1,000 lawyers
2. Test token refresh
3. Test script interruption/resume
4. Analyze error patterns

### Phase 4: Full Scrape
1. Process all 34,111 lawyers
2. Monitor continuously
3. Handle any issues that arise

---

## Implementation Decisions

### 1. Multiple Matches Strategy
**Decision:** Take first "exact" match
**Rationale:** Most likely to be the correct lawyer; alternative would require manual review of 34K entries

### 2. Phone/Email Separator
**Decision:** Semicolon (`;`)
**Rationale:** Matches CSV delimiter, easy to split later if needed

### 3. Output Filename
**Decision:** `avocats_enriched.csv`
**Rationale:** Clear, descriptive, doesn't overwrite original

### 4. CSV Encoding
**Decision:** Match input encoding (ISO-8859-1 or Windows-1252)
**Rationale:** Prevents character corruption, maintains consistency

### 5. Writing Strategy
**Decision:** Progressive/streaming (write each row immediately)
**Rationale:** Prevents data loss on interruption, allows real-time monitoring

---

## Success Criteria

✅ **Functional:**
- Script completes without crashing
- All 34,111 lawyers processed
- Output CSV has correct format
- Resume capability works

✅ **Data Quality:**
- >90% success rate (FOUND status)
- <5% errors
- Contact info matches manual spot checks

✅ **Performance:**
- Completes within 24 hours
- No rate limiting issues
- Token refresh works automatically

✅ **Robustness:**
- Handles interruptions gracefully
- Logs all errors with details
- Can resume from any checkpoint

---

## Next Steps

1. ✅ **Plan Approved** - Document created
2. ⏳ **Implementation** - Create Python scripts
3. ⏳ **Unit Testing** - Test individual components
4. ⏳ **Small Batch Test** - Process 100 lawyers
5. ⏳ **Full Scrape** - Process all 34,111 lawyers
6. ⏳ **Validation** - Verify output quality

---

## Notes

- Script designed for single-threaded execution (easier to manage rate limits)
- No parallel requests to avoid overwhelming the API
- All decisions prioritize data integrity over speed
- User approval required before proceeding with implementation

---

**Document Version:** 1.0  
**Last Updated:** 2025-10-22  

