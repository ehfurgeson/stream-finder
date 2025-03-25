import time
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
import random
import re
import logging
from datetime import datetime

# Optional imports for fallback methods
try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    print("Google search module not available. Install with: pip install googlesearch-python")

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Selenium not available. Install with: pip install selenium")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
INITIAL_DELAY = 5
MAX_DELAY = 120  # Maximum delay in seconds
OUTPUT_FILE = "filtered_streamers.json"

def read_streamers_from_csv(file_path="top_1000_twitch.csv"):
    """Read streamer names from CSV file."""
    try:
        df = pd.read_csv(file_path)
        return df["Name"].tolist()
    except FileNotFoundError:
        logger.error(f"Error: {file_path} not found.")
        return []
    except Exception as e:
        logger.error(f"Error reading CSV: {e}")
        return []

def random_user_agent():
    """Return a random user agent string from a sample list."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36"
    ]
    return random.choice(user_agents)

def generate_jitter(base_delay, factor=0.5):
    """Add randomized jitter to the delay time."""
    jitter = random.uniform(-factor * base_delay, factor * base_delay)
    return max(1, base_delay + jitter)  # Ensure delay is at least 1 second

def calculate_backoff_delay(attempt, base_delay=INITIAL_DELAY):
    """Calculate exponential backoff delay with jitter."""
    exp_delay = min(base_delay * (2 ** attempt), MAX_DELAY)
    return generate_jitter(exp_delay)

def normalize_streamer_name(name):
    """Normalize streamer name for URL comparison."""
    # Remove spaces, convert to lowercase, remove special characters
    normalized = re.sub(r'[^a-zA-Z0-9]', '', name.lower())
    return normalized

def fetch_page_content(url, timeout=15):
    """Attempt to scrape content from a given URL using a random user agent."""
    try:
        headers = {'User-Agent': random_user_agent()}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.get_text(separator='\n', strip=True)
        return content[:8000]  # Limit content length
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_twitch_page_direct(streamer_name):
    """Try to access a Twitch page directly without using search."""
    # Try different possible username formats
    possible_usernames = []
    
    # Format 1: Direct lowercase without spaces
    possible_usernames.append(streamer_name.lower().replace(" ", ""))
    
    # Format 2: Lowercase with underscores
    possible_usernames.append(streamer_name.lower().replace(" ", "_"))
    
    # Format 3: Direct lowercase (if already no spaces)
    if " " not in streamer_name:
        possible_usernames.append(streamer_name.lower())
    
    # Try up to 3 variants of the name
    name_parts = streamer_name.lower().split()
    if len(name_parts) > 1:
        # Format 4: First part only
        possible_usernames.append(name_parts[0])
        # Format 5: First two parts no space
        if len(name_parts) > 1:
            possible_usernames.append("".join(name_parts[:2]))
    
    # Remove duplicates
    possible_usernames = list(set(possible_usernames))
    
    logger.info(f"Trying direct Twitch URLs for {streamer_name}: {possible_usernames}")
    
    for username in possible_usernames:
        url = f"https://www.twitch.tv/{username}"
        
        # Add delay with jitter
        delay = generate_jitter(2, 0.5)
        logger.info(f"Waiting {delay:.2f} seconds before accessing {url}")
        time.sleep(delay)
        
        try:
            headers = {'User-Agent': random_user_agent()}
            response = requests.get(url, headers=headers, timeout=15)
            
            # If page exists (no 404)
            if response.status_code == 200:
                # Check for indicators of a non-existent channel
                non_existent_phrases = [
                    "Sorry. Unless you've got a time machine, that content is unavailable.",
                    "The page you were looking for doesn't exist yet"
                ]
                
                if not any(phrase in response.text for phrase in non_existent_phrases):
                    content = BeautifulSoup(response.content, 'html.parser').get_text(separator='\n', strip=True)
                    logger.info(f"Found Twitch page for {streamer_name} at {url}")
                    return {
                        "url": url,
                        "content": content[:8000],
                        "source": "Twitch Channel (Direct)",
                        "validated": True,
                        "username": username
                    }
                else:
                    logger.info(f"Channel page exists but appears to be invalid for {url}")
            else:
                logger.info(f"No Twitch page found at {url} (Status: {response.status_code})")
        except Exception as e:
            logger.warning(f"Error accessing {url}: {e}")
    
    logger.info(f"No direct Twitch page found for {streamer_name}")
    return None

def fetch_twitch_page_google(streamer_name, attempt=0):
    """
    Attempt to find Twitch page using Google search with backoff strategy.
    """
    if not GOOGLE_SEARCH_AVAILABLE:
        logger.warning("Google search module not available, skipping this method")
        return None
        
    # Calculate backoff delay
    delay = calculate_backoff_delay(attempt)
    logger.info(f"Google search method - Waiting {delay:.2f} seconds before searching (attempt {attempt+1})")
    time.sleep(delay)
    
    # Include twitch.tv specifically in the search query
    query = f"{streamer_name} twitch.tv channel"
    
    try:
        for url in google_search(query, num_results=3):
            # Only process actual Twitch URLs
            if "twitch.tv/" in url:
                logger.info(f"Found potential Twitch page via Google: {url}")
                
                # Add small delay between processing results
                time.sleep(generate_jitter(2, 0.3))
                
                # Extract username from URL to verify it matches
                try:
                    # Parse URL like "https://www.twitch.tv/ninja"
                    twitch_username = url.split("twitch.tv/")[1].split("/")[0].lower()
                    streamer_normalized = normalize_streamer_name(streamer_name)
                    
                    # Check if any part of the streamer name matches the Twitch username
                    if (streamer_normalized in twitch_username or 
                        twitch_username in streamer_normalized or
                        any(part.lower() in twitch_username for part in streamer_name.split())):
                        
                        logger.info(f"Username match found: {twitch_username} for {streamer_name}")
                        
                        # Fetch the page content
                        content = fetch_page_content(url)
                        if not content.startswith("Error:"):
                            return {
                                "url": url,
                                "content": content,
                                "source": "Twitch Channel (Google)",
                                "validated": True,
                                "username": twitch_username
                            }
                except Exception as e:
                    logger.warning(f"Error processing Twitch URL {url}: {e}")
        
        logger.info(f"No valid Twitch page found via Google for {streamer_name}")
        return None
        
    except Exception as e:
        logger.warning(f"Google search error: {e}")
        
        # Retry with exponential backoff if we have attempts left
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying Google search for {streamer_name} (attempt {attempt+2})")
            return fetch_twitch_page_google(streamer_name, attempt + 1)
        else:
            logger.warning(f"Max retries reached for Google search method")
            return None

def fetch_twitch_page_selenium(streamer_name):
    """
    Use Selenium as a last resort to find Twitch page.
    This helps bypass CAPTCHA and other anti-scraping measures.
    """
    if not SELENIUM_AVAILABLE:
        logger.warning("Selenium not available, skipping this method")
        return None
        
    logger.info(f"Trying Selenium method for {streamer_name}")
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"user-agent={random_user_agent()}")
    
    driver = None
    try:
        # Initialize the driver
        driver = webdriver.Chrome(options=chrome_options)
        
        # Try common username formats
        username = streamer_name.lower().replace(" ", "")
        url = f"https://www.twitch.tv/{username}"
        
        logger.info(f"Selenium accessing {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(5)
        
        # Check if it's a valid channel page
        page_source = driver.page_source
        non_existent_phrases = [
            "Sorry. Unless you've got a time machine, that content is unavailable.",
            "The page you were looking for doesn't exist yet"
        ]
        
        if not any(phrase in page_source for phrase in non_existent_phrases):
            logger.info(f"Found valid Twitch page via Selenium for {streamer_name}")
            return {
                "url": url,
                "content": page_source[:8000],  # Limit content length
                "source": "Twitch Channel (Selenium)",
                "validated": True,
                "username": username
            }
        
        logger.info(f"No valid Twitch page found via Selenium for {streamer_name}")
        return None
        
    except Exception as e:
        logger.error(f"Selenium error: {e}")
        return None
        
    finally:
        # Clean up
        if driver:
            driver.quit()

def update_json_file(data, filename):
    """Write data to a JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Error updating {filename}: {e}")

