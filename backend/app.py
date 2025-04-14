"""
Hybrid Search combining Boolean search and BERT semantic search
This implementation combines the strengths of both approaches:
1. Boolean search for precise keyword matching
2. BERT semantic search for understanding meaning
"""

import os, json, pickle, sys
import numpy as np
import re
from sentence_transformers import SentenceTransformer
import faiss
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import torch
from collections import defaultdict

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ CONFIG
# -----------------------------------------------------------------------------
MODEL_NAME   = "sentence-transformers/all-mpnet-base-v2"   # 768-dim embeddings
EMBED_PATH   = "embeddings.npy"
META_PATH    = "metadata.pkl"
BUILD_INDEX  = False                # set True for initial build, then flip to False
TOP_K        = 50                   # Number of results to retrieve for BERT
EMBED_DIM    = 768                  # Embedding dimension
SEMANTIC_WEIGHT = 0.5               # Weight for semantic results (0.0-1.0)
BOOLEAN_WEIGHT = 0.5                # Weight for boolean results (0.0-1.0)

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ DATA LOADING
# -----------------------------------------------------------------------------
BACK = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BACK, "init.json"), "r", encoding="utf-8") as f:
    init = json.load(f)
reddit_data  = init["reddit"]
twitter_data = init["twitter"]
wiki_data    = init["wiki"]
details_data = init["details"]

# CSV with extra streamer details
CSV_PATH = os.path.join(BACK, "streamer_details.csv")
streamer_csv = pd.read_csv(CSV_PATH).fillna("")
streamer_csv_data = {str(r["Name"]).upper().strip(): dict(r) for _, r in streamer_csv.iterrows()}

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ BOOLEAN SEARCH FUNCTIONS
# -----------------------------------------------------------------------------
def create_boolean_index():
    """Create an inverted index for boolean search"""
    print("Creating boolean index...")
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
    
    # Index Details descriptions
    for streamer, details in details_data.items():
        description = str(details.get("Description", "")).lower()
        words = re.findall(r"\w+", description)
        for word in words:
            index[word].append(("details", streamer, 0))
    
    print(f"Boolean index created with {len(index)} unique words")
    return index

def boolean_search(query, index):
    """Perform boolean search using the inverted index"""
    query = query.strip().lower()
    terms = re.findall(r"\w+", query)
    
    if not terms:
        return []
    
    # For each term, find matching documents
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
                            "idx": idx,
                            "term_matches": 0
                        }
                    elif source == "twitter":
                        doc_info[doc_id] = {
                            "source": "twitter",
                            "streamer": streamer,
                            "data": twitter_data[streamer][idx],
                            "text": twitter_data[streamer][idx],
                            "score": 1,
                            "idx": idx,
                            "term_matches": 0
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
                            "idx": idx,
                            "term_matches": 0
                        }
                    elif source == "details":
                        detail_entry = details_data.get(streamer, {})
                        description = detail_entry.get("Description", "")
                        doc_info[doc_id] = {
                            "source": "details",
                            "streamer": streamer,
                            "data": detail_entry,
                            "text": description,
                            "score": 3,
                            "idx": idx,
                            "term_matches": 0
                        }
    
    # Record term match counts
    for doc_id, match_count in doc_matches.items():
        doc_info[doc_id]["term_matches"] = match_count
    
    # Convert to list
    results = []
    for doc_id, doc in doc_info.items():
        results.append(doc)
    
    return results

