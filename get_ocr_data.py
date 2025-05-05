import os
import pandas as pd
import torch
from PIL import Image
import fitz  # PyMuPDF for PDF processing
from paddleocr import PaddleOCR
from transformers import T5Tokenizer, T5ForConditionalGeneration
import json
import numpy as np
import re

###############################################
# Configuration
###############################################
pdf_path = r'1950 Schedule A (no OCR).pdf'
output_csv_results = r'inference_results.csv'
output_word_coords = r'ocr_word_coords.csv'
start_page = 28
end_page = 28  # Pages with the table

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

###############################################
# OCR Extraction: Raw Text (Unchanged)
###############################################
def extract_ocr_text(pdf_path, start_page, end_page):
    print(f"Extracting text from PDF pages {start_page}-{end_page}...")
    doc = fitz.open(pdf_path)
    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    extracted_lines = []

    for page_number in range(start_page - 1, end_page):
        if page_number >= len(doc):
            print(f"Page {page_number + 1} does not exist. Skipping.")
            continue
        print(f"Processing Page {page_number + 1}...")
        page = doc[page_number]
        pix = page.get_pixmap(dpi=300)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_np = np.array(image)
        results = ocr.ocr(image_np, cls=True)
        for line in results:
            for line_data in line:
                text = line_data[1][0].strip()
                if text:
                    extracted_lines.append(text)

    doc.close()
    print("✅ OCR text extraction completed.")
    return extracted_lines

###############################################
# NEW: OCR Words with Coordinates
###############################################
def extract_ocr_words_with_coords(pdf_path, start_page, end_page, output_csv=output_word_coords):
    print(f"Extracting words with coordinates from PDF pages {start_page}-{end_page}...")
    doc = fitz.open(pdf_path)
    ocr = PaddleOCR(use_angle_cls=True, lang="en")
    extracted_data = []

    for page_number in range(start_page - 1, end_page):
        if page_number >= len(doc):
            print(f"Page {page_number + 1} does not exist. Skipping.")
            continue

        print(f"Processing Page {page_number + 1}...")
        page = doc[page_number]
        pix = page.get_pixmap(dpi=300)
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        image_np = np.array(image)
        results = ocr.ocr(image_np, cls=True)

        for line in results:
            for box, (text, confidence) in line:
                if not text.strip():
                    continue
                top_left = box[0]
                top_right = box[1]
                bottom_right = box[2]
                bottom_left = box[3]
                extracted_data.append({
                    "Word": text,
                    "Confidence": confidence,
                    "TopLeft_X": top_left[0],
                    "TopLeft_Y": top_left[1],
                    "TopRight_X": top_right[0],
                    "TopRight_Y": top_right[1],
                    "BottomLeft_X": bottom_left[0],
                    "BottomLeft_Y": bottom_left[1],
                    "BottomRight_X": bottom_right[0],
                    "BottomRight_Y": bottom_right[1],
                    "Page": page_number + 1
                })

    df = pd.DataFrame(extracted_data)
    df.to_csv(output_csv, index=False)
    print(f"✅ Word-coordinate CSV saved to: {output_csv}")

###############################################
# Regex Patterns
###############################################
commodity_regex = re.compile(r'^\d{4}\s*\d{3,4}(?:\s*\w*)?$')  # e.g. "0010 600", "0010 700 a"
tariff_regex = re.compile(r'^\(?\d{1,4}\)?$')                  # e.g. "701", "(2)"

###############################################
# Unwanted Keywords (case-insensitive)
###############################################
skip_keywords = [
    "GROUP 00", "ANIMALS AND ANIMAL PRODUCTS", "RATE OR DUTY",
    "SCHEDULE A", "UNIT OR", "TARIPE", "ECONOMIC CLASS", "ILIIOR",
    "COMMODIT", "QUANTITY", "PARAGRAPH", "1930 TARIFF ACT", "TRADE AGREEMENT",
    "(EXCEPT AS NOTED)", "BREEDING", "MEAT PRODUCTS"
]

def should_skip_line(line: str) -> bool:
    upper_line = line.upper()
    return any(keyword in upper_line for keyword in skip_keywords)

###############################################
# Build Rows: Minimal Logic + Paragraph Inheritance
###############################################
def build_rows(ocr_lines):
    rows = []
    current_row = {
        "Schedule_A_Commodity_Number": "",
        "Commodity_Description": "",
        "Tariff_Paragraph": ""
    }
    last_paragraph = ""  # Store last encountered paragraph for inheritance

    def finalize_row():
        if (current_row["Schedule_A_Commodity_Number"] or
            current_row["Commodity_Description"] or
            current_row["Tariff_Paragraph"]):
            if not current_row["Tariff_Paragraph"].strip() and last_paragraph:
                current_row["Tariff_Paragraph"] = last_paragraph
            rows.append(current_row.copy())

    for line in ocr_lines:
        line = line.strip()
        if not line or should_skip_line(line):
            continue

        if commodity_regex.match(line):
            finalize_row()
            current_row = {
                "Schedule_A_Commodity_Number": line,
                "Commodity_Description": "",
                "Tariff_Paragraph": ""
            }
            continue

        if tariff_regex.match(line):
            current_row["Tariff_Paragraph"] = line
            last_paragraph = line
            continue

        if current_row["Commodity_Description"]:
            current_row["Commodity_Description"] += " " + line
        else:
            current_row["Commodity_Description"] = line

    finalize_row()
    return rows

def save_3col_results(ocr_lines):
    table_rows = build_rows(ocr_lines)
    df = pd.DataFrame(table_rows, columns=[
        "Schedule_A_Commodity_Number",
        "Commodity_Description",
        "Tariff_Paragraph"
    ])
    df.to_csv(output_csv_results, index=False)
    print(f"✅ 3-column CSV saved to: {output_csv_results}")

###############################################
# Main
###############################################
def main():
    extract_ocr_words_with_coords(pdf_path, start_page, end_page)
    ocr_texts = extract_ocr_text(pdf_path, start_page, end_page)
    save_3col_results(ocr_texts)

if __name__ == "__main__":
    main()
