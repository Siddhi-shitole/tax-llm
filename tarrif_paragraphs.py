import pandas as pd
import re
import numpy as np

df = pd.read_csv('new_hierarchical_commodities.csv')

df = df.drop(['Commodity Description'], axis=1)

#df['Commodity Number'] = df['Commodity Number'].fillna(method='ffill')


# Fill empty Commodity Number at start if needed
#if pd.isna(df['Commodity Number'].iloc[0]):
 #   df['Commodity Number'].iloc[0] = df['Commodity Number'].bfill().iloc[0]

# Clean column names
df.columns = [col.strip() for col in df.columns]

# Ensure TopLeft_Y is numeric
df["BottomRight_Y"] = pd.to_numeric(df["BottomRight_Y"], errors="coerce")

def fill_tariff_paragraphs_from_commodity(df):
    df = df.copy()
    commodity_indices = df[df["Hierarchical Description"].notna()].index

    for i, idx in enumerate(commodity_indices):
        comm_y = df.loc[idx, "BottomRight_Y"]
        comm_page = df.loc[idx, "Page"]

        # --- Step 1: Check for nearby existing Tariff Paragraph ---
        nearby_mask = (
            (df["Tariff Paragraph"].notna()) &
            (df["Page"] == comm_page) &
            (df["BottomRight_Y"].between(comm_y, comm_y +5)
        ))
        if df[nearby_mask].shape[0] > 0:
            nearest_tariff_para = df[nearby_mask].iloc[0]["Tariff Paragraph"]
            df.loc[idx, "Tariff Paragraph"] = nearest_tariff_para
            continue  # Skip to next since we already filled it

        # --- Step 2: Follow original logic ---
        tariff_rows = df.loc[idx + 1 :]
        tariff_rows = tariff_rows[tariff_rows["Tariff Paragraph"].notna()]

        if not tariff_rows.empty:
            tariff_idx = tariff_rows.index[0]
            tariff_page = df.loc[tariff_idx, "Page"]
            tariff_y = df.loc[tariff_idx, "BottomRight_Y"]
            distance = abs(tariff_y - comm_y)

            y_min = comm_y
            y_max = df.loc[tariff_idx, "BottomRight_Y"] + distance + 10
            mask = (
                (df["BottomRight_Y"] >= y_min) &
                (df["BottomRight_Y"] <= y_max) &
                (df["Tariff Paragraph"].isna()) &
                (df["Page"] == tariff_page)
            )
            df.loc[mask, "Tariff Paragraph"] = df.loc[tariff_idx, "Tariff Paragraph"]

    return df


# Apply the logic
df_filled = fill_tariff_paragraphs_from_commodity(df)

df_filled['Commodity Number'] = df_filled['Commodity Number'].fillna(method='ffill')


# Fill empty Commodity Number at start if needed
if pd.isna(df_filled['Commodity Number'].iloc[0]):
    df_filled['Commodity Number'].iloc[0] = df_filled['Commodity Number'].bfill().iloc[0]

df_filled = df_filled.dropna(subset=['Hierarchical Description'])

print(df_filled.head(50))
# Save the result if needed
df_filled.to_csv("final_tables.csv", index=False)