def score_boolean_results(results, query):
    """Score boolean search results based on term matches and source"""
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored_results = []
    
    for doc in results:
        score = 0
        text = doc["text"].lower()
        
        # Term matches score
        term_match_score = doc.get("term_matches", 0) * 15
        score += term_match_score
        
        # Term frequency score
        for term in query_terms:
            count = text.count(term.lower())
            score += count * 5
        
        # Source-based weighting
        if doc["source"] == "reddit":
            reddit_score_boost = min(doc["score"] / 500, 20)
            score += reddit_score_boost
        elif doc["source"] == "wiki":
            score += 15
        elif doc["source"] == "details":
            score += 10
        
        # Exact phrase match bonus
        if " ".join(query_terms) in text:
            score += 50
        
        # Format the document for output
        formatted_doc = {
            "source": doc["source"],
            "name": doc["streamer"],
            "doc": doc["text"][:150] + "..." if len(doc["text"]) > 150 else doc["text"],
            "boolean_score": round(score, 2),
            "term_matches": doc.get("term_matches", 0)
        }
        
        # Add Reddit-specific fields if applicable
        if doc["source"] == "reddit" and isinstance(doc["data"], dict):
            formatted_doc["reddit_score"] = doc["score"]
            formatted_doc["id"] = doc["data"].get("ID", "")
            
        scored_results.append((formatted_doc, score))
    
    # Sort by score
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored_results]

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ BERT SEMANTIC SEARCH FUNCTIONS
# -----------------------------------------------------------------------------
def gather_documents():
    """Gather documents for BERT embeddings"""
    docs = []
    
    # Reddit posts
    for streamer, posts in reddit_data.items():
        for idx, post in enumerate(posts):
            docs.append({
                "text": post["Title"], 
                "source": "reddit", 
                "streamer": streamer, 
                "idx": idx, 
                "data": post,
                "score": post.get("Score", 1)
            })
    
    # Twitter posts
    for streamer, tweets in twitter_data.items():
        for idx, tweet in enumerate(tweets):
            docs.append({
                "text": tweet, 
                "source": "twitter", 
                "streamer": streamer, 
                "idx": idx, 
                "data": tweet,
                "score": 1
            })
    
    # Wiki entries
    if isinstance(wiki_data, dict):
        for streamer, entry in wiki_data.items():
            if isinstance(entry, dict) and "wikipedia_summary" in entry:
                # Add streamer name to wiki text to improve matching
                wiki_text = f"{entry['wikipedia_summary']} {streamer}"
                docs.append({
                    "text": wiki_text, 
                    "source": "wiki", 
                    "streamer": streamer, 
                    "idx": 0, 
                    "data": entry,
                    "score": 2
                })
    else:
        for idx, entry in enumerate(wiki_data):
            if isinstance(entry, dict) and "wikipedia_summary" in entry:
                streamer_name = entry.get("streamer", "")
                # Add streamer name to wiki text to improve matching
                wiki_text = f"{entry['wikipedia_summary']} {streamer_name}"
                docs.append({
                    "text": wiki_text, 
                    "source": "wiki", 
                    "streamer": streamer_name, 
                    "idx": idx, 
                    "data": entry,
                    "score": 2
                })
    
    # Details descriptions
    for streamer, det in details_data.items():
        # Add streamer name to details text to improve matching
        description = f"{str(det.get('Description', ''))} {streamer}"
        docs.append({
            "text": description, 
            "source": "details", 
            "streamer": streamer, 
            "idx": 0, 
            "data": det,
            "score": 3
        })
    
    print(f"Gathered {len(docs)} documents for BERT indexing")
    return docs

