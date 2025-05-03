import pdfplumber
import re
import pandas as pd
import csv 
from datetime import datetime 

def extract_date_and_time(text):
    date_match = re.search(r'(?<=Datum\s)(\d{4}-\d{2}-\d{2})', text)
    time_match = re.search(r'(?<=Tid\s)(\d{2}:\d{2})', text)
    
    date = date_match.group(0) if date_match else None
    time = time_match.group(0) if time_match else None
    
    full_timestamp = f"{date} {time}"
    full_timestamp = datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M")

    return full_timestamp

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

def extract_store_name(receipt):
    lines = [line.strip() for line in receipt.splitlines() if line.strip()]
    store_name = lines[1] if len(lines) > 1 else None
    
    return store_name

def extract_receipt_code(text):
    all_numbers = re.findall(r'\d+', text)
    purchase_id = all_numbers[-1] if all_numbers else None
    return purchase_id

def extract_line_items_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ''
        
        # Extract text and tables from each page
        for page in pdf.pages:
            all_text += page.extract_text()
        
        # extract purchase total
        receipt_total = re.search(r'(\d+,\d{2})', all_text)
        purchase_total = receipt_total.group(1) if receipt_total else 0.0

        # extract purchase discount
        disc = re.search(r'(?i)Erhållen rabatt\s+(-?\d+,\d{2})', all_text)
        discount = disc.group(1) if disc else 0.0

        # extract rounding
        receipt_rounding = re.search(r'(?i)Avrundning\s+(-?\d+,\d{2})', all_text)
        rounding = receipt_rounding.group(1) if receipt_rounding else 0.0
        
        purchase_timestamp = extract_date_and_time(all_text)
        purchase_id = extract_receipt_code(all_text)
        store_name = extract_store_name(all_text)
        tax, net, gross = extract_taxes(all_text)
    
    return all_text, purchase_timestamp, purchase_id, store_name, tax, net, gross, purchase_total, discount, rounding

def save_text_to_csv(text, output_csv):
    lines = text.split('\n')

    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for line in lines:
            writer.writerow([line])
            

# Example usage
text = extract_line_items_from_pdf('/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Receipts/Maxi ICA Stormarknad Lindhagen 2025-04-02-2.pdf')
#save_text_to_csv(text, '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Output/text_data.csv')
print(text)