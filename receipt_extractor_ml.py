import pdfplumber
import re
import pandas as pd
import csv 
from datetime import datetime 

def extract_purchase_details(text):
    date_match = re.search(r'(?<=Datum\s)(\d{4}-\d{2}-\d{2})', text)
    time_match = re.search(r'(?<=Tid\s)(\d{2}:\d{2})', text)
    
    date = date_match.group(0) if date_match else None
    time = time_match.group(0) if time_match else None
    
    full_timestamp = f"{date} {time}"
    full_timestamp = datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M")

    receipt_id = re.search(r'')

    return datetime.strptime(full_timestamp, "%Y-%m-%d %H:%M")

def extract_line_items_from_pdf(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ''
        
        # Extract text and tables from each page
        for page in pdf.pages:
            all_text += page.extract_text()
        
        purchase_timestamp = extract_purchase_details(all_text)
    
    return all_text, purchase_timestamp

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