def score_semantic_results(results, query):
    """Score semantic search results"""
    query_terms = set(re.findall(r"\w+", query.lower()))
    scored_results = []
    
    for doc in results:
        # Start with semantic similarity score (already 0-100)
        score = doc["sim_score"]
        text = doc["text"].lower()
        
        # Apply source-based weighting
        if doc["source"] == "wiki":
            score += 15  # Wiki boost
        elif doc["source"] == "details":
            score += 10  # Details boost
        elif doc["source"] == "reddit":
            # Small boost based on Reddit score
            reddit_score_boost = min(doc["score"] / 500, 20)
            score += reddit_score_boost
        
        # Exact phrase match bonus
        if query.lower() in text:
            score += 30
            
        # Format document for output
        formatted_doc = {
            "source": doc["source"],
            "name": doc["streamer"],
            "doc": doc["text"][:150] + "..." if len(doc["text"]) > 150 else doc["text"],
            "semantic_score": round(score, 2)
        }
        
        # Add Reddit-specific fields if applicable
        if doc["source"] == "reddit" and isinstance(doc["data"], dict):
            formatted_doc["reddit_score"] = doc["score"]
            formatted_doc["id"] = doc["data"].get("ID", "")
            
        scored_results.append((formatted_doc, score))
    
    # Sort by score
    scored_results.sort(key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in scored_results]

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ HYBRID SEARCH COMBINING BOOLEAN AND SEMANTIC SEARCH
# -----------------------------------------------------------------------------
def combine_search_results(boolean_results, semantic_results, boolean_weight=0.5, semantic_weight=0.5):
    """Combine boolean and semantic search results"""
    # Create a dictionary to store combined results
    combined_results = {}
    
    # Process boolean results
    for doc in boolean_results:
        streamer = doc["name"]
        if streamer not in combined_results:
            combined_results[streamer] = {
                "name": streamer,
                "documents": [],
                "boolean_score": 0,
                "semantic_score": 0,
                "combined_score": 0
            }
        
        # Store the document
        combined_results[streamer]["documents"].append(doc)
        
        # Update boolean score (use highest score among documents)
        if "boolean_score" in doc:
            boolean_score = doc["boolean_score"]
            if boolean_score > combined_results[streamer]["boolean_score"]:
                combined_results[streamer]["boolean_score"] = boolean_score
    
    # Process semantic results
    for doc in semantic_results:
        streamer = doc["name"]
        if streamer not in combined_results:
            combined_results[streamer] = {
                "name": streamer,
                "documents": [],
                "boolean_score": 0,
                "semantic_score": 0,
                "combined_score": 0
            }
        
        # Avoid duplicate documents
        if not any(d.get("source") == doc["source"] and d.get("doc") == doc["doc"] for d in combined_results[streamer]["documents"]):
            combined_results[streamer]["documents"].append(doc)
        
        # Update semantic score (use highest score among documents)
        if "semantic_score" in doc:
            semantic_score = doc["semantic_score"]
            if semantic_score > combined_results[streamer]["semantic_score"]:
                combined_results[streamer]["semantic_score"] = semantic_score
    
    # Calculate combined score
    for streamer, data in combined_results.items():
        boolean_score = data["boolean_score"]
        semantic_score = data["semantic_score"]
        
        # Normalize scores (both are already on similar 0-100 scales)
        combined_score = (boolean_score * boolean_weight) + (semantic_score * semantic_weight)
        data["combined_score"] = round(combined_score, 2)
    
    # Convert to list and sort by combined score
    result_list = list(combined_results.values())
    result_list.sort(key=lambda x: x["combined_score"], reverse=True)
    
    return result_list

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ HELPER FUNCTIONS
# -----------------------------------------------------------------------------
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

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ INITIALIZE SEARCH INDEXES
# -----------------------------------------------------------------------------
# Boolean search index
boolean_index = create_boolean_index()

# BERT semantic search
device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Using device: {device.upper()}")
model = SentenceTransformer(MODEL_NAME, device=device)

# Verify embedding dimension
embedding_test = model.encode(["Test sentence"], convert_to_numpy=True)
actual_dim = embedding_test.shape[1]
if actual_dim != EMBED_DIM:
    print(f"[WARNING] Expected embedding dimension {EMBED_DIM}, but model produces {actual_dim} dimensions")
    EMBED_DIM = actual_dim  # Update to actual dimension

if BUILD_INDEX or not (os.path.exists(EMBED_PATH) and os.path.exists(META_PATH)):
    DOCS = gather_documents()
    print(f"[BERT] Encoding {len(DOCS)} documents...")
    EMBEDDINGS = model.encode(
        [d["text"] for d in DOCS],
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    ).astype("float32")
    
    # Verify embedding dimension
    if EMBEDDINGS.shape[1] != EMBED_DIM:
        print(f"[WARNING] Embedding dimension mismatch: expected {EMBED_DIM}, got {EMBEDDINGS.shape[1]}")
    
    print(f"[INFO] Created embeddings with shape {EMBEDDINGS.shape}")
    
    np.save(EMBED_PATH, EMBEDDINGS)
    with open(META_PATH, "wb") as f:
        pickle.dump(DOCS, f)
    print("Embeddings + metadata saved. Exiting after build.")
    sys.exit(0)
