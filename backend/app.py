import subprocess

# Launch the check_live Flask app in a separate process (non-blocking).
subprocess.Popen(["python", "check_live.py"])


import json
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from helpers.MySQLDatabaseHandler import MySQLDatabaseHandler
import pandas as pd
from collections import defaultdict
import re

# Set ROOT_PATH for linking files
os.environ["ROOT_PATH"] = os.path.abspath(os.path.join("..", os.curdir))

# Get the directory of the current script (backend folder)
current_directory = os.path.dirname(os.path.abspath(__file__))

# Specify the path to the JSON file (init.json) in the backend folder
json_path = os.path.join(current_directory, "init.json")

# Load the JSON data with UTF-8 encoding
with open(json_path, "r", encoding="utf-8") as file:
    combined_data = json.load(file)

# Extract the individual datasets
reddit_data = combined_data["reddit"]
twitter_data = combined_data["twitter"]
wiki_data = combined_data["wiki"]
details_data = combined_data["details"]

# Debug info about data structure
print("Data structure loaded:")
print(f"Reddit data: {type(reddit_data)}, {len(reddit_data)} streamers")
print(f"Twitter data: {type(twitter_data)}, {len(twitter_data)} streamers")
if isinstance(wiki_data, dict):
    print(f"Wiki data: dict with {len(wiki_data)} entries")
elif isinstance(wiki_data, list):
    print(f"Wiki data: list with {len(wiki_data)} entries")
print(f"Details data: {type(details_data)}, {len(details_data)} streamers")

# Load CSV data about streamers for additional details (if needed)
csv_path = os.path.join(current_directory, "streamer_details.csv")
streamer_csv = pd.read_csv(csv_path).fillna("")  # Safely fill NaNs with empty strings

# Convert CSV rows into a dict keyed by uppercase Name
streamer_csv_data = {}
for _, row in streamer_csv.iterrows():
    name_upper = str(row["Name"]).upper().strip()
    streamer_csv_data[name_upper] = dict(row)

# Create inverted index for boolean search (temporary solution for prototype)
def create_index():
    index = defaultdict(list)
    # Index Reddit posts (titles)
    for streamer, data in reddit_data.items():
        for i, post in enumerate(data):
            title = post["Title"].lower()
            words = re.findall(r"\w+", title)
            for word in words:
                index[word].append(("reddit", streamer, i))
    # Index Twitter posts (full text)
    for streamer, tweets in twitter_data.items():
        for i, tweet in enumerate(tweets):
            tweet_text = tweet.lower()
            words = re.findall(r"\w+", tweet_text)
            for word in words:
                index[word].append(("twitter", streamer, i))
    # Index Wiki summaries
    if isinstance(wiki_data, dict):
        for streamer, entry in wiki_data.items():
            if isinstance(entry, dict) and "wikipedia_summary" in entry:
                summary = entry["wikipedia_summary"].lower()
                words = re.findall(r"\w+", summary)
                for word in words:
                    index[word].append(("wiki", streamer, 0))
    elif isinstance(wiki_data, list):
        for i, entry in enumerate(wiki_data):
            if isinstance(entry, dict) and "wikipedia_summary" in entry and "streamer" in entry:
                summary = entry["wikipedia_summary"].lower()
                words = re.findall(r"\w+", summary)
                for word in words:
                    index[word].append(("wiki", entry["streamer"], i))
    # Index Details descriptions (convert to string first)
    for streamer, details in details_data.items():
        description = str(details.get("Description", "")).lower()
        words = re.findall(r"\w+", description)
        for word in words:
            index[word].append(("details", streamer, 0))
    return index

