"""
Token Manager - Handles JWT token extraction and refresh
"""

import jwt
import time
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
from config import (
    ANNUAIRE_URL,
    API_BASE_URL,
    PLAYWRIGHT_HEADLESS,
    PLAYWRIGHT_TIMEOUT
)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TokenManager:
    """Manages JWT token extraction and validation"""
    
    def __init__(self):
        self.token = None
        self.expires_at = None
    
    def get_fresh_token(self):
        """
        Extract a fresh Bearer token by loading the annuaire page
        and intercepting network requests.
        
        Returns:
            tuple: (token_string, expiration_timestamp) or (None, None) on failure
        """
        logger.info("Starting token extraction using Playwright...")
        
        token = None
        expires_at = None
        
        try:
            with sync_playwright() as p:
                # Launch browser
                logger.info(f"Launching browser (headless={PLAYWRIGHT_HEADLESS})...")
                browser = p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
                context = browser.new_context()
                page = context.new_page()
                
                # Set up request interception
                def handle_request(request):
                    nonlocal token, expires_at
                    
                    # Look for requests to the API base URL
                    if API_BASE_URL in request.url:
                        headers = request.headers
                        auth_header = headers.get('authorization', '')
                        
                        if auth_header.startswith('Bearer '):
                            token_str = auth_header.replace('Bearer ', '')
                            logger.info(f"Token intercepted from: {request.url}")
                            
                            # Try to decode the token to get expiration
                            try:
                                decoded = jwt.decode(
                                    token_str,
                                    options={"verify_signature": False}
                                )
                                exp = decoded.get('exp')
                                if exp:
                                    token = token_str
                                    expires_at = exp
                                    logger.info(f"Token expiration: {datetime.fromtimestamp(exp)}")
                            except Exception as e:
                                logger.warning(f"Could not decode token: {e}")
                
                # Attach the request handler
                page.on('request', handle_request)
                
                # Navigate to the annuaire page
                logger.info(f"Loading page: {ANNUAIRE_URL}")
                page.goto(ANNUAIRE_URL, timeout=PLAYWRIGHT_TIMEOUT)
                
                # Wait a bit for API calls to complete
                logger.info("Waiting for API calls...")
                page.wait_for_timeout(5000)  # Wait 5 seconds for API calls
                
                # Close browser
                browser.close()
                
                if token and expires_at:
                    logger.info("✓ Token extracted successfully!")
                    self.token = token
                    self.expires_at = expires_at
                    return token, expires_at
                else:
                    logger.error("✗ Failed to extract token from network requests")
                    return None, None
                    
        except PlaywrightTimeoutError:
            logger.error(f"✗ Timeout while loading page (timeout: {PLAYWRIGHT_TIMEOUT}ms)")
            return None, None
        except Exception as e:
            logger.error(f"✗ Error during token extraction: {e}")
            return None, None
    
    def is_token_valid(self, margin_seconds=300):
        """
        Check if the current token is still valid.
        
        Args:
            margin_seconds: Refresh token this many seconds before expiry
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        if not self.token or not self.expires_at:
            return False
        
        current_time = time.time()
        time_until_expiry = self.expires_at - current_time
        
        if time_until_expiry <= margin_seconds:
            logger.info(f"Token expires in {time_until_expiry:.0f}s - needs refresh")
            return False
        
        logger.info(f"Token valid for {time_until_expiry:.0f}s")
        return True
    
    def refresh_token_if_needed(self, margin_seconds=300):
        """
        Refresh the token if it's expired or about to expire.
        
        Args:
            margin_seconds: Refresh token this many seconds before expiry
            
        Returns:
            bool: True if token is valid (or successfully refreshed), False otherwise
        """
        if self.is_token_valid(margin_seconds):
            return True
        
        logger.info("Token needs refresh - fetching new token...")
        token, expires_at = self.get_fresh_token()
        
        if token:
            logger.info("✓ Token refreshed successfully")
            return True
        else:
            logger.error("✗ Failed to refresh token")
            return False
    
    def get_token(self):
        """
        Get the current token (or None if not available).
        
        Returns:
            str: Current Bearer token or None
        """
        return self.token


# Convenience function for quick testing
def test_token_extraction():
    """Test the token extraction process"""
    print("\n" + "="*60)
    print("TESTING TOKEN EXTRACTION")
    print("="*60 + "\n")
    
    manager = TokenManager()
    token, expires_at = manager.get_fresh_token()
    
    if token:
        print(f"\n✓ SUCCESS!")
        print(f"Token (first 50 chars): {token[:50]}...")
        print(f"Full token length: {len(token)} characters")
        print(f"Expires at: {datetime.fromtimestamp(expires_at)}")
        print(f"Time until expiry: {(expires_at - time.time()) / 60:.1f} minutes")
        return True
    else:
        print(f"\n✗ FAILED to extract token")
        return False


if __name__ == "__main__":
    # Run test when executed directly
    test_token_extraction()