else:
    DOCS = pickle.load(open(META_PATH, "rb"))
    EMBEDDINGS = np.load(EMBED_PATH)
    
    # Verify loaded embedding dimension
    if EMBEDDINGS.shape[1] != EMBED_DIM:
        print(f"[WARNING] Loaded embeddings dimension {EMBEDDINGS.shape[1]} differs from configured {EMBED_DIM}")
        EMBED_DIM = EMBEDDINGS.shape[1]  # Update to actual dimension

# Initialize FAISS index for similarity search
index = faiss.IndexFlatIP(EMBED_DIM)  # Use explicit dimension
index.add(EMBEDDINGS)
print(f"[FAISS] {index.ntotal} vectors indexed → dim {EMBED_DIM}")

# ───────────────────────────────────────────────────────────────────────────────
# ⬇️ FLASK SERVER
# -----------------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return render_template("base.html", title="Streamer Search")

@app.route("/search")
def search_streamer():
    query = request.args.get("name", "").strip()
    if not query:
        return jsonify([])
    
    print(f"[SEARCH] Query: '{query}'")
    
    # 1. Perform Boolean search
    print("[SEARCH] Performing Boolean search...")
    boolean_raw_results = boolean_search(query, boolean_index)
    boolean_results = score_boolean_results(boolean_raw_results, query)
    
    # 2. Perform BERT semantic search
    print("[SEARCH] Performing BERT semantic search...")
    q_emb = model.encode(query, convert_to_numpy=True, normalize_embeddings=True)
    D, I = index.search(q_emb.reshape(1, -1), TOP_K)
    
    # Prepare semantic results
    semantic_raw_results = []
    for score, idx in zip(D[0], I[0]):
        if idx == -1: 
            continue
        meta = DOCS[idx]
        
        # Convert similarity score to 0-100 scale
        sim_score = float(score) * 100
        
        # Format document for output
        formatted_doc = {
            "source": meta["source"],
            "streamer": meta["streamer"],
            "text": meta["text"],
            "score": meta.get("score", 1),
            "data": meta.get("data", {}),
            "sim_score": round(sim_score, 2)
        }
        
        # Add Reddit-specific fields if applicable
        if meta["source"] == "reddit" and isinstance(meta["data"], dict):
            formatted_doc["reddit_score"] = meta["score"]
            formatted_doc["id"] = meta["data"].get("ID", "")
            
        semantic_raw_results.append(formatted_doc)
    
    semantic_results = score_semantic_results(semantic_raw_results, query)
    
    # 3. Combine results
    print("[SEARCH] Combining search results...")
    combined_results = combine_search_results(
        boolean_results, 
        semantic_results, 
        boolean_weight=BOOLEAN_WEIGHT, 
        semantic_weight=SEMANTIC_WEIGHT
    )
    
    # 4. Add streamer info to results
    print("[SEARCH] Adding streamer info...")
    final_results = []
    
    for result in combined_results[:10]:  # Take top 10
        streamer = result["name"]
        
        # Clean the documents for display
        cleaned_documents = []
        for doc in result["documents"]:
            # Clean up text for display (remove streamer name if appended and truncate)
            display_text = doc.get("doc", "")
            
            # Create clean document for output
            display_doc = {
                "source": doc.get("source", ""),
                "name": streamer,
                "doc": display_text,
                "sim_score": doc.get("semantic_score", doc.get("boolean_score", 0))
            }
            
            # Add Reddit-specific fields if present
            if "reddit_score" in doc:
                display_doc["reddit_score"] = doc["reddit_score"]
            if "id" in doc:
                display_doc["id"] = doc["id"]
                
            cleaned_documents.append(display_doc)
        
        # Add streamer info
        final_results.append({
            "name": streamer,
            "documents": cleaned_documents,
            "twitch_info": get_twitch_info(streamer),
            "image_path": get_streamer_image_path(streamer),
            "csv_data": get_csv_streamer_info(streamer)
        })
    
    # 5. Sort by combined score
    final_results.sort(
        key=lambda x: next((doc["sim_score"] for doc in x["documents"] if doc["sim_score"] > 0), 0),
        reverse=True
    )
    
    return jsonify(final_results)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001) #checking