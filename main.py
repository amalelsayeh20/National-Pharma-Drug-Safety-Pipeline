# main.py
import logging
from etl.data_loader import load_local_drug_database
from etl.cdss_engine import clinical_safety_validator

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info("🚀 Starting Enterprise CDSS Pipeline...")
    
    # 1. Load local database using the correct function
    df_local = load_local_drug_database()
    
    # 2. Define test patient profile
    dynamic_patient = {
        "patient_id": "P-505",
        "chronic_diseases": ["Asthma", "Diabetes"]
    }
    
    # 3. Run validation test passing df_local
    clinical_safety_validator("Ibuprofen", dynamic_patient, df_local)