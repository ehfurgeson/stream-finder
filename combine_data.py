import json
import os

def combine_data():
    # Get the current directory (root folder)
    root_directory = os.path.dirname(os.path.abspath(__file__))
    
    # Specify paths to input files in the root directory
    reddit_json_path = os.path.join(root_directory, "reddit.json")
    twitter_json_path = os.path.join(root_directory, "twitter.json")
    wiki_json_path = os.path.join(root_directory, "wikipage2.json")
    random_json_path = os.path.join(root_directory, "filtered_twitchpage.json")
    
    # Specify path to output file in the backend folder
    backend_directory = os.path.join(root_directory, "backend")
    init_json_path = os.path.join(backend_directory, "init.json")
    
    # Load the json data
    with open(reddit_json_path, "r") as file:
        reddit_data = json.load(file)

    with open(twitter_json_path, "r") as file:
        twitter_data = json.load(file)

    with open(wiki_json_path, "r") as file:
        wiki_data = json.load(file)

    with open(random_json_path, "r") as file:  # Load random.json
        random_data = json.load(file)
    
    # Create combined data structure
    combined_data = {
        "reddit": reddit_data,
        "twitter": twitter_data,
        "wiki": wiki_data,
        "random": random_data  # Add to combined data
    }
    
    # Write to init.json
    with open(init_json_path, "w") as file:
        json.dump(combined_data, file, indent = 2)
    
    print(f"Successfully combined data into {init_json_path}")

if __name__ == "__main__":
    combine_data()
