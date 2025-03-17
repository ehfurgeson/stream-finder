import pandas as pd
import logging
import ssl
import certifi
import praw
import re
import datetime
import json
import time

logging.basicConfig(level=logging.DEBUG)
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())

def scrape_reddit_for_streamer(streamer, max_posts=500):
    """
    Scrape top Reddit posts mentioning the streamer from the past year.
    Returns a list of dictionaries containing post info.
    """
    reddit = praw.Reddit(client_id='01QZ_xjftNaD37KztVGK6w',
                         client_secret='O3eYDfW96Y_Ccm1y8KcCYHksBfdmIw',
                         user_agent='StreamFinderApp/0.1 by JavaScript1202')
    
    posts = []
    one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
    
    for post in reddit.subreddit('all').search(streamer, sort='top', time_filter='year', limit=max_posts):
        post_date = datetime.datetime.fromtimestamp(post.created_utc)
        if post_date >= one_year_ago:
            posts.append({
                "Title": post.title,
                "Score": post.score,
                "ID": post.id,
                "Created": post.created_utc
            })
    return posts

def update_reddit_json(streamer, posts, json_filename="reddit.json"):
    """
    Loads an existing JSON file (or creates an empty dict if not found or empty),
    appends the scraped posts for the streamer (avoiding duplicates), and writes the data back.
    """
    try:
        with open(json_filename, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    # Append posts if the streamer exists, or add a new key otherwise.
    if streamer in data:
        existing_ids = {p["ID"] for p in data[streamer]}
        new_posts = [p for p in posts if p["ID"] not in existing_ids]
        data[streamer].extend(new_posts)
    else:
        data[streamer] = posts

    with open(json_filename, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Updated {json_filename} with data for streamer: {streamer}")


def main():
    # Read the CSV file that contains the top 1000 streamers
    df = pd.read_csv("top_1000_twitch.csv")
    
    # Iterate over each streamer in the CSV (assuming column 'Name' contains streamer names)
    for idx, row in df.iterrows():
        streamer = row["Name"].strip()
        print(f"\nProcessing streamer: {streamer}")
        
        posts = scrape_reddit_for_streamer(streamer)
        print(f"Scraped {len(posts)} posts for {streamer}")
        
        update_reddit_json(streamer, posts)
        
        # Optional: pause between requests to be polite to Reddit's servers.
        time.sleep(2)

if __name__ == "__main__":
    main()
