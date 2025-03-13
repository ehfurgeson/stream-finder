from twikit import Client, TooManyRequests
import pandas as pd
import re
import time
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from datetime import datetime
import os
import csv
from configparser import ConfigParser
from random import randint
import asyncio

# Query for Kai Cenat tweets
QUERY = 'Kai Cenat OR kaicenat lang:en'
MINIMUM_TWEETS = 500

async def get_tweets(client, tweets=None):
    """Get tweets using pagination"""
    if tweets is None:
        # First request
        print(f'{datetime.now()} - Getting tweets for query: {QUERY}')
        tweets = await client.search_tweet(QUERY, product='Top')
    else:
        # Subsequent requests
        wait_time = randint(2, 5)
        print(f'{datetime.now()} - Getting next tweets after {wait_time} seconds...')
        await asyncio.sleep(wait_time)
        tweets = await tweets.next()
    return tweets

def generate_wordcloud(tweet_texts):
    print(f"Generating word cloud from {len(tweet_texts)} tweets")
    
    # Join and clean text
    all_text = ' '.join(tweet_texts)
    all_text = re.sub(r'http\S+', '', all_text)  # Remove URLs
    all_text = re.sub(r'#\S+', '', all_text)    # Remove hashtags
    all_text = re.sub(r'@\S+', '', all_text)    # Remove mentions
    all_text = re.sub(r'[^\w\s]', '', all_text) # Remove punctuation

    # Define stopwords
    
    from wordcloud import STOPWORDS
    all_query_terms = QUERY.split()
    query_words = all_query_terms
    main_search_terms = [
        term.strip() 
        for term in query_words 
        if term.upper() != 'OR'  
        and not term.startswith('lang:')  # Exclude language filters like 'lang:en'
    ]
    #new
    # Define additional terms to exclude from the word cloud
    additional_stopwords = {'streamer', 'streaming', 'stream', 'twitch'}
    
    # Combine base stopwords with query terms and additional terms
    custom_stopwords = STOPWORDS.union(main_search_terms, additional_stopwords)
    # Generate word cloud
    wordcloud = WordCloud(
        width=800, height=400,
        background_color='white',
        stopwords=custom_stopwords,
        min_word_length=4,
        colormap='viridis'
    ).generate(all_text)

    # Display and save
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title('Common Words in Tweets')
    plt.tight_layout()
    plt.savefig('word_cloud.png')
    plt.close()

    print("Word cloud generated and saved as 'word_cloud.png'")

async def main():
    CONFIG_FILE = 'twitter_config.cfg'
    COOKIES_FILE = 'cookies.json'
    client = Client(language='en-US')

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
            raise ValueError("No authentication method available. Provide cookies.json or twitter_config.ini")

        with open('kai_cenat_tweets.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Tweet_count', 'Username', 'Text', 'Created_At', 'Retweets', 'Likes'])

        tweet_count = 0
        tweets = None
        tweet_texts = []

        while tweet_count < MINIMUM_TWEETS:
            try:
                tweets = await get_tweets(client, tweets)
            except TooManyRequests as e:
                rate_limit_reset = datetime.fromtimestamp(e.rate_limit_reset)
                print(f'{datetime.now()} - Rate limit reached. Waiting until {rate_limit_reset}')
                wait_time = (rate_limit_reset - datetime.now()).total_seconds()
                await asyncio.sleep(wait_time)
                continue

            if not tweets:
                print(f'{datetime.now()} - No more tweets found')
                break

            for tweet in tweets:
                tweet_count += 1
                tweet_texts.append(tweet.text)
                with open('kai_cenat_tweets.csv', 'a', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow([
                        tweet_count, tweet.user.screen_name, tweet.text,
                        tweet.created_at, tweet.retweet_count, tweet.favorite_count
                    ])

                if tweet_count >= MINIMUM_TWEETS:
                    break

            print(f'{datetime.now()} - Got {tweet_count} tweets so far')

        print(f'{datetime.now()} - Done! Collected {tweet_count} tweets')

        if tweet_texts:
            generate_wordcloud(tweet_texts)
            print("Analysis complete!")
        else:
            print("No tweets collected, cannot generate word cloud.")

    except Exception as e:
        print(f"Error during execution: {e}")
        print("Please check your authentication and network connection.")

if __name__ == "__main__":
    asyncio.run(main())