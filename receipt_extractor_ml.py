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
        
        purchase_timestamp = extract_date_and_time(all_text)
        purchase_id = extract_receipt_code(all_text)
    
    return all_text, purchase_timestamp, purchase_id

def save_text_to_csv(text, output_csv):
    lines = text.split('\n')

    with open(output_csv, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        for line in lines:
            writer.writerow([line])
            

# Example usage
text = extract_line_items_from_pdf('/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Receipts/tmp/Maxi ICA Stormarknad Lindhagen 2025-04-26.pdf')
#save_text_to_csv(text, '/Users/joel.ljungstroem/Documents/Projects/Receipt Extractor/Output/text_data.csv')
print(text)