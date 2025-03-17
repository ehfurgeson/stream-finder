import time
import json
import pandas as pd
import wikipedia
import wikipediaapi
from top_scraper import scrape_twitch_streamers  # Import the Twitch scraper

def format_streamer_name(name):
    """Format streamer name for better Wikipedia matching."""
    formatted_name = name.replace("_", " ").title()  # Convert to title case
    return formatted_name

def get_wikipedia_summary(streamer_name):
    """Fetch Wikipedia summary using the Wikipedia API."""
    formatted_name = format_streamer_name(streamer_name)

    try:
        # Try to get the exact Wikipedia page
        summary = wikipedia.summary(formatted_name, sentences=3)
        return summary

    except wikipedia.DisambiguationError as e:
        # If multiple results exist, pick the first one
        print(f"DisambiguationError for {formatted_name}, selecting first option: {e.options[0]}")
        try:
            summary = wikipedia.summary(e.options[0], sentences=3)
            return summary
        except Exception as inner_e:
            print(f"Failed to resolve disambiguation: {inner_e}")
            return "Disambiguation error, unable to fetch summary."

    except wikipedia.PageError:
        # If no exact match, search Wikipedia for similar names
        print(f"No exact match for {formatted_name}, searching Wikipedia...")
        search_results = wikipedia.search(formatted_name)

        if search_results:
            try:
                summary = wikipedia.summary(search_results[0], sentences=3)  # Use first search result
                return summary
            except Exception as search_e:
                print(f"Failed on search fallback: {search_e}")
                return "Search error, unable to fetch summary."

        return "Failed to retrieve Wikipedia page."

    except Exception as e:
        print(f"Error fetching Wikipedia page for {formatted_name}: {e}")
        return "Error retrieving Wikipedia page."

def compile_streamer_wikipedia():
    """Scrape Wikipedia summaries for the top Twitch streamers and save as JSON."""
    # Get the top 1000 streamers
    print("Fetching top Twitch streamers from TwitchTracker...")
    streamers_df = scrape_twitch_streamers(num_pages=20)

    data = []
    for _, row in streamers_df.iterrows():
        streamer = row["Name"]
        formatted_streamer = format_streamer_name(streamer)
        
        print(f"Fetching Wikipedia summary for {formatted_streamer}...")
        summary = get_wikipedia_summary(formatted_streamer)

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
        
        text = " ".join([entry["wikipedia_summary"] for entry in data if entry["wikipedia_summary"] != "Failed to retrieve Wikipedia page"])
        
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt
        import re

        text = re.sub(r'http\S+|www\S+', '', text)  
        text = re.sub(r'[^A-Za-z0-9 ]+', '', text)  
        
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
