import pdfplumber
import re
import pandas as pd
import numpy as np
import hashlib
import glob
import os
import csv
from datetime import datetime

# check if string can be converted to number and return failed instance if ther is one
def safe_to_float(val, col_name):
        try:
            if isinstance(val, str):
                return float(val.replace(',', '.'))
            return val
        except Exception:
            print(f"[ERROR] PDF: {pdf_path}, conversion failed in column '{col_name}' with value: {val!r}")
            raise

# function for generating artificial article number
def generate_article_number(article_name, unit_price):
    article_number_components = f'{article_name}_{unit_price}'
    hashed = hashlib.md5(article_number_components.encode()).hexdigest()
    article_number = hashed[:13]
    article_number = article_number.zfill(13)

    return article_number

# function for extracting purchase id
def extract_receipt_code(receipt):
    all_numbers = re.findall(r'\d+', receipt)
    purchase_id = all_numbers[-1] if all_numbers else None
    
    return purchase_id

# function for identifying and creating purchase timestamp
def extract_date_and_time(receipt):    
    date_match = re.search(r'(?<=Datum\s)(\d{4}-\d{2}-\d{2})', receipt)
    time_match = re.search(r'(?<=Tid\s)(\d{2}:\d{2})', receipt)
    
    date = date_match.group(0) if date_match else None
    time = time_match.group(0) if time_match else None
    
    full_timestamp = f"{date} {time}"
    purchase_timestamp = datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M")
    
    return purchase_timestamp

# function for extracting store name
def extract_store_name(receipt):
    lines = [line.strip() for line in receipt.splitlines() if line.strip()]
    store_name = lines[1] if len(lines) > 1 else None
    
    return store_name

# function for extracting taxes
def extract_taxes(receipt):
    lines = [line.strip() for line in receipt.splitlines() if line.strip()]
    taxes = re.search(r"Moms\s*%\s+Moms\s+Netto\s+Brutto", receipt)
    if not taxes:
        tax = 0.0
        net = 0.0
        gross = 0.0
    
    else: 
        block = receipt[taxes.end():]
        lines = re.findall(r"^(\d+,\d{2})\s+(\d+,\d{2})\s+(\d+,\d{2})\s+(\d+,\d{2})",
                        block, flags=re.MULTILINE)

        tax = sum(float(t.replace(',', '.')) for _, t, _, _ in lines)
        net = sum(float(n.replace(',', '.')) for _, _, n, _ in lines)
        gross = sum(float(g.replace(',', '.')) for _, _, _, g in lines)
    
    return tax, net, gross

# function for saving output as a CSV
def save_df_to_csv(df, file_name):
    output_path = f'/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Output/{file_name}.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')

# function for extracting text from PDF
def extract_text_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        receipt = ''
        for page in pdf.pages:
            page_text = page.extract_text() or ''
            receipt += page_text + '\n'
    
    return receipt

# function for extracting line items from PDF
def extract_line_items(pdf_path):
    
    receipt = extract_text_from_pdf(pdf_path)

    start_word = "Summa(SEK)"
    if re.search(r"(?i)\bAvstämning\b", receipt):
        end_word = "Avstämning"
    elif re.search(r"(?i)\bFelaktig\b", receipt):
        end_word = "Felaktig"
    else:
        end_word = "Betalat"

    purchase_timestamp = extract_date_and_time(receipt)
    purchase_id = extract_receipt_code(receipt)
    store_name = extract_store_name(receipt)

    pattern = re.compile(r'{}(.*?){}'.format(re.escape(start_word), re.escape(end_word)), re.DOTALL)
    matches = pattern.findall(receipt)
    
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
                        None,  # article_id
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
                        None, # article_id
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
            columns.append(store_name)

            line_items.append(columns)
            
    expected_cols = 9
    for idx, cols in enumerate(line_items):
        if len(cols) != expected_cols:
            print(f"[ERROR] PDF: {pdf_path}, line item {idx} has {len(cols)} columns: {cols}")

    line_items_df = pd.DataFrame(line_items, columns=[
            "article_name", 
            "article_id", 
            "unit_price", 
            "amount", 
            "unit_measurement", 
            "total", 
            "purchase_timestamp",
            "purchase_id",
            "store_name"
        ]
    )

    for col in ["unit_price", "amount", "total"]:
        line_items_df[col] = line_items_df[col].apply(lambda x: safe_to_float(x, col))
    for col in ["article_name", "article_id", "unit_measurement"]:
        line_items_df[col] = line_items_df[col].astype(str)

    return line_items_df

# function for extracting shop instances from PDF
def extract_purchase_information(pdf_path):
    
    receipt = extract_text_from_pdf(pdf_path)

    purchase_timestamp = extract_date_and_time(receipt)
    purchase_id = extract_receipt_code(receipt)
    store_name = extract_store_name(receipt)
    tax, net, gross = extract_taxes(receipt)

    start_word = "Betalat"
    end_word = "Betalningsinformation"

    pattern = re.compile(r'{}(.*?){}'.format(re.escape(start_word), re.escape(end_word)), re.DOTALL)
    matches = pattern.findall(receipt)
    
    purchase_instances = []
    for match in matches:
        # extract purchase total
        receipt_total = re.search(r'(\d+,\d{2})', match)
        purchase_total = receipt_total.group(1) if receipt_total else "0,00"

        # extract purchase discount
        disc = re.search(r'(?i)Erhållen rabatt\s+(-?\d+,\d{2})', match)
        discount = disc.group(1) if disc else "0,00"

        # extract rounding
        receipt_rounding = re.search(r'(?i)Avrundning\s+(-?\d+,\d{2})', match)
        rounding = receipt_rounding.group(1) if receipt_rounding else "0,00"

        purchase_instances.append([
            purchase_id,
            purchase_timestamp,
            store_name,
            purchase_total,
            tax,
            net,
            gross,
            discount,
            rounding,
            "SEK"
        ])

    purchase_instances_df = pd.DataFrame(
        purchase_instances,
        columns=[
            "id",
            "timestamp",
            "store_name",
            "total",
            "tax",
            "net",
            "gross",
            "discount",
            "rounding",
            "currency"
        ]
    )

    for col in ["total", "tax", "net", "gross", "discount", "rounding"]:
        purchase_instances_df[col] = purchase_instances_df[col].apply(lambda x: safe_to_float(x, col))

    return purchase_instances_df

# function for extracting line items from multiple PDFs
def purchase_history(folder_path):
    pdf_paths = glob.glob(os.path.join(folder_path, "*.pdf"))

    line_items = []
    purchase_instances = []
    
    for pdf_path in pdf_paths:
        line_items_df = extract_line_items(pdf_path)
        line_items.append(line_items_df)

        purchase_instances_df = extract_purchase_information(pdf_path)
        purchase_instances.append(purchase_instances_df)

    combined_line_items = pd.concat(line_items, ignore_index=True)
    combined_purchase_instances = pd.concat(purchase_instances, ignore_index=True)

    save_df_to_csv(combined_line_items, "line_items")
    save_df_to_csv(combined_purchase_instances, "purchases")

    return combined_line_items, combined_purchase_instances

# function for storing unique articles
def unique_articles(line_items_df, article_name, article_number):
    article_pairs = line_items_df[[article_name, article_number]].drop_duplicates()
    return article_pairs

# paths for pdfs
pdf_path = '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Receipts/Maxi ICA Stormarknad Lindhagen 2025-04-26.pdf'
folder_path = '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Receipts'

# run 1 file
line_items_df = extract_line_items(pdf_path)
#print(line_items_df)

# run multiple files
combined_data = purchase_history(folder_path)
print(combined_data)
