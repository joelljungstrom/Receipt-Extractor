import pdfplumber
import re
import pandas as pd
import numpy as np
import hashlib
import glob
import os
import csv
from datetime import datetime


# function for generating artificial article number
def generate_article_number(article_name, unit_price):
    article_number_components = f'{article_name}_{unit_price}'
    hashed = hashlib.md5(article_number_components.encode()).hexdigest()
    article_number = hashed[:13]
    article_number = article_number.zfill(13)

    return article_number

# function for extracting purchase id
def extract_receipt_code(text):
    all_numbers = re.findall(r'\d+', text)
    purchase_id = all_numbers[-1] if all_numbers else None
    return purchase_id

# function for identifying and creating purchase timestamp
def extract_date_and_time(text):    
    date_match = re.search(r'(?<=Datum\s)(\d{4}-\d{2}-\d{2})', text)
    time_match = re.search(r'(?<=Tid\s)(\d{2}:\d{2})', text)
    
    date = date_match.group(0) if date_match else None
    time = time_match.group(0) if time_match else None
    
    full_timestamp = f"{date} {time}"
    return datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M")

# function for saving output as a CSV
def save_df_to_csv(df):
    output_path = '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Output/article_purchase_data.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')

# function for extracting line items from PDF
def extract_line_items_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ''
        for page in pdf.pages:
            page_text = page.extract_text() or ''
            all_text += page_text + '\n'

    start_word = "Summa(SEK)"
    if re.search(r"(?i)\bAvstämning\b", all_text):
        end_word = "Avstämning"
    elif re.search(r"(?i)\bFelaktig\b", all_text):
        end_word = "Felaktig"
    else:
        end_word = "Betalat"

    purchase_timestamp = extract_date_and_time(all_text)
    purchase_id = extract_receipt_code(all_text)

    pattern = re.compile(r'{}(.*?){}'.format(re.escape(start_word), re.escape(end_word)), re.DOTALL)
    matches = pattern.findall(all_text)
    
    line_items = []
    for match in matches:
        lines = match.strip().split("\n")
        for line in lines:
            columns = None

            # Identify regular line items where article numbers are present (a minimum 7-digit long string)
            if re.search(r'\d{4,}', line):
                columns = re.split(r'(\d{4,})', line)
                columns = [col.strip() for col in columns if col.strip()]
                
                if len(columns) > 1:
                    remaining_columns = columns[2].split()
                    columns = columns[:2] + remaining_columns
            
            # Identify anomalies, where there is a line-item for pant/deposit
            elif re.search(r"(?i)\bPant\b", line):
                match = re.search(r"(?i)\bPant\b\s+(\d+,\d{2})\s+(\d+)\s+(\d+,\d{2})", line)
                if match:
                    unit_price = match.group(1)
                    amount = match.group(2)
                    article_total = match.group(3)
                    columns = [
                        "Pant", # article_name
                        None,  # article_number
                        unit_price,  # unit_price
                        amount,  # amount
                        "st",  # unit_measurement
                        article_total  # article_total
                    ]
                else: 
                    columns = [line.strip(), None]
            
            # Identify anomalies, where there is a line-item for a discount
            else:
                match = re.search(r"-\d+,\d+", line)
                if match:
                    columns = [
                        line[:match.start(0)].strip(),  # article_name
                        None, # article_number
                        line[match.start(0):match.end(0)].strip(), # unit_price
                        "1,00",  # amount
                        "st",  # unit_measurement
                        line[match.start(0):match.end(0)].strip() # article_total
                    ]

            if columns is None:
                continue

            if len(columns) > 1:
                if columns[1] is None:
                    article_number = generate_article_number(columns[0], columns[2])
                    columns[1] = article_number

            # append timestamp and purchase id
            columns.append(purchase_timestamp)
            columns.append(purchase_id)

            line_items.append(columns)
            
    expected_cols = 8
    for idx, cols in enumerate(line_items):
        if len(cols) != expected_cols:
            print(f"[ERROR] PDF: {pdf_path}, line item {idx} has {len(cols)} columns: {cols}")

    line_items_df = pd.DataFrame(line_items, columns=[
            "article_name", 
            "article_number", 
            "unit_price", 
            "amount", 
            "unit_measurement", 
            "article_total", 
            "purchase_timestamp",
            "purchase_id"
        ]
    )

    def safe_to_float(val, col_name):
        try:
            if isinstance(val, str):
                return float(val.replace(',', '.'))
            return val
        except Exception:
            print(f"[ERROR] PDF: {pdf_path}, conversion failed in column '{col_name}' with value: {val!r}")
            raise

    line_items_df['article_name'] = line_items_df['article_name'].astype(str)
    line_items_df['article_number'] = line_items_df['article_number'].fillna(np.nan).astype(str)
    line_items_df['unit_price'] = line_items_df['unit_price'].apply(lambda x: safe_to_float(x, 'unit_price'))
    line_items_df['amount'] = line_items_df['amount'].apply(lambda x: safe_to_float(x, 'amount'))
    line_items_df['unit_measurement'] = line_items_df['unit_measurement'].astype(str)
    line_items_df['article_total'] = line_items_df['article_total'].apply(lambda x: safe_to_float(x, 'article_total'))

    return line_items_df

# function for extracting line items from multiple PDFs
def purchase_history(folder_path):
    pdf_paths = glob.glob(os.path.join(folder_path, "*.pdf"))

    all_line_items = []
    
    for pdf_path in pdf_paths:
        line_items_df = extract_line_items_from_pdf(pdf_path)
        all_line_items.append(line_items_df)

    combined_line_items = pd.concat(all_line_items, ignore_index=True)
    
    #pdf_names = [os.path.basename(path) for path in pdf_paths]
    #repeated_pdf_names = [pdf_name for pdf_name in pdf_names for _ in range(len(all_line_items[0]))]

    #combined_line_items['source_name'] = repeated_pdf_names[:len(combined_line_items)]
    save_df_to_csv(combined_line_items)
    return combined_line_items

# function for storing unique articles
def unique_articles(line_items_df, article_name, article_number):
    article_pairs = line_items_df[[article_name, article_number]].drop_duplicates()
    return article_pairs

# paths for pdfs
pdf_path = '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Receipts/tmp/Maxi ICA Stormarknad Lindhagen 2025-04-26.pdf'
folder_path = '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Receipts'

# run 1 file
line_items_df = extract_line_items_from_pdf(pdf_path)
#print(line_items_df)

# run multiple files
combined_data = purchase_history(folder_path)
print(combined_data)
