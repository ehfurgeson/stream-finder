import json
import nltk

# Uncomment these lines if you haven't already downloaded these corpora.
# nltk.download('words')
# nltk.download('wordnet')

# Build a set of English words from the NLTK words corpus.
english_words = set(word.lower() for word in nltk.corpus.words.words())

# Custom exceptions for words that might not be in the corpus.
custom_valid_words = {"fortnite", "loft"}  # add more words as needed

def is_valid_word(word):
    """
    Check if a word is valid by checking the NLTK corpus or the custom exception list.
    """
    word_lower = word.lower()
    return word_lower in english_words or word_lower in custom_valid_words

def union_valid_and_set_keys(my_set, twitter_json_file='twitter.json'):
    """
    Load twitter.json and return the union of:
        - Keys that are in twitter.json and in my_set.
        - Keys that are in twitter.json and are valid words.
    
    Args:
        my_set (set): A set of keywords (in all-caps) to consider.
        twitter_json_file (str): Path to the twitter.json file.
    
    Returns:
        set or None: The union as described, or None if the file couldn't be read.
    """
    try:
        with open(twitter_json_file, 'r') as f:
            twitter_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    twitter_keys = set(twitter_data.keys())

    # twitter.json ∩ my_set
    keys_in_my_set = my_set.intersection(twitter_keys)
    
    # twitter.json ∩ valid_words
    valid_twitter_keys = {key for key in twitter_keys if is_valid_word(key)}
    
    # Union of both sets
    return keys_in_my_set.union(valid_twitter_keys)

if __name__ == "__main__":
    # Example: my_set contains these keywords.
    my_set = {"FORTNITE", "HELLO", "WORLD"}
    result = union_valid_and_set_keys(my_set)
    print(result)
