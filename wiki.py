import requests
from bs4 import BeautifulSoup
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re
import json

STREAMERS = [
    "Kai Cenat", "Ninja", "xQc", "Ibai Llanos", "AuronPlay",
    "Shroud", "Pokimane", "Rubius", "Dr DisRespect", "Ludwig Ahgren"
]

def get_wikipedia_summary(streamer_name):
    """Scrape Wikipedia summary using BeautifulSoup."""
    url = f"https://en.wikipedia.org/wiki/{streamer_name.replace(' ', '_')}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        paragraphs = soup.find_all("p")
        
        summary = " ".join([p.text for p in paragraphs[:3]]) 
        return summary.strip()
    else:
        return "Failed to retrieve Wikipedia page."

def compile_streamer_wikipedia():
    """Compile Wikipedia summaries for top 10 streamers and save as JSON."""
    data = []
    for streamer in STREAMERS:
        print(f"Scraping Wikipedia summary for {streamer}...")
        summary = get_wikipedia_summary(streamer)
        data.append({"streamer": streamer, "wikipedia_summary": summary})
    
    with open("top_streamers_wikipedia.json", "w", encoding="utf-8") as json_file:
        json.dump(data, json_file, ensure_ascii=False, indent=4)
    
    print("Dataset saved as top_streamers_wikipedia.json")

def generate_word_cloud():
    """Generates a word cloud from the Wikipedia summaries."""
    with open("top_streamers_wikipedia.json", "r", encoding="utf-8") as json_file:
        data = json.load(json_file)
    
    text = " ".join([entry["wikipedia_summary"] for entry in data if entry["wikipedia_summary"] != "Failed to retrieve Wikipedia page"])
    
    text = re.sub(r'http\S+|www\S+', '', text)  
    text = re.sub(r'[^A-Za-z0-9 ]+', '', text)  
    
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    
    plt.figure(figsize=(10, 5))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.title("Word Cloud for Top Streamers Wikipedia Summaries")
    plt.show()

compile_streamer_wikipedia()
generate_word_cloud()
