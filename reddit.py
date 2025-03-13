import pandas as pd
import matplotlib.pyplot as plt
import logging
logging.basicConfig(level=logging.DEBUG)

import ssl
import certifi
ssl._create_default_https_context = ssl.create_default_context(cafile=certifi.where())

import praw
import re
from wordcloud import WordCloud, STOPWORDS
import datetime

# Define the query for Reddit search
QUERY = "Kai Cenat"

# Initialize Reddit client with your credentials
reddit = praw.Reddit(client_id='01QZ_xjftNaD37KztVGK6w',
                     client_secret='O3eYDfW96Y_Ccm1y8KcCYHksBfdmIw',
                     user_agent='StreamFinderApp/0.1 by JavaScript1202')

reddit_posts = []
max_posts = 500  # sample size

# Calculate timestamp for one year ago (365 days)
one_year_ago = datetime.datetime.now() - datetime.timedelta(days=365)

# Search Reddit for posts mentioning the query; sort by top posts within the past year.
# Then filter manually to include only posts from the last year.
for post in reddit.subreddit('all').search(QUERY, sort='top', time_filter='year', limit=max_posts):
    post_date = datetime.datetime.fromtimestamp(post.created_utc)
    if post_date >= one_year_ago:
        reddit_posts.append([post.title, post.score, post.id, post.created_utc])

# Create a DataFrame for Reddit posts
reddit_df = pd.DataFrame(reddit_posts, columns=['Title', 'Score', 'ID', 'Created'])

# Save the scraped data to a CSV file (this will replace the file if it exists)
reddit_csv_filename = "kai_cenat_reddit.csv"
reddit_df.to_csv(reddit_csv_filename, index=False)
print(f"Reddit data saved to {reddit_csv_filename}")

# --- Word Cloud Generation ---
# Concatenate all post titles into one large string
text = " ".join(reddit_df["Title"].astype(str).tolist())

# Clean text: remove URLs and punctuation
text = re.sub(r"http\S+", "", text)  # Remove URLs
text = re.sub(r"[^\w\s]", "", text)    # Remove punctuation

# Process the query to form stopwords
all_query_terms = QUERY.split()
main_search_terms = [term.strip() for term in all_query_terms 
                     if term.upper() != "OR" and not term.startswith("lang:")]

# Define additional irrelevant terms to exclude from the word cloud
additional_stopwords = {"streamer", "streaming", "stream", "twitch"}

# Combine the default STOPWORDS with the query terms and additional stopwords
custom_stopwords = STOPWORDS.union(main_search_terms, additional_stopwords)

# Generate the word cloud object using the custom stopwords
wordcloud = WordCloud(width=800,
                      height=400,
                      background_color="white",
                      stopwords=custom_stopwords,
                      collocations=False).generate(text)

# Plot and save the word cloud
plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation="bilinear")
plt.axis("off")
plt.title("Word Cloud for Kai Cenat Reddit Titles (Last Year)")
plt.tight_layout()
plt.savefig("reddit_wordcloud.png")
plt.show()

print("Word cloud generated and saved as 'reddit_wordcloud.png'")
