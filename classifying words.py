import pandas as pd
import re

# Load the CSV
df = pd.read_csv('ocr_word_coords.csv')

# Drop rows from 0 to 13 (to start at Cattle:) and reset index
df = df.iloc[14:].reset_index(drop=True)

# Filter out rows where TopLeft_X is between 1305 and 2150
df = df[~((df['TopLeft_X'] > 1305) & (df['TopLeft_X'] < 2150))].reset_index(drop=True)

# Classification function
def classify_word(word):
    word = str(word).strip()
    
    # Match commodity number: starts with 00 + 2 digits + space + 3 digits
    match_commodity = re.match(r'^(00\d{2} \d{3})', word)
    if match_commodity:
        return match_commodity.group(1), None, None
    
    # Match tariff paragraph: starts with 3 digits (not 00X), and is not a commodity number
    elif re.fullmatch(r'.\d{3}.*', word):
        return None, None, word
    # Else, it's a description
    else:
        return None, word, None

# Apply classification to the Word column
df[['Commodity Number', 'Commodity Description', 'Tariff Paragraph']] = df['Word'].apply(
    lambda w: pd.Series(classify_word(w))
)

# Save to new CSV
df = df.drop(['Word'], axis=1 )


# Step 1: Handle cases with 3 digits and short string (≤3 letters), move to Tariff Paragraph
def move_to_tariff_paragraph(desc):
    if pd.isna(desc):
        return None, None

    cleaned = re.sub(r'[^\w\s]', '', desc)  # Remove special characters
    match = re.fullmatch(r'(\d{3})([A-Za-z]{1,3})?', cleaned)

    if match:
        return None, match.group(0)  # Set desc to None, move cleaned text to Tariff Paragraph
    else:
        return desc, None  # Leave as-is

# Apply transformation
df[['Commodity Description', 'Moved_To_Tariff']] = df['Commodity Description'].apply(
    lambda x: pd.Series(move_to_tariff_paragraph(x))
)

# Merge 'Moved_To_Tariff' into 'Tariff Paragraph' (only if original is null)
df['Tariff Paragraph'] = df['Tariff Paragraph'].combine_first(df['Moved_To_Tariff'])

# Drop temporary helper column
df.drop(columns=['Moved_To_Tariff'], inplace=True)

# Step 2: Drop rows where Commodity Description is only digits or negative numbers
def is_digits_or_negative(val):
    if pd.isna(val):
        return False
    return re.fullmatch(r'-?\d+', str(val)) is not None  # Match negative or positive digits

df = df[~df['Commodity Description'].apply(is_digits_or_negative)].reset_index(drop=True)

# Optional: Save cleaned output
df.to_csv("cleaned_classified_words.csv", index=False)

# Show preview
print(df[['Commodity Number', 'Commodity Description', 'Tariff Paragraph']].head())