def load_json_file(filename):
    """Load data from a JSON file, or return an empty dict if missing or invalid."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def scrape_twitch_pages():
    """
    Process each streamer and search for their Twitch page using multiple methods,
    saving results to filtered_streamers.json
    """
    streamers = read_streamers_from_csv()
    if not streamers:
        logger.error("No streamers found to process.")
        return

    # Load existing data if any
    twitch_data = load_json_file(OUTPUT_FILE)
    
    # Track stats
    total_streamers = len(streamers)
    successful_validations = 0
    
    # Count existing validations
    for streamer in twitch_data:
        if twitch_data[streamer].get("validated", False):
            successful_validations += 1
    
    logger.info(f"Starting Twitch page scraping for {total_streamers} streamers")
    logger.info(f"Found {successful_validations} already validated streamers in existing data")
    
    start_time = time.time()
    
    for i, streamer in enumerate(streamers, 1):
        logger.info(f"Processing {streamer} ({i}/{total_streamers})...")
        
        # Skip if already processed with a validated result
        if streamer in twitch_data and twitch_data[streamer].get("validated", False):
            logger.info(f"Skipping {streamer} - already has validated Twitch page")
            continue
        
        # Try multiple methods to find Twitch page
        
        # Method 1: Direct URL check (fastest and most reliable)
        twitch_result = fetch_twitch_page_direct(streamer)
        
        # Method 2: Google search (if direct failed)
        if not twitch_result:
            logger.info(f"Direct method failed for {streamer}, trying Google search...")
            twitch_result = fetch_twitch_page_google(streamer)
        
        # Method 3: Selenium (last resort)
        if not twitch_result:
            logger.info(f"Google search failed for {streamer}, trying Selenium...")
            twitch_result = fetch_twitch_page_selenium(streamer)
        
        if twitch_result and twitch_result.get("validated", False):
            # We found a valid Twitch page
            twitch_entry = {
                "streamer": streamer,
                "content": twitch_result["content"],
                "url": twitch_result["url"],
                "validated": True,
                "username": twitch_result.get("username", ""),
                "source": twitch_result.get("source", "Unknown")
            }
            successful_validations += 1
            logger.info(f"Successfully validated Twitch page for {streamer}")
        else:
            # No valid Twitch page found after all methods
            twitch_entry = {
                "streamer": streamer,
                "content": "",
                "url": "",
                "validated": False,
                "username": "",
                "source": ""
            }
            logger.info(f"Failed to find valid Twitch page for {streamer} after trying all methods")
        
        # Update data and save to file
        twitch_data[streamer] = twitch_entry
        update_json_file(twitch_data, OUTPUT_FILE)
        
        # Progress update
        success_rate = (successful_validations / i) * 100
        elapsed_time = time.time() - start_time
        avg_time_per_streamer = elapsed_time / i
        remaining_streamers = total_streamers - i
        est_time_remaining = remaining_streamers * avg_time_per_streamer
        
        logger.info(f"Progress: {i}/{total_streamers} ({i/total_streamers:.1%}) - Success rate: {success_rate:.1f}%")
        logger.info(f"Elapsed time: {elapsed_time/60:.1f} minutes - Est. remaining: {est_time_remaining/60:.1f} minutes")
        
        # Wait before next streamer to avoid rate limiting
        if i < total_streamers:
            delay = generate_jitter(5, 0.5)
            logger.info(f"Waiting for {delay:.2f} seconds before next streamer...")
            time.sleep(delay)
    
    # Final stats
    elapsed_time = time.time() - start_time
    logger.info("\nProcessing complete!")
    logger.info(f"Total streamers processed: {total_streamers}")
    logger.info(f"Successful validations: {successful_validations}")
    logger.info(f"Success rate: {(successful_validations/total_streamers)*100:.1f}%")
    logger.info(f"Total time: {elapsed_time/60:.1f} minutes")
    logger.info(f"Data saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    try:
        logger.info("-" * 50)
        logger.info(f"Starting Twitch scraper at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        scrape_twitch_pages()
    except KeyboardInterrupt:
        logger.warning("\nScript interrupted by user.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info(f"Script finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("-" * 50)