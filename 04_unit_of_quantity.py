import pandas as pd
import re

CLEAN_CSV = r'output/cleaned_classified_words.csv'
FINAL_CSV = r'output/final-table.csv'

# Pattern to identify units of quantity - enhanced with context awareness
unit_patterns = [
    r'\b(lb|lbs|pound|pounds)\b',
    r'\b(kg|kilogram|kilograms)\b', 
    r'\b(ton|tons|tonne|tonnes)\b',
    r'\b(gal|gallon|gallons)\b',
    r'\b(qt|quart|quarts)\b',
    r'\b(pt|pint|pints)\b',
    r'\b(oz|ounce|ounces)\b',
    r'\b(cu\s?ft|cubic\s+feet?)\b',
    r'\b(sq\s?ft|square\s+feet?)\b',
    r'\b(linear\s+feet?|lin\s?ft)\b',
    r'\b(yard|yards|yd)\b',
    r'\b(meter|metres?|m)\b',
    r'\b(each|ea)\b',
    r'\b(dozen|doz)\b',
    r'\b(gross)\b',
    r'\b(case|cases)\b',
    r'\b(box|boxes)\b',
    r'\b(bag|bags)\b',
    r'\b(bale|bales)\b',
    r'\b(bundle|bundles)\b',
    r'\b(head|hd)\b',  # For livestock
    r'\b(no|number)\b',  # Sometimes "No" indicates quantity units
]

# Enhanced patterns for context-aware unit detection
context_patterns = {
    'livestock': {
        'patterns': [r'cattle', r'sheep', r'lamb', r'swine', r'pig', r'horse', r'animal'],
        'units': ['No', 'Head']
    },
    'weight_based': {
        'patterns': [r'meat', r'beef', r'pork', r'carcass', r'dressed', r'fresh', r'frozen'],
        'units': ['Lb', 'Cwt']
    },
    'volume_based': {
        'patterns': [r'liquid', r'oil', r'milk', r'beverage'],
        'units': ['Gal', 'Qt']
    },
    'count_based': {
        'patterns': [r'eggs', r'birds', r'chickens', r'turkeys', r'ducks', r'poultry'],
        'units': ['No', 'Doz']
    }
}

def extract_unit_from_text(text, context_description=''):
    """
    Extract unit of quantity from description text using patterns and context.
    Enhanced to better distinguish between "No" (number) and weight units.
    """
    if pd.isna(text) or not text:
        return ''
    
    text_lower = str(text).lower()
    context_lower = str(context_description).lower() if context_description else ''
    combined_text = f"{text_lower} {context_lower}".strip()
    
    # First, check context-specific patterns
    for context_type, context_info in context_patterns.items():
        for pattern in context_info['patterns']:
            if re.search(pattern, combined_text, re.IGNORECASE):
                # Found context match, prefer context-appropriate units
                for unit in context_info['units']:
                    unit_pattern = rf'\b{re.escape(unit.lower())}\b'
                    if re.search(unit_pattern, combined_text, re.IGNORECASE):
                        return unit
                # If no specific unit found but context matches, return default for context
                if context_type == 'livestock':
                    return 'No'
                elif context_type == 'weight_based':
                    return 'Lb'
    
    # Fall back to general pattern matching
    for pattern in unit_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            matched_text = match.group(0)
            # Normalize common units
            if matched_text in ['lb', 'lbs', 'pound', 'pounds']:
                return 'Lb'
            elif matched_text in ['no', 'number']:
                return 'No'
            elif matched_text in ['each', 'ea']:
                return 'No'
            elif matched_text in ['head', 'hd']:
                return 'Head'
            else:
                return matched_text.capitalize()
    
    return ''

def infer_unit_from_commodity_type(commodity_num, description):
    """
    Infer unit based on commodity number patterns and description context.
    """
    if not commodity_num or not description:
        return ''
    
    description_lower = str(description).lower()
    
    # Livestock commodities typically use "No" (number)
    if any(word in description_lower for word in ['cattle', 'sheep', 'lamb', 'swine', 'pig', 'horse', 'live']):
        return 'No'
    
    # Meat products typically use "Lb" (pounds)
    if any(word in description_lower for word in ['meat', 'beef', 'pork', 'carcass', 'dressed', 'fresh', 'frozen']):
        return 'Lb'
    
    # Default fallback based on commodity number ranges (if patterns exist)
    try:
        num = int(commodity_num.replace(' ', ''))
        if 100 <= num <= 199:  # Livestock range (example)
            return 'No'
        elif 200 <= num <= 299:  # Meat products range (example)
            return 'Lb'
    except (ValueError, AttributeError):
        pass
    
    return ''

