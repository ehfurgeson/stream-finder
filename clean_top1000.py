import pandas as pd

# Define the keywords to remove (in lowercase)
remove_keywords = {
    'august', 'annoying', 'warn', 'method', 'maximum', 'slacked',
    'celerity', 'mingo', 'tray', 'apply', 'bean', 'mukluk', 'mande',
    'effect', 'ray', 'deme', 'soap', 'dinah', 'morgana', 'rain', 'curry',
    'sinder', 'leopard', 'ship', 'meat', 'fortnite', 'warcraft', 'chap', 'scream', 'faith','foolish',
    'patty', 'apex', 'guru', 'stunt', 'name', 'scrap', 'scrapie', 'aspen',
    'knight', 'apathy', 'quantum', 'dizzy', 'formal', 'gale', 'prod', 'bonnie', 'vei', 'twitch'
    }

# Read the CSV file
df = pd.read_csv('top_1000_twitch.csv')

# Filter out rows where the 'Name' (converted to lowercase) is in the removal set.
df_clean = df[~df['Name'].str.lower().isin(remove_keywords)]

# Write the cleaned data back to the original CSV file.
df_clean.to_csv('top_1000_twitch.csv', index=False)

print("File 'top_1000_twitch.csv' has been cleaned and updated.")
