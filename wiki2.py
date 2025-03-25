import time
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
from googlesearch import search
import random

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
    """Attempt to scrape content from a given URL using a random user agent."""
    try:
        headers = {'User-Agent': random_user_agent()}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        content = soup.get_text(separator='\n', strip=True)
        return content[:5000]  # Limit content length for practicality
    except Exception as e:
        return f"Error: {str(e)}"

def fetch_google_scrapable_content(streamer_name, max_results=5):
    """
    Search Google using the query "[streamer name] twitch wikipedia" and return the first scrapable page.
    """
    query = f"{streamer_name} twitch wikipedia"
    delay_before = random.randint(2, 5)
    print(f"Waiting {delay_before} seconds before performing Google search for {streamer_name}...")
    time.sleep(delay_before)
    
    for url in search(query, num_results=max_results):
        time.sleep(random.uniform(1, 3))
        print(f"Attempting to scrape URL: {url}")
        content = fetch_page_content(url)
        if not content.startswith("Error:"):
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
    """Process each streamer and update wikipage2.json and random.json accordingly."""
    streamers = read_streamers_from_csv()
    if not streamers:
        print("No streamers found to process.")
        return

    wiki_data = load_json_file("wikipage2.json")
    random_data = load_json_file("random.json")
    
    for i, streamer in enumerate(streamers, 1):
        # If the streamer already exists and has a non-empty summary, skip processing.
        if streamer in wiki_data and wiki_data[streamer].get("wikipedia_summary", "").strip():
            print(f"Skipping {streamer} as it already has data.")
            continue

        print(f"Processing {streamer} ({i}/{len(streamers)})...")
        formatted = format_streamer_name(streamer)
        
        # First attempt: Google search fallback (only method now)
        result = fetch_google_scrapable_content(streamer)
        if result["url"]:
            if "wikipedia.org" in result["url"]:
                # Since it's a Wikipedia link, store it in wiki_data.
                wiki_entry = {
                    "streamer": streamer,
                    "formatted_name": formatted,
                    "wikipedia_summary": result["content"],
                    "link": result["url"],
                    "source": result["source"]
                }
                random_entry = {
                    "streamer": streamer,
                    "formatted_name": formatted,
                    "content": "",
                    "link": "",
                    "source": ""
                }
            else:
                # For non-Wikipedia links, store in random_data.
                random_entry = {
                    "streamer": streamer,
                    "formatted_name": formatted,
                    "content": result["content"],
                    "link": result["url"],
                    "source": result["source"]
                }
                wiki_entry = {
                    "streamer": streamer,
                    "formatted_name": formatted,
                    "wikipedia_summary": "Failed to retrieve Wikipedia page.",
                    "link": "",
                    "source": ""
                }
        else:
            random_entry = {
                "streamer": streamer,
                "formatted_name": formatted,
                "content": "",
                "link": "",
                "source": ""
            }
            wiki_entry = {
                "streamer": streamer,
                "formatted_name": formatted,
                "wikipedia_summary": "Failed to retrieve Wikipedia page.",
                "link": "",
                "source": ""
            }
        
        wiki_data[streamer] = wiki_entry
        random_data[streamer] = random_entry
        
        update_json_file(wiki_data, "wikipage2.json")
        update_json_file(random_data, "random.json")
        print(f"Updated wikipage2.json and random.json for {streamer}.")
        
        delay = random.randint(5, 15)
        print(f"Waiting for {delay} seconds before next streamer...")
        time.sleep(delay)
    
    print("Processing complete. Data saved to wikipage2.json and random.json.")


if __name__ == "__main__":
    try:
        compile_streamer_wikipedia()
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")
