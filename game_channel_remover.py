import json
import os

def filter_esports_from_json_files(esports_channels, json_files = ["reddit.json", "twitter.json", "wikipage2.json", "random.json"]):
    """
    Remove esports channels from specified JSON files.
    
    Parameters:
    -----------
    esports_channels : list
        List of esports channel names to remove
    json_files : list
        List of JSON files to process
    """
    # Convert all channel names to uppercase for case-insensitive comparison
    # This matches the format in your JSON examples
    esports_channels_upper = [channel.upper() for channel in esports_channels]
    
    # Process each JSON file
    for json_file in json_files:
        try:
            # Check if file exists
            if not os.path.exists(json_file):
                print(f"Warning: File {json_file} not found. Skipping.")
                continue
                
            print(f"\nProcessing {json_file}...")
            
            # Load the JSON data
            with open(json_file, "r", encoding = "utf-8") as f:
                data = json.load(f)
            
            # Count original entries
            original_count = len(data)
            print(f"Original entries: {original_count}")
            
            # Create a list of channels to remove
            channels_to_remove = [channel for channel in data.keys() if channel in esports_channels_upper]
            
            # Create a new dict without the esports channels
            filtered_data = {k: v for k, v in data.items() if k not in esports_channels_upper}
            
            # Count filtered entries
            filtered_count = len(filtered_data)
            removed_count = original_count - filtered_count
            
            # Save the filtered data
            if json_file.startswith("random"):
                output_file = "filtered_twitchpage.json"
            else:
                output_file = f"filtered_{json_file}"
            with open(output_file, "w", encoding = "utf-8") as f:
                json.dump(filtered_data, f, ensure_ascii = False, indent = 4)
            
            # Print summary
            print(f"Removed {removed_count} esports channels")
            print(f"Remaining entries: {filtered_count}")
            print(f"Saved filtered data to {output_file}")
            
            # Print the names of removed channels
            if removed_count > 0:
                print("\nRemoved channels from this file:")
                for channel in channels_to_remove:
                    print(f"- {channel}")
                    
        except Exception as e:
            print(f"Error processing {json_file}: {e}")

if __name__ == "__main__":
    # List of esports channels to remove
    esports_channels = [
        "ECHO_ESPORTS",
        "ESLCS",
        "PGL",
        "ESL_DOTA2",
        "TEAMLIQUID",
        "PGL_DOTA2",
        "VALORANT",
        "RAINBOW6",
        "AUSSIEANTICS",
        "LEC",
        "LCK",
        "OW_ESPORTS",
        "RIOT GAMES",
        "ESLCSB",
        "ROCKETLEAGUE",
        "LTANORTH",
        "PGL_CS2",
        "WORLDOFTANKS",
        "EASPORTSFC",
        "MAGIC",
        "CCT_CS",
        "CAPCOMFIGHTERS",
        "BRAWLHALLA",
        "PGL_DOTA2EN2",
        "CHESS",
        "EAMADDENNFL",
        "TWITCHRIVALS",
        "BRAWLSTARS",
        "CCT_CS2",
        "NBA2KLEAGUE",
        "ESL_DOTA2EMBER",
        "SMITEGAME",
        "PUBG_BATTLEGROUNDS",
        "ESL_DOTA2STORM",
        "TEKKEN",
        "CCT_DOTA",
        "PLAYHEARTHSTONE",
        "ESL_DOTA2EARTH"
    ]
    
    # Run the filtering process
    filter_esports_from_json_files(esports_channels)