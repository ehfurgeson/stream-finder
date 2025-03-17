import time
import json
import pandas as pd
import wikipedia
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from top_scraper import scrape_twitch_streamers  # Import the Twitch scraper

def format_streamer_name(name):
    """Format streamer name for better Wikipedia matching."""
    return name.replace("_", " ").title()

def get_wikipedia_summary_selenium(streamer_name):
    """Use Selenium to find and scrape Wikipedia summary from Google search."""
    formatted_name = format_streamer_name(streamer_name)
    search_query = f"{formatted_name} wikipedia"
    
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.get("https://www.google.com")
    
    search_box = driver.find_element(By.NAME, "q")
    search_box.send_keys(search_query)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)
    
    # Find first Wikipedia link
    links = driver.find_elements(By.CSS_SELECTOR, "a")
    wiki_url = None
    for link in links:
        href = link.get_attribute("href")
        if href and "wikipedia.org/wiki/" in href:
            wiki_url = href
            break
    
    driver.quit()
    
    if not wiki_url:
        return "Wikipedia page not found."
    
    # Scrape Wikipedia summary
    try:
        response = requests.get(wiki_url)
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.select("p")
        for para in paragraphs:
            text = para.get_text().strip()
            if text:
                return text[:500]  # Limit to first 500 characters
    except Exception as e:
        print(f"Error fetching Wikipedia page for {formatted_name}: {e}")
        return "Error retrieving Wikipedia page."

def compile_streamer_wikipedia():
    """Scrape Wikipedia summaries for the top Twitch streamers using Selenium."""
    print("Fetching top Twitch streamers from TwitchTracker...")
    streamers_df = scrape_twitch_streamers(num_pages=20)
    
    data = []
    for _, row in streamers_df.iterrows():
        streamer = row["Name"]
        formatted_streamer = format_streamer_name(streamer)
        
        print(f"Fetching Wikipedia summary for {formatted_streamer}...")
        summary = get_wikipedia_summary_selenium(formatted_streamer)

        data.append({
            "streamer": streamer,
            "formatted_name": formatted_streamer,
            "wikipedia_summary": summary
        })
    
    # Save data to a JSON file
    with open("top_streamers_wikipedia.json", "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    
    print("Dataset saved as top_streamers_wikipedia.json")

def generate_word_cloud():
    """Generates a word cloud from the Wikipedia summaries."""
    try:
        with open("top_streamers_wikipedia.json", "r", encoding="utf-8") as json_file:
            data = json.load(json_file)
        
        text = " ".join([entry["wikipedia_summary"] for entry in data if "Wikipedia page not found" not in entry["wikipedia_summary"]])
        
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        import re

        text = re.sub(r'http\S+|www\S+', '', text)  # Remove URLs
        text = re.sub(r'[^A-Za-z0-9 ]+', '', text)  # Remove special characters
        
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
        
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis("off")
        plt.title("Word Cloud for Top Streamers Wikipedia Summaries")
        plt.show()
    
    except FileNotFoundError:
        print("Error: JSON file not found. Run compile_streamer_wikipedia() first.")

# Run the script
if __name__ == "__main__":
    compile_streamer_wikipedia()  # Scrape Wikipedia summaries
    generate_word_cloud()  # Generate word cloud from summaries
