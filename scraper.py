"""
Lawyer Scraper - Main Script
Scrapes contact information (phone, email) for lawyers from Paris Bar Association
"""

import csv
import json
import logging
import os
import random
import sys
import time
import requests
import urllib3
from datetime import datetime
from urllib.parse import urlencode
from token_manager import TokenManager

# Disable SSL warnings (since we're using verify=False due to macOS certificate issues)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from config import (
    API_BASE_URL,
    SEARCH_ENDPOINT,
    INPUT_CSV,
    OUTPUT_CSV,
    CHECKPOINT_FILE,
    LOG_FILE,
    CSV_DELIMITER,
    CSV_ENCODING,
    DELAY_MIN,
    DELAY_MAX,
    MAX_RETRIES,
    BACKOFF_FACTOR,
    LOG_INTERVAL,
    CHECKPOINT_INTERVAL,
    TOKEN_REFRESH_MARGIN
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class LawyerScraper:
    """Main scraper class for extracting lawyer contact information"""
    
    def __init__(self, test_mode=False, test_limit=5):
        """
        Initialize the scraper
        
        Args:
            test_mode: If True, only process first test_limit lawyers
            test_limit: Number of lawyers to process in test mode
        """
        self.token_manager = TokenManager()
        self.test_mode = test_mode
        self.test_limit = test_limit
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'found': 0,
            'not_found': 0,
            'multiple_matches': 0,
            'errors': 0,
            'started_at': datetime.now().isoformat()
        }
        
        # Output file handle
        self.output_file = None
        self.output_writer = None
        
        logger.info("="*70)
        logger.info("LAWYER SCRAPER INITIALIZED")
        logger.info("="*70)
        if test_mode:
            logger.info(f"⚠️  TEST MODE: Will process only {test_limit} lawyers")
    
    def load_checkpoint(self):
        """
        Load checkpoint if it exists
        
        Returns:
            dict: Checkpoint data or None
        """
        if os.path.exists(CHECKPOINT_FILE):
            try:
                with open(CHECKPOINT_FILE, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                logger.info(f"📂 Checkpoint found: {checkpoint['total_processed']} lawyers already processed")
                return checkpoint
            except Exception as e:
                logger.error(f"❌ Error loading checkpoint: {e}")
                return None
        return None
    
    def save_checkpoint(self, last_index, last_id):
        """
        Save current progress to checkpoint file
        
        Args:
            last_index: Last processed row index
            last_id: Last processed lawyer ID
        """
        checkpoint = {
            'last_processed_index': last_index,
            'last_processed_id': last_id,
            'total_processed': self.stats['total_processed'],
            'successful': self.stats['found'],
            'not_found': self.stats['not_found'],
            'multiple_matches': self.stats['multiple_matches'],
            'errors': self.stats['errors'],
            'last_updated': datetime.now().isoformat(),
            'started_at': self.stats['started_at']
        }
        
        try:
            with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
                json.dump(checkpoint, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error saving checkpoint: {e}")
    
    def search_lawyer(self, nom, prenom):
        """
        Search for a lawyer using the API
        
        Args:
            nom: Last name
            prenom: First name
            
        Returns:
            dict: API response data or None on error
        """
        # Format search query
        full_name = f"{prenom} {nom}".strip()
        
        # Build URL
        params = {
            'page': 0,
            'result': 30,
            'nom': full_name
        }
        url = f"{API_BASE_URL}{SEARCH_ENDPOINT}?{urlencode(params)}"
        
        # Get valid token
        if not self.token_manager.refresh_token_if_needed(TOKEN_REFRESH_MARGIN):
            logger.error("❌ Failed to get valid token")
            return None
        
        # Make request
        headers = {
            'Authorization': f'Bearer {self.token_manager.get_token()}',
            'Accept': '*/*',
            'Origin': 'https://www.avocatparis.org',
            'Referer': 'https://www.avocatparis.org/'
        }
        
        for attempt in range(MAX_RETRIES):
            try:
                response = requests.get(url, headers=headers, timeout=30, verify=False)
                
                # Handle rate limiting
                if response.status_code == 429:
                    wait_time = (BACKOFF_FACTOR ** attempt) * 5
                    logger.warning(f"⚠️  Rate limited (429) - waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue
                
                # Handle token expiration
                if response.status_code == 401:
                    logger.warning("⚠️  Token expired (401) - refreshing")
                    self.token_manager.get_fresh_token()
                    headers['Authorization'] = f'Bearer {self.token_manager.get_token()}'
                    continue
                
                # Success
                if response.status_code == 200:
                    return response.json()
                
                # Other errors
                logger.error(f"❌ HTTP {response.status_code} for {full_name}")
                return None
                
            except requests.exceptions.Timeout:
                logger.warning(f"⚠️  Timeout (attempt {attempt+1}/{MAX_RETRIES})")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(BACKOFF_FACTOR ** attempt)
                continue
                
            except Exception as e:
                logger.error(f"❌ Error searching {full_name}: {e}")
                return None
        
        logger.error(f"❌ Max retries exceeded for {full_name}")
        return None
    
    def extract_contact_info(self, api_response, full_name):
        """
        Extract phone and email from API response
        
        Args:
            api_response: JSON response from API
            full_name: Full name searched for logging
            
        Returns:
            dict: Extracted data with keys: telephone, email, status, identifiant, notes
        """
        result = {
            'telephone': '',
            'email': '',
            'status': 'ERROR',
            'identifiant': '',
            'notes': ''
        }
        
        try:
            # Check if response has expected structure
            if not api_response or 'list' not in api_response:
                result['status'] = 'NOT_FOUND'
                result['notes'] = 'Invalid API response'
                return result
            
            # Get exact matches
            exact_matches = api_response.get('list', {}).get('exact', [])
            
            if not exact_matches or len(exact_matches) == 0:
                result['status'] = 'NOT_FOUND'
                result['notes'] = 'No exact matches found'
                return result
            
            # Handle multiple matches
            if len(exact_matches) > 1:
                result['status'] = 'MULTIPLE_MATCHES'
                result['notes'] = f'Found {len(exact_matches)} exact matches - took first'
                logger.info(f"ℹ️  Multiple matches for {full_name}: {len(exact_matches)}")
            else:
                result['status'] = 'FOUND'
                result['notes'] = 'Exact match found'
            
            # Extract from first match
            match = exact_matches[0]
            
            # Extract phone numbers
            telephones = match.get('telephone', [])
            if telephones:
                result['telephone'] = '; '.join(telephones)
            
            # Extract emails
            emails = match.get('emails', [])
            if emails:
                result['email'] = '; '.join(emails)
            
            # Extract identifiant
            result['identifiant'] = match.get('identifiant', '')
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error extracting contact info: {e}")
            result['status'] = 'ERROR'
            result['notes'] = f'Extraction error: {str(e)}'
            return result
    
    def init_output_file(self, resume_from_index=None):
        """
        Initialize output CSV file
        
        Args:
            resume_from_index: If set, open in append mode (resuming)
        """
        # If resuming and file exists, open in append mode
        if resume_from_index is not None and os.path.exists(OUTPUT_CSV):
            logger.info(f"📝 Resuming - opening {OUTPUT_CSV} in append mode")
            self.output_file = open(OUTPUT_CSV, 'a', encoding=CSV_ENCODING, newline='')
            self.output_writer = csv.writer(self.output_file, delimiter=CSV_DELIMITER)
        else:
            # Create new file with header
            logger.info(f"📝 Creating new output file: {OUTPUT_CSV}")
            self.output_file = open(OUTPUT_CSV, 'w', encoding=CSV_ENCODING, newline='')
            self.output_writer = csv.writer(self.output_file, delimiter=CSV_DELIMITER)
            
            # Write header (all original fields + new fields)
            header = [
                'ID_AVO', 'NOM', 'PARTICULE', 'PRENOM1', 'PRENOM2', 'PRENOM3',
                'ADR1', 'ADR2', 'ADR3', 'CP', 'VILLE', 'PAYS',
                'DATE_SERMENT', 'EXE_ETRANGER', 'SPECIALITE', 'ACTIVITE_DOMINANTE',
                'MANDAT', 'LANGUE', 'NATIONALITE', 'TOQUE', 'SIREN',
                'BARREAU_ORIGINE', 'CATEGORIE_PROF',
                # New fields
                'TELEPHONE', 'EMAIL', 'SCRAPE_STATUS', 'SCRAPE_DATE',
                'API_IDENTIFIANT', 'SCRAPE_NOTES'
            ]
            self.output_writer.writerow(header)
    
    def close_output_file(self):
        """Close output file"""
        if self.output_file:
            self.output_file.close()
            logger.info(f"📁 Output file closed: {OUTPUT_CSV}")
    
    def process_lawyers(self):
        """
        Main processing loop - read CSV and scrape each lawyer
        """
        # Check for checkpoint
        checkpoint = self.load_checkpoint()
        resume_from_index = None
        
        if checkpoint:
            response = input(f"\n🔄 Resume from row {checkpoint['last_processed_index']}? (Y/n): ").strip().lower()
            if response in ['', 'y', 'yes']:
                resume_from_index = checkpoint['last_processed_index']
                self.stats = {
                    'total_processed': checkpoint['total_processed'],
                    'found': checkpoint['successful'],
                    'not_found': checkpoint['not_found'],
                    'multiple_matches': checkpoint.get('multiple_matches', 0),
                    'errors': checkpoint['errors'],
                    'started_at': checkpoint['started_at']
                }
                logger.info(f"✓ Resuming from index {resume_from_index}")
            else:
                logger.info("✓ Starting fresh (checkpoint ignored)")
        
        # Get initial token
        logger.info("🔑 Obtaining initial token...")
        if not self.token_manager.get_fresh_token():
            logger.error("❌ Failed to get initial token - aborting")
            return
        
        # Initialize output file
        self.init_output_file(resume_from_index)
        
        # Read and process input CSV
        try:
            with open(INPUT_CSV, 'r', encoding=CSV_ENCODING) as csvfile:
                reader = csv.DictReader(csvfile, delimiter=CSV_DELIMITER)
                
                logger.info(f"📖 Reading input CSV: {INPUT_CSV}")
                logger.info("🚀 Starting scraping process...\n")
                
                for index, row in enumerate(reader):
                    # Skip already processed rows
                    if resume_from_index is not None and index <= resume_from_index:
                        continue
                    
                    # Test mode limit
                    if self.test_mode and self.stats['total_processed'] >= self.test_limit:
                        logger.info(f"\n⚠️  TEST MODE: Reached limit of {self.test_limit} lawyers")
                        break
                    
                    # Extract data
                    id_avo = row.get('ID_AVO', '')
                    nom = row.get('NOM', '')
                    prenom = row.get('PRENOM1', '')
                    
                    if not nom or not prenom:
                        logger.warning(f"⚠️  Skipping row {index}: missing name data")
                        continue
                    
                    full_name = f"{prenom} {nom}"
                    
                    # Search lawyer
                    logger.info(f"🔍 [{self.stats['total_processed']+1}] Searching: {full_name}")
                    api_response = self.search_lawyer(nom, prenom)
                    
                    # Extract contact info
                    contact_info = self.extract_contact_info(api_response, full_name)
                    
                    # Update statistics
                    self.stats['total_processed'] += 1
                    if contact_info['status'] == 'FOUND':
                        self.stats['found'] += 1
                        logger.info(f"   ✓ Found - Phone: {contact_info['telephone']}, Email: {contact_info['email']}")
                    elif contact_info['status'] == 'NOT_FOUND':
                        self.stats['not_found'] += 1
                        logger.info(f"   ✗ Not found")
                    elif contact_info['status'] == 'MULTIPLE_MATCHES':
                        self.stats['multiple_matches'] += 1
                        logger.info(f"   ⚠ Multiple matches")
                    else:
                        self.stats['errors'] += 1
                        logger.error(f"   ❌ Error: {contact_info['notes']}")
                    
                    # Write to output CSV (preserve all original fields + add new ones)
                    output_row = [
                        row.get('ID_AVO', ''),
                        row.get('NOM', ''),
                        row.get('PARTICULE', ''),
                        row.get('PRENOM1', ''),
                        row.get('PRENOM2', ''),
                        row.get('PRENOM3', ''),
                        row.get('ADR1', ''),
                        row.get('ADR2', ''),
                        row.get('ADR3', ''),
                        row.get('CP', ''),
                        row.get('VILLE', ''),
                        row.get('PAYS', ''),
                        row.get('DATE_SERMENT', ''),
                        row.get('EXE_ETRANGER', ''),
                        row.get('SPECIALITE', ''),
                        row.get('ACTIVITE_DOMINANTE', ''),
                        row.get('MANDAT', ''),
                        row.get('LANGUE', ''),
                        row.get('NATIONALITE', ''),
                        row.get('TOQUE', ''),
                        row.get('SIREN', ''),
                        row.get('BARREAU_ORIGINE', ''),
                        row.get('CATEGORIE_PROF', ''),
                        # New fields
                        contact_info['telephone'],
                        contact_info['email'],
                        contact_info['status'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        contact_info['identifiant'],
                        contact_info['notes']
                    ]
                    
                    self.output_writer.writerow(output_row)
                    self.output_file.flush()  # Write immediately
                    
                    # Progress logging
                    if self.stats['total_processed'] % LOG_INTERVAL == 0:
                        self.log_progress()
                    
                    # Save checkpoint
                    if self.stats['total_processed'] % CHECKPOINT_INTERVAL == 0:
                        self.save_checkpoint(index, id_avo)
                        logger.info(f"💾 Checkpoint saved at row {index}")
                    
                    # Rate limiting
                    delay = random.uniform(DELAY_MIN, DELAY_MAX)
                    time.sleep(delay)
                
        except FileNotFoundError:
            logger.error(f"❌ Input file not found: {INPUT_CSV}")
            return
        except Exception as e:
            logger.error(f"❌ Error processing CSV: {e}")
            return
        finally:
            self.close_output_file()
        
        # Final summary
        self.print_final_summary()
    
    def log_progress(self):
        """Log current progress"""
        total = self.stats['total_processed']
        found = self.stats['found']
        not_found = self.stats['not_found']
        multiple = self.stats['multiple_matches']
        errors = self.stats['errors']
        
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 PROGRESS: {total} processed")
        logger.info(f"   ✓ Found: {found} ({found/total*100:.1f}%)")
        logger.info(f"   ✗ Not found: {not_found} ({not_found/total*100:.1f}%)")
        logger.info(f"   ⚠ Multiple matches: {multiple} ({multiple/total*100:.1f}%)")
        logger.info(f"   ❌ Errors: {errors} ({errors/total*100:.1f}%)")
        logger.info(f"{'='*70}\n")
    
    def print_final_summary(self):
        """Print final summary"""
        logger.info("\n" + "="*70)
        logger.info("🏁 SCRAPING COMPLETE!")
        logger.info("="*70)
        logger.info(f"Total processed: {self.stats['total_processed']}")
        logger.info(f"✓ Found: {self.stats['found']}")
        logger.info(f"✗ Not found: {self.stats['not_found']}")
        logger.info(f"⚠ Multiple matches: {self.stats['multiple_matches']}")
        logger.info(f"❌ Errors: {self.stats['errors']}")
        logger.info(f"Started at: {self.stats['started_at']}")
        logger.info(f"Ended at: {datetime.now().isoformat()}")
        logger.info(f"Output file: {OUTPUT_CSV}")
        logger.info("="*70 + "\n")


def main():
    """Main entry point"""
    # Check if we should run in test mode
    test_mode = '--test' in sys.argv or '-t' in sys.argv
    
    # Check for custom test limit
    test_limit = 5  # Default
    for arg in sys.argv:
        if arg.startswith('--limit='):
            try:
                test_limit = int(arg.split('=')[1])
                test_mode = True
                logger.info(f"Custom test limit: {test_limit}")
            except ValueError:
                logger.error("Invalid limit value. Using default: 5")
    
    # Create scraper
    scraper = LawyerScraper(test_mode=test_mode, test_limit=test_limit)
    
    # Run scraping
    scraper.process_lawyers()


if __name__ == "__main__":
    main()

