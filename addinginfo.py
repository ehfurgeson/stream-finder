import requests
import json
from bs4 import BeautifulSoup
import time

# Your private API keys
SERPAPI_KEY = "f8163165484d45e0b213cf9618076a242ec32cd34aaa9b6453b17122f3a130ce"
NEWSAPI_KEY = "b10505ddafe74d2b80cfa50612d8033d"  # Get from https://newsapi.org/

# Load JSON file
with open("wikipage.json", "r", encoding="utf-8") as f:
    streamers_data = json.load(f)

# Function to check if content contains a 429 error
def has_429_error(content):
    return "Error: 429 Client Error: Too Many Requests for url:" in content

# Function to get Twitch-related news from NewsAPI
def get_news_article(query):
    url = f"https://newsapi.org/v2/everything?q={query}&apiKey={NEWSAPI_KEY}&language=en&sortBy=publishedAt"
    
    response = requests.get(url)
    if response.status_code == 200:
        news_data = response.json()
        if "articles" in news_data and len(news_data["articles"]) > 0:
            first_article = news_data["articles"][0]  # Get the latest news
            return first_article["url"]
    
    return None

# Function to get a valid search result (excluding Wikipedia)
def get_valid_link(query):
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "num": 5,
    }
    
    response = requests.get("https://serpapi.com/search", params=params)
    if response.status_code == 200:
        results = response.json()
        if "organic_results" in results:
            for result in results["organic_results"]:
                link = result["link"]
                if "wikipedia.org" not in link and "google.com" not in link and "login" not in link:
                    return link
    return None

# Function to scrape content from a webpage
def scrape_content(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            paragraphs = soup.find_all("p")
            content = " ".join(p.get_text() for p in paragraphs if len(p.get_text().strip()) > 20)  
            if len(content) > 100:
                return content[:2000]
    except Exception as e:
        print(f"❌ Error scraping {url}: {e}")
    
    return None

# Process each streamer
for streamer_data in streamers_data:
    streamer_name = streamer_data["streamer"]
    
    if has_429_error(streamer_data["content"]):
        print(f"⚠️ 429 error detected for {streamer_name}. Searching for news articles...")

        # Try fetching a news article first
        news_link = get_news_article(streamer_name)
        if news_link:
            print(f"✅ Found news article: {news_link}")
            page_content = scrape_content(news_link)
            
            if page_content:
                streamer_data["url"] = news_link
                streamer_data["content"] = page_content
                streamer_data["source"] = "NewsAPI Article"
                print(f"✅ Successfully updated {streamer_name} with news content.")
                continue  # Skip to next streamer if successful

        # If no news article, fallback to Google search
        print(f"🔎 No news found, trying Google search for {streamer_name}...")
        search_query = f"{streamer_name} streamer news"
        valid_link = get_valid_link(search_query)

        if valid_link:
            print(f"✅ Found link: {valid_link}")
            page_content = scrape_content(valid_link)
            
            if page_content:
                streamer_data["url"] = valid_link
                streamer_data["content"] = page_content
                streamer_data["source"] = "Google Search"
                print(f"✅ Successfully updated {streamer_name} with web search content.")
            else:
                print(f"❌ Failed to extract content from {valid_link}.")
        else:
            print(f"❌ No valid alternative site found for {streamer_name}.")

    time.sleep(1)  # Prevent rate limits

# Save updated JSON data
with open("wikipage.json", "w", encoding="utf-8") as f:
    json.dump(streamers_data, f, indent=4, ensure_ascii=False)

print("🎉 All missing data has been updated in wikipage.json!")
