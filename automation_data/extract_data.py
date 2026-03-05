import pandas as pd
import numpy as np
import os
import re

def clean_text(text):
    if pd.isna(text) or str(text).lower() == 'nan':
        return ""
    return str(text).strip()

def get_professional_title(column_name):
    column_name = column_name.lower()
    if 'cxo' in column_name:
        return "Leadership Team"
    if 'hr' in column_name:
        return "Human Resources Team"
    return "Team"

def process_excel(input_file, output_file):
    # Ensure dependencies are available
    try:
        df = pd.read_excel(input_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    records = []
    
    # Pairs of (Name Column, Email Column)
    email_pairs = [
        ('CXO Name', 'Email Id'),
        ('CXO Name.1', 'Email Id.1'),
        ('HR Name', 'Email id')
    ]
    
    # Check if columns exist in the dataframe
    available_columns = df.columns.tolist()
    
    for idx, row in df.iterrows():
        company_name = clean_text(row.get('Company Name', ''))
        city = clean_text(row.get('Location', ''))
        context = clean_text(row.get('Context', ''))
        
        # company_type is fixed as "Corporate"
        company_type = "Corporate"
        
        for name_col, email_col in email_pairs:
            if name_col in available_columns and email_col in available_columns:
                name = clean_text(row.get(name_col, ''))
                emails = clean_text(row.get(email_col, ''))
                
                if not emails:
                    continue
                
                # Split emails by comma or semicolon
                email_list = [e.strip() for e in re.split(r'[,;]', emails) if e.strip()]
                
                # Professional fallback for missing name
                if not name:
                    name = get_professional_title(name_col)
                
                for email in email_list:
                    records.append({
                        'email': email,
                        'CXO Name': name,
                        'company_name': company_name,
                        'company_type': company_type,
                        'city': city,
                        'context': context
                    })
    
    if not records:
        print("No records found to extract.")
        return

    output_df = pd.DataFrame(records)
    # Reorder columns as requested: email, CXO Name, company_name, company_type, city, context
    cols = ['email', 'CXO Name', 'company_name', 'company_type', 'city', 'context']
    output_df = output_df[cols]
    
    output_df.to_csv(output_file, index=False)
    print(f"Extraction complete! {len(records)} records saved to {output_file}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(current_dir, 'Company Data - Raw.xlsx')
    output_path = os.path.join(current_dir, 'extracted_data.csv')
    
    # If the script is run from a different location, adjust paths
    if not os.path.exists(input_path):
        # Specific path from user metadata
        input_path = r'c:\Users\Admin\Documents\HARSH\GDG\OSW\Automation\OSW_EMAIL_AUTOMATION\automation_data\Company Data - Raw.xlsx'
        output_path = r'c:\Users\Admin\Documents\HARSH\GDG\OSW\Automation\OSW_EMAIL_AUTOMATION\automation_data\extracted_data.csv'

    process_excel(input_path, output_path)
