import pandas as pd
import numpy as np

def process_commodity_descriptions_by_pixels(data):
    # Sort by page and vertical position
    data = data.sort_values(by=['Page', 'TopLeft_Y'])
    
    # Analyze the TopLeft_X values to identify distinct indentation levels
    x_values = sorted(data['TopLeft_X'].unique())
    
    # Create a mapping of each X value to its hierarchy level
    x_level_map = {x: level for level, x in enumerate(x_values)}
    
    # Initialize variables to track hierarchy
    current_texts = [None] * len(x_values)  # Store text at each indentation level
    
    # Create a new column for hierarchical descriptions
    data['Hierarchical Description'] = None
    data['Is Parent'] = False  # Flag to identify parent rows
    
    # Process each row in order
    for idx, row in data.iterrows():
        # Handle potential NaN or non-string values
        description = str(row['Commodity Description'])
        if description == 'nan':
            continue
        description = description.strip()
        if not description:
            continue
        
        x_coord = row['TopLeft_X']
        level = x_level_map[x_coord]
        
        # Update the current text at this level
        current_texts[level] = description
        
        # Clear any deeper levels when we encounter a new parent
        for i in range(level + 1, len(current_texts)):
            current_texts[i] = None
        
        # Mark as parent if description ends with colon
        is_parent = description.endswith(':')
        data.at[idx, 'Is Parent'] = is_parent
        
        # Build the full hierarchical description
        if level == 0 and not is_parent:
            # This is a standalone top-level item
            data.at[idx, 'Hierarchical Description'] = description
        elif not is_parent:
            # This is a child item, combine with its parent(s)
            parent_texts = [text for text in current_texts[:level] if text and text.endswith(':')]
            
            if parent_texts:
                # Has parent(s), combine them
                hierarchical_desc = " ".join(parent_texts) + " " + description
                data.at[idx, 'Hierarchical Description'] = hierarchical_desc
            else:
                # No valid parent, treat as standalone
                data.at[idx, 'Hierarchical Description'] = description
    
    # Remove parent rows - we only keep rows that aren't parents or have standalone descriptions
    result = data[(~data['Is Parent']) | (data['Hierarchical Description'].notna())].copy()
    result = result.drop(columns=['Is Parent'])
    
    return result

# Read the CSV file
data = pd.read_csv("cleaned_classified_words.csv")


# First, preprocess to handle split lines based ONLY on pixel positions
processed_data = data.copy()
skip_indices = set()
combined_rows = {}  # Store mapping of which rows were combined

for i in range(len(data) - 1):
    try:
        # Get current and next line information
        curr_x = data.iloc[i]['TopLeft_X']
        next_x = data.iloc[i+1]['TopLeft_X']
        curr_y = data.iloc[i]['TopLeft_Y']
        next_y = data.iloc[i+1]['TopLeft_Y']
        
        # Convert values to strings and handle NaN values
        curr_desc = str(data.iloc[i]['Commodity Description'])
        if curr_desc == 'nan':
            curr_desc = ''
        curr_desc = curr_desc.strip()
        
        next_desc = str(data.iloc[i+1]['Commodity Description'])
        if next_desc == 'nan':
            next_desc = ''
        next_desc = next_desc.strip()
        
        # Pure pixel-based continuation detection logic
        if curr_desc and next_desc:
            # Calculate Y-proximity (close lines likely to be related)
            y_proximity = next_y - curr_y
            
            # Check if next line appears to be a continuation based ONLY on position
            if (next_x > curr_x) and (y_proximity < 50) and not curr_desc.endswith(':'):
                combined_desc = f"{curr_desc} {next_desc}"
                processed_data.at[i, 'Commodity Description'] = combined_desc
                skip_indices.add(i+1)
                combined_rows[i] = i+1  # Record that row i+1 was combined into row i
    except (IndexError, KeyError):
        pass  # Handle the last row case

# Create a new dataframe without the skipped (combined) rows
result_data = pd.DataFrame([row for i, row in processed_data.iterrows() if i not in skip_indices])

# Process the data based purely on pixel positions
hierarchical_data = process_commodity_descriptions_by_pixels(result_data)

# Save the processed data with hierarchical descriptions
hierarchical_data.to_csv("new_hierarchical_commodities.csv", index=False)

# Also save just the hierarchical descriptions for reference
with open("formatted_commodities.txt", "w") as f:
    for desc in hierarchical_data['Hierarchical Description'].dropna():
        f.write(str(desc) + "\n")

print("Processing complete!")
print(f"Processed data saved to: hierarchical_commodities.csv")
print(f"Formatted descriptions saved to: formatted_commodities.txt")

# Print a sample of the results
print("\nSample of processed hierarchical descriptions:")
for desc in hierarchical_data['Hierarchical Description'].dropna().head(10):
    print(desc)