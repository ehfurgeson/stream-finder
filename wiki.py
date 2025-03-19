import time
import json
import pandas as pd
import requests
from bs4 import BeautifulSoup
import wikipediaapi
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

def fetch_wikipedia_content(streamer_name):
    """Fetch Wikipedia content with a single attempt."""
    wiki = wikipediaapi.Wikipedia(
        language='en',
        extract_format=wikipediaapi.ExtractFormat.WIKI,
        user_agent='StreamerWikiScraper/1.0 (contact: your-email@example.com)'
    )
    
    formatted_name = format_streamer_name(streamer_name)
    
    page = wiki.page(formatted_name)
    if page.exists():
        return {
            "url": page.fullurl,
            "content": page.text,
            "source": "Wikipedia"
        }
    
    page = wiki.page(f"{formatted_name} (streamer)")
    if page.exists():
        return {
            "url": page.fullurl,
            "content": page.text,
            "source": "Wikipedia"
        }
    
    return None

def fetch_google_search_content(streamer_name, retries=3, backoff_factor=2):
    """Fetch content from the first Google Search result with retries and exponential backoff."""
    query = f"{streamer_name} twitch wikipedia"
    url = None
    for attempt in range(retries):
        try:
            # Use googlesearch to find the first result
            for url in search(query, num_results=1):
                print(f"Scraping content from: {url}")
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                content = soup.get_text(separator='\n', strip=True)
                return {
                    "url": url,
                    "content": content[:5000],  # Limit content size for practicality
                    "source": "Google Search"
                }
            return {
                "url": None,
                "content": "No relevant content found.",
                "source": "Google Search"
            }
        except requests.HTTPError as e:
            if e.response.status_code == 429:
                # Exponential backoff
                wait_time = backoff_factor ** attempt
                print(f"429 Too Many Requests. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print(f"HTTP error fetching content for {streamer_name}: {e}")
                return {
                    "url": url if url else None,
                    "content": f"Error: {str(e)}",
                    "source": "Google Search"
                }
        except Exception as e:
            print(f"Error fetching content for {streamer_name}: {e}")
            return {
                "url": url if url else None,
                "content": f"Error: {str(e)}",
                "source": "Google Search"
            }
    
    # If all retries fail, return an error message
    return {
        "url": None,
        "content": "Error: Too many retries. Falling back to news search.",
        "source": "Google Search"
    }

def fetch_news_info(streamer_name):
    """Fetch news content about the streamer from a web search."""
    query = f"{streamer_name} streamer news site:*.com | site:*.org | site:*.edu -inurl:(signup login wikipedia)"
    url = None
    try:
        # Use googlesearch to find a news-like article
        for url in search(query, num_results=1):
            print(f"Scraping news article: {url}")
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            content = soup.get_text(separator='\n', strip=True)
            return {
                "url": url,
                "content": content[:5000],  # Limit content size for practicality
                "source": "News Article"
            }
        return {
            "url": None,
            "content": "No news articles found.",
            "source": "News Article"
        }
    except requests.HTTPError as e:
        print(f"HTTP error fetching news for {streamer_name}: {e}")
        return {
            "url": url if url else None,
            "content": f"Error: {str(e)}",
            "source": "News Article"
        }
    except Exception as e:
        print(f"Error fetching news for {streamer_name}: {e}")
        return {
            "url": url if url else None,
            "content": f"Error: {str(e)}",
            "source": "News Article"
        }

def update_json_file(data, filename="wikipage.json"):
    """Update the JSON file with current data."""
    try:
        with open(filename, "w", encoding="utf-8") as json_file:
            json.dump(data, json_file, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error updating {filename}: {e}")

def compile_streamer_wikipedia():
    """Compile streamer data, updating JSON file progressively."""
    streamers = read_streamers_from_csv()
    if not streamers:
        print("No streamers found to process.")
        return

    data = []
    update_json_file(data)
    print("Initialized wikipage.json")

    for i, streamer in enumerate(streamers, 1):
        print(f"Processing {streamer} ({i}/{len(streamers)})...")
        
        result = fetch_wikipedia_content(streamer)
        
        if result is None:
            print(f"No Wikipedia page found for {streamer}, falling back to Google Search...")
            result = fetch_google_search_content(streamer)
            
            # If Google Search fails (e.g., due to 429 errors), fall back to news search
            if result["content"].startswith("Error:"):
                print(f"Google Search failed for {streamer}, falling back to news search...")
                result = fetch_news_info(streamer)
        
        data.append({
            "streamer": streamer,
            "url": result["url"],
            "content": result["content"],
            "source": result["source"]
        })
        
        update_json_file(data)
        print(f"Updated wikipage.json with {streamer}")
        
        # Random delay between 5 to 15 seconds to avoid being flagged as a bot
        delay = random.randint(5, 15)
        print(f"Waiting for {delay} seconds before the next request...")
        time.sleep(delay)

    print("Dataset fully processed and saved as wikipage.json")

if __name__ == "__main__":
    try:
        compile_streamer_wikipedia()
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")
    except Exception as e:
        print(f"Unexpected error: {e}")