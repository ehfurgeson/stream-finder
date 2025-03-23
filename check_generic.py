import json
import csv
import nltk

# Uncomment these lines if you haven't already downloaded these corpora.
# nltk.download('words')
# nltk.download('wordnet')

# Build a set of English words from the NLTK words corpus.
english_words = set(word.lower() for word in nltk.corpus.words.words())

# Custom exceptions for words that might not be in the corpus.
custom_valid_words = {"fortnite", "loft", "gothamchess"}  # add more words as needed

def is_valid_word(word):
    """
    Check if a word is valid by checking the NLTK corpus or the custom exception list.
    """
    word_lower = word.lower()
    return word_lower in english_words or word_lower in custom_valid_words

def union_valid_and_set_keys(my_set, twitch_csv_file='top_1000_twitch.csv'):
    """
    Load top_1000_twitch.csv and return the union of:
        - Keys that are in top_1000_twitch.csv and in my_set.
        - Keys that are in top_1000_twitch.csv and are valid words.
    
    Args:
        my_set (set): A set of keywords (in all-caps) to consider.
        twitch_csv_file (str): Path to the top_1000_twitch.csv file.
    
    Returns:
        set or None: The union as described, or None if the file couldn't be read.
    """
    try:
        with open(twitch_csv_file, 'r') as f:
            reader = csv.reader(f)
            # Extract the second column (streamer names) from each row
            twitch_keys = set(row[1].lower() for row in reader)
    except (FileNotFoundError, csv.Error, IndexError):
        return None

    # twitch.csv ∩ my_set
    keys_in_my_set = my_set.intersection(twitch_keys)
    
    # twitch.csv ∩ valid_words
    valid_twitch_keys = {key for key in twitch_keys if is_valid_word(key)}
    
    # Union of both sets
    return keys_in_my_set.union(valid_twitch_keys)

if __name__ == "__main__":
    # Example: my_set contains these keywords.
    my_set = {"FORTNITE", "HELLO", "WORLD", "MR_MAMMAL", "DENIMS", "GOTHAMCHESS"}
    result = union_valid_and_set_keys(my_set)
    print(result)