# Simple search function for prototype
def search(query, index):
    query = query.strip().lower()
    terms = re.findall(r"\w+", query)
    if not terms:
        return []
    
    doc_matches = defaultdict(int)
    doc_info = {}
    for term in terms:
        if term in index:
            for doc in index[term]:
                source, streamer, idx = doc
                doc_id = f"{source}:{streamer}:{idx}"
                doc_matches[doc_id] += 1
                if doc_id not in doc_info:
                    if source == "reddit":
                        doc_info[doc_id] = {
                            "source": "reddit",
                            "streamer": streamer,
                            "data": reddit_data[streamer][idx],
                            "text": reddit_data[streamer][idx]["Title"],
                            "score": reddit_data[streamer][idx]["Score"],
                            "idx": idx
                        }
                    elif source == "twitter":
                        doc_info[doc_id] = {
                            "source": "twitter",
                            "streamer": streamer,
                            "data": twitter_data[streamer][idx],
                            "text": twitter_data[streamer][idx],
                            "score": 1,
                            "idx": idx
                        }
                    elif source == "wiki":
                        wiki_entry = None
                        wiki_text = ""
                        if isinstance(wiki_data, dict) and streamer in wiki_data:
                            wiki_entry = wiki_data[streamer]
                            if isinstance(wiki_entry, dict) and "wikipedia_summary" in wiki_entry:
                                wiki_text = wiki_entry["wikipedia_summary"]
                        elif isinstance(wiki_data, list) and 0 <= idx < len(wiki_data):
                            wiki_entry = wiki_data[idx]
                            if isinstance(wiki_entry, dict) and "wikipedia_summary" in wiki_entry:
                                wiki_text = wiki_entry["wikipedia_summary"]
                        doc_info[doc_id] = {
                            "source": "wiki",
                            "streamer": streamer,
                            "data": wiki_entry,
                            "text": wiki_text,
                            "score": 2,
                            "idx": idx
                        }
                    elif source == "details":
                        detail_entry = details_data.get(streamer, {})
                        description = detail_entry.get("Description", "")
                        doc_info[doc_id] = {
                            "source": "details",
                            "streamer": streamer,
                            "data": detail_entry,
                            "text": description,
                            "score": 3,  # Boost for details.
                            "idx": idx
                        }
    results = []
    for doc_id, match_count in doc_matches.items():
        doc = doc_info[doc_id]
        doc["term_matches"] = match_count
        results.append(doc)
    return results

def score_results(results, query):
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored_results = []
    for doc in results:
        score = 0
        text = doc["text"].lower()
        term_match_score = doc.get("term_matches", 0) * 15
        score += term_match_score
        for term in query_terms:
            count = text.count(term.lower())
            score += count * 5
        if doc["source"] == "reddit":
            reddit_score_boost = min(doc["score"] / 500, 20)
            score += reddit_score_boost
        elif doc["source"] == "wiki":
            score += 15
        elif doc["source"] == "details":
            score += 10  # Boost for details.
        if " ".join(query_terms) in text:
            score += 50
        formatted_doc = {
            "source": doc["source"],
            "name": doc["streamer"],
            "doc": doc["text"][:150] + "..." if len(doc["text"]) > 150 else doc["text"],
            "sim_score": round(score, 2)
        }
        if doc["source"] == "reddit":
            formatted_doc["reddit_score"] = doc["score"]
            formatted_doc["id"] = doc["data"]["ID"]
        scored_results.append((formatted_doc, score))
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored_results]

def get_twitch_info(streamer_name):
    """Get Twitch page info for a streamer if available."""
    variants = [
        streamer_name,
        streamer_name.upper(),
        streamer_name.lower(),
        streamer_name.title(),
        streamer_name.replace(" ", "")
    ]
    for name_variant in variants:
        if name_variant in streamer_csv_data:
            data = streamer_csv_data[name_variant]
            if "Twitch URL" in data and data["Twitch URL"].strip():
                return data
            else:
                default_url = f"https://www.twitch.tv/{streamer_name}"
                data["url"] = default_url
                return data
    print(f"No Twitch data found for streamer: {streamer_name}")
    return None

def get_streamer_image_path(streamer_name):
    """Get the image path for a streamer if available."""
    image_paths = [
        f"images/streamer_images/{streamer_name.upper()}.jpg",
        f"images/streamer_images/{streamer_name}.jpg",
        f"images/streamer_images/{streamer_name.lower()}.jpg",
        f"images/streamer_images/{streamer_name.replace(' ', '')}.jpg"
    ]
    return image_paths[0]

def get_csv_streamer_info(streamer_name):
    """Look up extra CSV info for the streamer from streamer_details.csv."""
    name_upper = streamer_name.upper().strip()
    return streamer_csv_data.get(name_upper, None)

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

search_index = create_index()

@app.route("/")
def home():
    return render_template("base.html", title="Streamer Search")

@app.route("/search")
def search_streamer():
    query = request.args.get("name", "")
    if not query:
        return jsonify([])
    
    raw_results = search(query, search_index)
    scored_results = score_results(raw_results, query)[:10]
    
    # Group results by streamer
    streamer_results = {}
    for result in scored_results:
        streamer = result["name"]
        if streamer not in streamer_results:
            streamer_results[streamer] = {
                "documents": [],
                "twitch_info": get_twitch_info(streamer)
            }
        streamer_results[streamer]["documents"].append(result)
    
    final_results = []
    for streamer, data in streamer_results.items():
        csv_info = get_csv_streamer_info(streamer)
        final_results.append({
            "name": streamer,
            "documents": data["documents"],
            "twitch_info": data["twitch_info"],
            "image_path": get_streamer_image_path(streamer),
            "csv_data": csv_info
        })
    
    final_results.sort(
        key=lambda x: max([doc["sim_score"] for doc in x["documents"]]) if x["documents"] else 0, 
        reverse=True
    )
    
    return jsonify(final_results)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