def add_units():
    # Note: This script now works with the new 6-column structure:
    # SCHEDULE A COMMODITY NUMBER, COMMODITY DESCRIPTION AND ECONOMIC CLASS, 
    # UNIT OF QUANTITY, RATE OF DUTY 1930, RATE OF DUTY TRADE AGREEMENT, TARIFF PARAGRAPH
    
    df_clean = pd.read_csv(CLEAN_CSV)
    df_final = pd.read_csv(FINAL_CSV)
    
    # Create a mapping of commodity numbers to units based on coordinate proximity and context
    commodity_units = {}
    commodity_descriptions = {}
    
    # First pass: collect all descriptions for each commodity
    for _, row in df_clean.iterrows():
        if pd.notna(row['Commodity Number']) and str(row['Commodity Number']).strip():
            commodity_num = str(row['Commodity Number']).strip()
            if pd.notna(row['Commodity Description']) and str(row['Commodity Description']).strip():
                description = str(row['Commodity Description']).strip()
                if commodity_num not in commodity_descriptions:
                    commodity_descriptions[commodity_num] = []
                commodity_descriptions[commodity_num].append(description)
    
    # Second pass: extract units with enhanced context awareness
    for _, row in df_clean.iterrows():
        if pd.notna(row['Commodity Description']) and str(row['Commodity Description']).strip():
            description = str(row['Commodity Description']).strip()
            
            # Try to find nearby commodity number using Y-coordinate proximity
            y_coord = row['TopLeft_Y']
            tolerance = 30  # Y-coordinate tolerance
            
            # Find commodity numbers within Y-coordinate range
            nearby_commodities = df_clean[
                (df_clean['Commodity Number'].notna()) & 
                (df_clean['Commodity Number'] != '') &
                (abs(df_clean['TopLeft_Y'] - y_coord) <= tolerance)
            ]
            
            if len(nearby_commodities) > 0:
                commodity_num = str(nearby_commodities.iloc[0]['Commodity Number']).strip()
                if commodity_num and commodity_num != 'nan':
                    # Get all context for this commodity
                    context_descriptions = commodity_descriptions.get(commodity_num, [])
                    full_context = ' '.join(context_descriptions)
                    
                    # Extract unit with context awareness
                    unit = extract_unit_from_text(description, full_context)
                    
                    # If no unit found from text, try to infer from commodity type
                    if not unit:
                        unit = infer_unit_from_commodity_type(commodity_num, full_context)
                    
                    if unit:
                        commodity_units[commodity_num] = unit
    
    # Third pass: Handle commodities without explicit units using inference
    for commodity_num, descriptions in commodity_descriptions.items():
        if commodity_num not in commodity_units:
            full_description = ' '.join(descriptions)
            inferred_unit = infer_unit_from_commodity_type(commodity_num, full_description)
            if inferred_unit:
                commodity_units[commodity_num] = inferred_unit
            else:
                # Default to "No" for most commodities if no clear pattern
                commodity_units[commodity_num] = 'No'
    
    # Update final table with extracted units (now using new column structure)
    updated_count = 0
    for idx, row in df_final.iterrows():
        commodity_num_formatted = str(row['SCHEDULE A COMMODITY NUMBER']).strip()
        
        # Convert formatted number to match source data format (like we did in description script)
        clean_num = commodity_num_formatted.replace(' ', '')
        if len(clean_num) == 7:
            without_leading_zero = clean_num[1:]
            without_trailing_zeros = without_leading_zero.rstrip('0')
            
            if len(without_trailing_zeros) == 2:
                converted_num = without_trailing_zeros + '000'
            elif len(without_trailing_zeros) == 3:
                converted_num = without_trailing_zeros + '00'
            elif len(without_trailing_zeros) == 4:
                converted_num = without_trailing_zeros + '0'
            else:
                converted_num = without_trailing_zeros
                
            mapping_key = f"{converted_num}.0"
        else:
            mapping_key = clean_num
            
        # Check if we have a unit for this commodity
        if mapping_key in commodity_units:
            df_final.at[idx, 'UNIT OF QUANTITY'] = commodity_units[mapping_key]
            updated_count += 1
        else:
            # Enhanced fallback logic based on description
            description = str(row.get('COMMODITY DESCRIPTION AND ECONOMIC CLASS', '')).lower()
            
            # If description contains explicit units, use them
            if 'lb' in description or 'pound' in description:
                df_final.at[idx, 'UNIT OF QUANTITY'] = 'Lb'
            elif any(word in description for word in ['cattle', 'sheep', 'lamb', 'live', 'head', 'each']):
                df_final.at[idx, 'UNIT OF QUANTITY'] = 'No'
            elif any(word in description for word in ['meat', 'beef', 'pork', 'mutton', 'veal', 'fresh', 'frozen', 'offal']):
                df_final.at[idx, 'UNIT OF QUANTITY'] = 'Lb'
            else:
                # Default to "No" if no clear pattern
                df_final.at[idx, 'UNIT OF QUANTITY'] = 'No'
            updated_count += 1
    
    # Ensure all expected columns exist with proper headers
    expected_columns = [
        'SCHEDULE A COMMODITY NUMBER',
        'COMMODITY DESCRIPTION AND ECONOMIC CLASS', 
        'UNIT OF QUANTITY',
        'RATE OF DUTY 1930',
        'RATE OF DUTY TRADE AGREEMENT',
        'TARIFF PARAGRAPH'
    ]
    
    # Add missing columns if they don't exist
    for col in expected_columns:
        if col not in df_final.columns:
            df_final[col] = ''
    
    # Reorder columns to match new structure
    df_final = df_final[expected_columns]
    
    df_final.to_csv(FINAL_CSV, index=False)
    print(f"Updated {updated_count} units of quantity in {FINAL_CSV}")
    print(f"Found units: {list(set(commodity_units.values()))}")
    print(f"File now uses new 6-column structure: {expected_columns}")
    
    # Print some examples for verification
    print(f"\nSample unit assignments:")
    for commodity_num, unit in list(commodity_units.items())[:10]:
        context = ' '.join(commodity_descriptions.get(commodity_num, []))[:50]
        print(f"  {commodity_num}: {unit} (context: {context}...)")

if __name__ == "__main__":
    add_units()
