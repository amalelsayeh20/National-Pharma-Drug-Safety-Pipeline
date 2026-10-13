# src/data_loader.py
import os
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def load_local_drug_database():
    """Download or load the local Egyptian drug database CSV file."""
    base_dir = os.getcwd()
    if 'src' in base_dir or 'etl' in base_dir:
        base_dir = os.path.dirname(base_dir)

    data_dir = os.path.join(base_dir, 'data', 'raw')
    os.makedirs(data_dir, exist_ok=True)
    
    local_file_path = os.path.join(data_dir, 'egyptian drugs.csv')
    csv_url = "https://raw.githubusercontent.com/karem505/egyptian-drug-database/main/data/egyptian-drugs.csv"

    if not os.path.exists(local_file_path):
        logger.info("Loading the CSV file from the URL and saving it to the local data directory...")
        import requests
        response = requests.get(csv_url, timeout=30)
        response.raise_for_status()
        
        with open(local_file_path, 'wb') as f:
            f.write(response.content)
        logger.info("The CSV file has been downloaded and saved successfully in the data/raw/ directory!")
    else:
        logger.info("The file already exists locally in the data/raw/ directory, reading it directly...")

    df_local = pd.read_csv(local_file_path, encoding='utf-8')
    logger.info(f"Local database loaded successfully with {len(df_local):,} records.")
    return df_local

def get_local_drug_info(drug_name, df_local):
    """Search for the drug in both English and Arabic commercial names."""
    drug_name = drug_name.strip().lower()
    match = df_local[
        df_local['commercial_name_en'].str.lower().str.contains(drug_name, na=False) |
        df_local['commercial_name_ar'].str.contains(drug_name, na=False)
    ]
    
    if not match.empty:
        row = match.iloc[0]
        return {
            "found_locally": True,
            "commercial_name": row['commercial_name_en'],
            "scientific_name": row.get('scientific_name', 'Unknown'),
            "price": row.get('price_egp', 'N/A'),
            "manufacturer": row.get('manufacturer', 'N/A')
        }
    return {"found_locally": False, "scientific_name": drug_name}