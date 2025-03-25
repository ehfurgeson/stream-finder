import json
import os
import pandas as pd

def combine_data():
    # Get the project root directory (where this file is located)
    root_directory = os.path.dirname(os.path.abspath(__file__))
    
    # Paths to JSON files in the root directory
    reddit_json_path = os.path.join(root_directory, "reddit.json")
    twitter_json_path = os.path.join(root_directory, "twitter.json")
    wiki_json_path = os.path.join(root_directory, "wikipage2.json")
    
    # streamer_details.csv is in the backend folder
    details_csv_path = os.path.join(root_directory, "backend", "streamer_details.csv")
    
    # Output file inside the backend folder
    backend_directory = os.path.join(root_directory, "backend")
    init_json_path = os.path.join(backend_directory, "init.json")
    
    # Load the JSON data with explicit UTF-8 encoding
    with open(reddit_json_path, "r", encoding="utf-8") as file:
        reddit_data = json.load(file)

    with open(twitter_json_path, "r", encoding="utf-8") as file:
        twitter_data = json.load(file)

    with open(wiki_json_path, "r", encoding="utf-8") as file:
        wiki_data = json.load(file)
    
    # Load CSV data for streamer details and convert it to a dictionary keyed by Name
    details_df = pd.read_csv(details_csv_path)
    details_data = {}
    for _, row in details_df.iterrows():
        name = str(row["Name"]).strip()
        details_data[name] = row.to_dict()
    
    # Create combined data structure
    combined_data = {
        "reddit": reddit_data,
        "twitter": twitter_data,
        "wiki": wiki_data,
        "details": details_data
    }
    
    # Write to init.json with UTF-8 encoding
    with open(init_json_path, "w", encoding="utf-8") as file:
        json.dump(combined_data, file, indent=2, ensure_ascii=False)
    
    print(f"Successfully combined data into {init_json_path}")

if __name__ == "__main__":
    combine_data()
