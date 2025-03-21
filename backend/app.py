import json
import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from helpers.MySQLDatabaseHandler import MySQLDatabaseHandler
import pandas as pd
from collections import defaultdict
import re

# ROOT_PATH for linking with all your files. 
# Feel free to use a config.py or settings.py with a global export variable
os.environ["ROOT_PATH"] = os.path.abspath(os.path.join("..", os.curdir))

# Get the directory of the current script
current_directory = os.path.dirname(os.path.abspath(__file__))

# specify the path to the json file relative to the current script
json_path = os.path.join(current_directory, "init.json")

# load the json data
with open(json_path, "r") as file:
    combined_data = json.load(file)

# extract the individual datasets
reddit_data = combined_data["reddit"]
twitter_data = combined_data["twitter"]
wiki_data = combined_data["wiki"]

# create inverted index for boolean search (temporary solution for prototype)
def create_index():
    index = defaultdict(list)
    for streamer, data in reddit_data.items():
        for i, post in enumerate(data):
            title = post["Title"].lower()
            words = re.findall(r"\w+", title)
            for word in words:
                index[word].append(("reddit", streamer, i))
    for streamer, tweets in twitter_data.items():
        for i, tweet in enumerate(tweets):
            tweet_text = tweet.lower()
            words = re.findall(r"\w+", tweet_text)
            for word in words:
                index[word].append(("twitter", streamer, i))
    for i, entry in enumerate(wiki_data):
        if (entry["wikipedia_summary"] != "Search error, unable to fetch summary."
            and entry["wikipedia_summary"] != "Failed to retrieve Wikipedia page."):
            summary = entry["wikipedia_summary"].lower()
            words = re.findall(r"\w+", summary)
            for word in words:
                index[word].append(("wiki", entry["streamer"], i))
    return index

# simple search function for prototype
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
                            "score": 1,  # Default score for tweets
                            "idx": idx
                        }
                    elif source == "wiki":
                        doc_info[doc_id] = {
                            "source": "wiki",
                            "streamer": streamer,
                            "data": wiki_data[idx],
                            "text": wiki_data[idx]["wikipedia_summary"],
                            "score": 2,  # Default score for wiki entries
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
        
        if " ".join(query_terms) in text.lower():
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
    
    scored_results.sort(key = lambda x: x[1], reverse = True)
    
    return [doc for doc, _ in scored_results]

app = Flask(__name__)
CORS(app)

search_index = create_index()

@app.route("/")
def home():
    return render_template("base.html", title = "Streamer Search")

@app.route("/search")
def search_streamer():
    query = request.args.get("name", "")
    if not query:
        return jsonify([])
    
    raw_results = search(query, search_index)
    
    scored_results = score_results(raw_results, query)[:10]
    
    # Return the results directly since we already formatted them in score_results
    return jsonify(scored_results)

if __name__ == "__main__":
    app.run(debug = True, host = "0.0.0.0", port = 5000)