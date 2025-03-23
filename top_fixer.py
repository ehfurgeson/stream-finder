import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def scrape_esports_channels(num_pages = 2, base_url = "https://twitchtracker.com/channels/ranking/english/esports", delay_range = (4, 9), max_retries = 3):
    """
    Scrape esports channels from TwitchTracker using Selenium.
    
    Parameters:
    -----------
    num_pages : int
        Number of pages to scrape (default 2)
    base_url : str
        Base URL for the TwitchTracker esports ranking page
    delay_range : tuple
        Range of seconds to delay between requests (min, max)
    max_retries : int
        Maximum number of retry attempts for each page
    
    Returns:
    --------
    List of esports channel names
    """
    # Create list to store esports channel names
    esports_names = []
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Initialize the driver
    driver = webdriver.Chrome(options = chrome_options)
    
    try:
        # Loop through each page
        page = 1
        while page <= num_pages:
            # Construct the URL for the current page
            url = f"{base_url}?page={page}"
            
            # Initialize retry counter
            retry_count = 0
            success = False
            
            # Retry loop
            while retry_count < max_retries and not success:
                try:
                    # Navigate to the page
                    driver.get(url)
                    
                    # Wait for the table to load
                    wait = WebDriverWait(driver, 10)
                    table = wait.until(EC.presence_of_element_located((By.ID, "channels")))
                    
                    print(f"Successfully loaded esports page {page}")
                    
                    # Find all rows in the table body
                    rows = driver.find_elements(By.CSS_SELECTOR, "#channels tbody tr")
                    
                    # For each row (excluding ad rows)
                    for row in rows:
                        # Check if this is an ad row
                        try:
                            colspan = row.find_element(By.TAG_NAME, "td").get_attribute("colspan")
                            if colspan:  # This is an ad row
                                continue
                        except NoSuchElementException:
                            pass
                        
                        try:
                            # Extract cells
                            cells = row.find_elements(By.TAG_NAME, "td")
                            
                            # Extract name (third td > a)
                            name = cells[2].find_element(By.TAG_NAME, "a").text
                            
                            # Add to list
                            esports_names.append(name)
                        except (IndexError, NoSuchElementException) as e:
                            print(f"Error processing a row: {e}")
                    
                    # Mark as successful
                    success = True
                    
                except TimeoutException:
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = random.uniform(delay_range[0] * 1.5, delay_range[1] * 1.5)  # Longer wait for retries
                        print(f"Timeout waiting for esports page {page}. Retrying ({retry_count}/{max_retries}) after {wait_time:.2f} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"Failed to load esports page {page} after {max_retries} attempts. Moving to next page.")
                except Exception as e:
                    print(f"Error scraping esports page {page}: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        wait_time = random.uniform(delay_range[0], delay_range[1])
                        print(f"Retrying ({retry_count}/{max_retries}) after {wait_time:.2f} seconds...")
                        time.sleep(wait_time)
                    else:
                        print(f"Failed to process esports page {page} after {max_retries} attempts. Moving to next page.")
            
            # Move to the next page
            page += 1
            
            # Random delay between requests to avoid being blocked
            if page <= num_pages:
                delay = random.uniform(delay_range[0], delay_range[1])
                print(f"Waiting {delay:.2f} seconds before the next request...")
                time.sleep(delay)
    
    finally:
        # Always close the driver
        driver.quit()
    
    return esports_names

def filter_esports_from_csv(input_csv = "top_1000_twitch.csv", output_csv = "filtered_twitch_streamers.csv"):
    """
    Filter out esports channels from the Twitch streamers CSV file.
    Also removes channels with "ESL_" prefix or containing "PGL".
    
    Parameters:
    -----------
    input_csv : str
        Path to the input CSV file containing all streamers
    output_csv : str
        Path to save the filtered CSV file
    """
    # Scrape esports channel names
    print("Scraping esports channels...")
    esports_names = scrape_esports_channels()
    print(f"Found {len(esports_names)} esports channels.")
    
    # Convert to lowercase for case-insensitive comparison
    esports_names_lower = [name.lower() for name in esports_names]
    
    # Load the streamers CSV
    try:
        streamers_df = pd.read_csv(input_csv)
        original_count = len(streamers_df)
        print(f"Loaded {original_count} streamers from {input_csv}")
        
        # Make a copy to identify removed channels
        all_streamers = streamers_df.copy()
        
        # Filter out esports channels (case-insensitive)
        filtered_df = streamers_df[~streamers_df["Name"].str.lower().isin(esports_names_lower)]
        
        # Also filter out channels with "ESL_" prefix (case-insensitive)
        filtered_df = filtered_df[~filtered_df["Name"].str.lower().str.startswith("esl_")]
        
        # Also filter out channels containing "PGL" (case-insensitive)
        filtered_df = filtered_df[~filtered_df["Name"].str.lower().str.contains("pgl")]
        
        filtered_count = len(filtered_df)
        removed_count = original_count - filtered_count
        
        # Save filtered DataFrame to CSV
        filtered_df.to_csv(output_csv, index = False)
        
        print(f"Removed {removed_count} channels (esports channels and those with ESL_/PGL).")
        print(f"Saved {filtered_count} filtered streamers to {output_csv}")
        
        # Print the names of removed channels for verification
        if removed_count > 0:
            # Get the names that were kept in the filtered DataFrame
            kept_names = set(filtered_df["Name"].str.lower())
            # Get all names from original DataFrame
            all_names = set(all_streamers["Name"].str.lower())
            # Calculate the removed names
            removed_names_lower = all_names - kept_names
            # Get the original case-sensitive names that were removed
            removed_channels = all_streamers[all_streamers["Name"].str.lower().isin(removed_names_lower)]["Name"].tolist()
            
            print("\nRemoved channels:")
            for channel in removed_channels:
                # Identify why each channel was removed
                channel_lower = channel.lower()
                if channel_lower in esports_names_lower:
                    reason = "Esports channel"
                elif channel_lower.startswith("esl_"):
                    reason = "ESL_ prefix"
                elif "pgl" in channel_lower:
                    reason = "Contains PGL"
                else:
                    reason = "Unknown reason"
                    
                print(f"- {channel} ({reason})")
    
    except FileNotFoundError:
        print(f"Error: Could not find the input file {input_csv}")
    except Exception as e:
        print(f"Error processing the CSV file: {e}")

if __name__ == "__main__":
    filter_esports_from_csv()