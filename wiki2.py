import time
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import random

# List of banned URL substrings for social media and non-encyclopedic content.
BAD_URL_SUBSTRINGS = [
    "instagram.com",
    "tiktok.com",
    "twitch.tv",
    "x.com",
    "reddit.com",
    "facebook.com",
    "youtube.com",  # Optionally, you can ban YouTube if you don't want video pages.
    "twitter.com"   # Sometimes Twitter may show up too.
]
# Explicitly banned Twitch Wikipedia page.
BAD_WIKI_LINK = "https://en.wikipedia.org/wiki/Twitch_(service)"

def is_bad_url(url):
    """Return True if the URL is from a banned domain or is the banned Twitch Wikipedia page."""
    for bad_substring in BAD_URL_SUBSTRINGS:
        if bad_substring in url:
            return True
    if url.strip().lower() == BAD_WIKI_LINK.lower():
        return True
    return False

def read_streamers_from_csv(file_path="top_1000_twitch.csv"):
    """Read streamer names from CSV file."""
    try:
        df = pd.read_csv(file_path)
        return df["Name"].tolist()
    except FileNotFoundError:
        print(f"Error: {file_path} not found.")
        return []
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return []

def format_streamer_name(name):
    """Format streamer name for better matching."""
    return name.replace("_", " ").title()

def random_user_agent():
    """Return a random user agent string from a sample list."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
    ]
    return random.choice(user_agents)

def fetch_page_content(url, timeout=10):
    """Attempt to scrape full content from a given URL using a random user agent."""
    try:
        headers = {'User-Agent': random_user_agent()}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.get_text(separator='\n', strip=True)
        return content  # Return full content with no slicing.
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_google_scrapable_content(streamer_name, max_results=5):
    """
    Search Google using the query "[streamer name] twitch wikipedia" and check each result sequentially.
    Return the first scrapable page that is not from a banned domain.
    """
    query = f"{streamer_name} twitch wikipedia"
    delay_before = random.randint(2, 5)
    print(f"Waiting {delay_before} seconds before performing Google search for {streamer_name}...")
    time.sleep(delay_before)
    
    for url in search(query, num_results=max_results):
        if is_bad_url(url):
            print(f"Skipping banned URL: {url}")
            continue

        time.sleep(random.uniform(1, 3))
        print(f"Attempting to scrape URL: {url}")
        content = fetch_page_content(url)
        if not content.startswith("Error:"):
            print(f"Success with URL: {url}")
            return {
                "url": url,
                "content": content,
                "source": "Google Search"
            }
        else:
            print(f"URL {url} not scrapable, trying next result...")
    
    return {
        "url": "",
        "content": "",
        "source": "Google Search"
    }

def update_json_file(data, filename):
    """Write data to a JSON file."""
    try:
        with open(filename, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error updating {filename}: {e}")

def load_json_file(filename):
    """Load data from a JSON file, or return an empty dict if missing or invalid."""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def compile_streamer_wikipedia():
    """Process each streamer and update wikipage2.json accordingly."""
    streamers = read_streamers_from_csv()
    if not streamers:
        print("No streamers found to process.")
        return

    # Reprocess every streamer.
    wiki_data = load_json_file("wikipage2.json")
    
    for i, streamer in enumerate(streamers, 1):
        print(f"Processing {streamer} ({i}/{len(streamers)})...")
        formatted = format_streamer_name(streamer)
        
        result = fetch_google_scrapable_content(streamer)
        if result["url"]:
            wiki_entry = {
                "streamer": streamer,
                "formatted_name": formatted,
                "wikipedia_summary": result["content"],
                "link": result["url"],
                "source": result["source"]
            }
        else:
            wiki_entry = {
                "streamer": streamer,
                "formatted_name": formatted,
                "wikipedia_summary": "Failed to retrieve page.",
                "link": "",
                "source": ""
            }
        
        # Overwrite any existing entry for this streamer.
        wiki_data[streamer] = wiki_entry
        update_json_file(wiki_data, "wikipage2.json")
        print(f"Updated wikipage2.json for {streamer}.")
        
        delay = random.randint(5, 15)
        print(f"Waiting for {delay} seconds before next streamer...")
        time.sleep(delay)
    
    print("Processing complete. Data saved to wikipage2.json.")

if __name__ == "__main__":
    try:
        compile_streamer_wikipedia()
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
