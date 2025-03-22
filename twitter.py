from twikit import Client, TooManyRequests
import re
import time
from datetime import datetime
import os
import json
from configparser import ConfigParser
from random import randint
import asyncio
import pandas as pd

# Minimum number of tweets to collect per streamer
MINIMUM_TWEETS = 500

def clean_text(text):
    """Remove URLs and emoji characters from the text."""
    # Remove URLs
    text = re.sub(r"http\S+", "", text)
    # Remove emoji (unicode emoji ranges)
    emoji_pattern = re.compile("["
                               u"\U0001F600-\U0001F64F"  # emoticons
                               u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                               u"\U0001F680-\U0001F6FF"  # transport & map symbols
                               u"\U0001F1E0-\U0001F1FF"  # flags
                               "]+", flags=re.UNICODE)
    text = emoji_pattern.sub(r'', text)
    return text.strip()

async def get_tweets(client, query, tweets=None):
    """Get tweets using pagination for the given query."""
    if tweets is None:
        print(f'{datetime.now()} - Getting tweets for query: {query}')
        tweets = await client.search_tweet(query, product='Top')
    else:
        wait_time = randint(2, 5)
        print(f'{datetime.now()} - Getting next tweets after {wait_time} seconds...')
        await asyncio.sleep(wait_time)
        tweets = await tweets.next()
    return tweets

async def main():
    # List of streamers to process
    def load_streamers_csv(filename):
        df = pd.read_csv(filename)
        # Assumes the CSV has headers 'Rank' and 'Name'
        return df['Name'].tolist()

# Usage:
    streamers= load_streamers_csv('top_1000_twitch.csv')


    # Path to the twitter.json file (guaranteed to exist)
    JSON_FILE = 'twitter.json'
    
    # Initialize twitter_data; if the file is empty, set as empty dict.
    twitter_data = {}
    if os.path.exists(JSON_FILE):
        if os.path.getsize(JSON_FILE) > 0:
            try:
                with open(JSON_FILE, 'r') as jf:
                    twitter_data = json.load(jf)
            except json.decoder.JSONDecodeError:
                print(f"{datetime.now()} - {JSON_FILE} contains invalid JSON. Initializing empty data.")
                twitter_data = {}
        else:
            print(f"{datetime.now()} - {JSON_FILE} is empty. Initializing empty data.")
    else:
        print(f"{datetime.now()} - {JSON_FILE} does not exist. Creating new file.")

    client = Client(language='en-US')
    CONFIG_FILE = 'twitter_config.cfg'
    COOKIES_FILE = 'cookies.json'
    
    try:
        if os.path.exists(COOKIES_FILE):
            print(f"Loading cookies from {COOKIES_FILE}...")
            client.load_cookies(COOKIES_FILE)
            print("Cookies loaded successfully.")
        elif os.path.exists(CONFIG_FILE):
            print(f"No cookies found. Using credentials from {CONFIG_FILE}...")
            config = ConfigParser()
            config.read(CONFIG_FILE)
            username = config['Twitter']['username']
            email = config['Twitter']['email']
            password = config['Twitter']['password']
            await client.login(auth_info_1=username, auth_info_2=email, password=password)
            client.save_cookies(COOKIES_FILE)
            print(f"Logged in and saved cookies to {COOKIES_FILE}")
        else:
            raise ValueError("No authentication method available. Provide cookies.json or twitter_config.cfg")

        streamers = streamers[700:800]
        # Process each streamer in the list
        for streamer in streamers:
            # Create key by removing spaces (e.g., "Kai Cenat" -> "KaiCenat")
            streamer_key = streamer.replace(" ", "")
            # Skip if streamer already exists in twitter.json
            if streamer_key in twitter_data:
                print(f"{datetime.now()} - Tweets for '{streamer_key}' already exist in {JSON_FILE}. Skipping...")
                continue
            
            # Construct query using the streamer's key and the language filter.
            # For example: "KaiCenat lang:en"
            query = f"{streamer_key} lang:en"
            
            tweet_count = 0
            tweets = None
            tweet_texts = []  # list to hold individual tweet texts

            while tweet_count < MINIMUM_TWEETS:
                try:
                    tweets = await get_tweets(client, query, tweets)
                except TooManyRequests as e:
                    rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
                    print(f'{datetime.now()} - Rate limit reached. Waiting until {rate_limit_reset}')
                    wait_time = (rate_limit_reset - datetime.now()).total_seconds()
                    await asyncio.sleep(wait_time)
                    continue

                if not tweets:
                    print(f'{datetime.now()} - No more tweets found for query: {query}')
                    break

                for tweet in tweets:
                    cleaned = clean_text(tweet.text)
                    tweet_texts.append(cleaned)
                    tweet_count += 1
                    if tweet_count >= MINIMUM_TWEETS:
                        break

                print(f'{datetime.now()} - Got {tweet_count} tweets so far for query: {query}')

            print(f'{datetime.now()} - Done! Collected {tweet_count} tweets for "{streamer}"')
            
            # Update the twitter_data with cleaned tweet texts for this streamer
            twitter_data[streamer_key] = tweet_texts

            # Save updated twitter_data back to the JSON file
            with open(JSON_FILE, 'w') as jf:
                json.dump(twitter_data, jf, indent=4)
            print(f"{datetime.now()} - Saved tweets for '{streamer_key}' to {JSON_FILE}")

    except Exception as e:
        print(f"Error during execution: {e}")
        print("Please check your authentication and network connection.")

if __name__ == "__main__":
    asyncio.run(main())
