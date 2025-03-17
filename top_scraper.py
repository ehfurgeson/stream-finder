import time
import random
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def scrape_twitch_streamers(num_pages=20, base_url="https://twitchtracker.com/channels/ranking", delay_range=(1, 3)):
    """
    Scrape top Twitch streamers from TwitchTracker using Selenium.
    
    Parameters:
    -----------
    num_pages : int
        Number of pages to scrape (default 20)
    base_url : str
        Base URL for the TwitchTracker ranking page
    delay_range : tuple
        Range of seconds to delay between requests (min, max)
    
    Returns:
    --------
    DataFrame containing each streamer's rank and name
    """
    # Create lists to store data
    ranks = []
    names = []
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode (no UI)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Loop through each page
        for page in range(1, num_pages + 1):
            # Construct the URL for the current page
            url = f"{base_url}?page={page}"
            
            try:
                # Navigate to the page
                driver.get(url)
                
                # Wait for the table to load
                wait = WebDriverWait(driver, 10)
                table = wait.until(EC.presence_of_element_located((By.ID, "channels")))
                
                print(f"Successfully loaded page {page}")
                
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
                        
                        # Extract rank (first td)
                        rank = cells[0].text.strip('#')
                        
                        # Extract name (third td > a)
                        name = cells[2].find_element(By.TAG_NAME, "a").text
                        
                        # Add to lists
                        ranks.append(rank)
                        names.append(name)
                    except (IndexError, NoSuchElementException) as e:
                        print(f"Error processing a row: {e}")
                
            except TimeoutException:
                print(f"Timeout waiting for page {page} to load")
            except Exception as e:
                print(f"Error scraping page {page}: {e}")
            
            # Random delay between requests to avoid being blocked
            if page < num_pages:
                delay = random.uniform(delay_range[0], delay_range[1])
                print(f"Waiting {delay:.2f} seconds before the next request...")
                time.sleep(delay)
    
    finally:
        # Always close the driver
        driver.quit()
    
    # Create a DataFrame
    streamers_df = pd.DataFrame({
        'Rank': ranks,
        'Name': names
    })
    
    return streamers_df

# Example usage
if __name__ == "__main__":
    # Scrape the first 20 pages
    streamers = scrape_twitch_streamers(num_pages=20)
    
    # Display the first few rows
    print(streamers.head())
    
    # Save to CSV
    streamers.to_csv('top_1000_twitch.csv', index=False)
    print(f"Saved data for {len(streamers)} streamers to twitch_top_streamers.csv")