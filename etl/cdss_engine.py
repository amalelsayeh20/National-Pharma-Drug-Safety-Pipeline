# src/cdss_engine.py
import logging
from etl.data_loader import get_local_drug_info
from etl.API_client import fetch_global_safety_data

logger = logging.getLogger(__name__)

# 4. (Dynamic Clinical Rule Engine)
def clinical_safety_validator(drug_query, patient_profile, df_local):
    print(f" [check drug]: {drug_query} |  [patient profile]: chronic diseases recorded: {patient_profile.get('chronic_diseases', [])}")
  
    # search for the drug in the local Egyptian database
    local_info = get_local_drug_info(drug_query, df_local)
    active_ingredient = local_info['scientific_name']
    
    print(f" [active ingredient]: {active_ingredient}")
    
    # extract global safety data from openFDA for the active ingredient
    safety_data = fetch_global_safety_data(active_ingredient)
    
    # Dynamic Clinical Rule Engine: Check for contraindications based on patient profile
    alerts = []                                                         # ----> just a prototype phase , next we make a database 
    chronic_diseases = patient_profile.get('chronic_diseases', [])
    
    if safety_data['status'] == "Success":
        # Combine warnings, contraindications, and side effects into a single text for easier searching
        full_text = (
            safety_data.get('warnings', '') + " " + 
            safety_data.get('contraindications', '') + " " + 
            safety_data.get('side_effects', '')
        ).lower()
        
        # check each chronic disease against the combined safety text
        for disease in chronic_diseases:
            disease_clean = disease.strip().lower()
            # check if the disease is mentioned in the safety data
            if disease_clean in full_text:
                alerts.append(f"[take care - Contraindication]: the drug has contraindications for: ({disease})!")
        
        # if no alerts were generated, it means the drug is considered safe for the given chronic diseases
        if not alerts:
            alerts.append(" the drug is considered safe for the patient's chronic diseases based on global safety data.")
    else:
        alerts.append(" No global safety data found for this drug in openFDA, please consult a healthcare professional for further guidance.")
        
    # print the alerts and safety summary
    print("\n the alerts satisfied for the patient's chronic diseases:")
    for alert in alerts:
        print(f"   {alert}")
        
    if safety_data['status'] == "Success":
        print(f"\n summary effects(Side Effects) (Global): \n{safety_data['side_effects']}")