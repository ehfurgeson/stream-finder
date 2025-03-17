import csv
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import re
import os

def setup_driver():
    """Set up and return a configured Chrome webdriver"""
    chrome_options = Options()
    # Uncomment the line below if you want to run in headless mode
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-popup-blocking")
    
    driver = webdriver.Chrome(options = chrome_options)
    return driver

def find_twitch_url(streamer_name, driver):
    """
    Search for streamer on Google with 'twitch' and extract the Twitch URL
    
    Args:
        streamer_name: The name of the streamer
        driver: Selenium webdriver instance
        
    Returns:
        Dictionary containing the streamer name and their Twitch URL
    """
    try:
        search_query = f"{streamer_name} twitch"
            
        # Navigate to Google
        driver.get("https://www.google.com")
        
        # Accept cookies if the dialog appears (this varies by region)
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accept all')]"))
            ).click()
        except (TimeoutException, NoSuchElementException):
            # Cookie dialog might not appear, so we can ignore this
            pass
        
        # Find the search box and enter the query
        search_box = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.clear()
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.RETURN)
        
        # Wait for results and get the first result URL
        # Look specifically for twitch.tv links
        twitch_results = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
        )
        
        # Try to find a direct Twitch URL
        twitch_url = None
        
        # Look for direct twitch.tv URLs in the search results
        links = driver.find_elements(By.CSS_SELECTOR, "div.g a")
        for link in links:
            href = link.get_attribute('href')
            if href and 'twitch.tv' in href:
                # Skip URLs to Twitch's main page or generic sections
                if re.match(r'https?://www\.twitch\.tv/directory', href) or href == 'https://www.twitch.tv/':
                    continue
                twitch_url = href
                break
        
        # If no specific Twitch URL found, just take the first result
        if not twitch_url and links:
            twitch_url = links[0].get_attribute('href')
            
        return {
            "streamer_name": streamer_name,
            "twitch_url": twitch_url or "Not found"
        }
        
    except Exception as e:
        print(f"Error processing {streamer_name}: {str(e)}")
        return {
            "streamer_name": streamer_name,
            "twitch_url": f"Error: {str(e)}"
        }

def main():
    # Read the CSV file with streamer data
    try:
        df = pd.read_csv('top_1000_twitch.csv')
        # Assuming first column is rank and second is name
        streamers = df.iloc[:, 1].tolist()  # Get the second column (names)
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        return
    
    # Set up the driver
    driver = setup_driver()
    
    # Prepare CSV for results
    results = []
    
    try:
        # Process each streamer
        for i, streamer_name in enumerate(streamers):
            print(f"Processing {i+1}/{len(streamers)}: {streamer_name}")
            
            # Search and find URL
            result = find_twitch_url(streamer_name, driver)
            results.append(result)
            
            # Pause between requests to avoid getting blocked
            time.sleep(2)
            
        # Save all results to a CSV file
        with open("streamer_twitch_urls.csv", "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = ["streamer_name", "twitch_url"]
            writer = csv.DictWriter(csvfile, fieldnames = fieldnames)
            writer.writeheader()
            writer.writerows(results)
            
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        
        # Save any results collected so far
        if results:
            with open("streamer_twitch_urls_partial.csv", "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = ["streamer_name", "twitch_url"]
                writer = csv.DictWriter(csvfile, fieldnames = fieldnames)
                writer.writeheader()
                writer.writerows(results)
    
    finally:
        # Close the driver
        driver.quit()
        print("Process completed.")

if __name__ == "__main__":
    main()