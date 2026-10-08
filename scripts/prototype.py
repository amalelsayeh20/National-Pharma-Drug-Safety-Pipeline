# ============================================================
# RxVision Pipeline - Drug Safety API Prototype
# ============================================================
""" Purpose:
 This prototype tests the integration between RxNorm and
 the FDA OpenFDA API.

# Workflow:
 1. Receive a drug/active ingredient name.
 2. Retrieve its RxCUI from the RxNorm API.
 3. Search OpenFDA for the drug's safety information.
 4. Extract available warning information.
 5. Return the data in a structured format.

- This is an initial prototype for the Drug Identification
 and Safety Information layer of the RxVision
 Pharmacovigilance Pipeline.

# Future development:
 - Normalize drug names and active ingredients.
 - Extract more FDA safety fields.
 - Store structured data in PostgreSQL.
 - Build the patient-drug safety conflict engine.
 - Add Airflow/Prefect orchestration.
"""
# ============================================================

import logging
import requests

# ------------------------------------------------------------
# Logging Configuration
# ------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
        # مستقبلاً تقدري تضيفي ملف تسجل فيه الأخطاء تلقائياً:
        # logging.FileHandler("rxvision_pipeline.log")
    ]
)
logger = logging.getLogger(__name__)

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------

RXNORM_URL = "https://rxnav.nlm.nih.gov/REST/rxcui.json"
FDA_LABEL_URL = "https://api.fda.gov/drug/label.json"

HEADERS = {
    "User-Agent": "RxVision-Pipeline/1.0"
}

TIMEOUT = 10


# ------------------------------------------------------------
# 1. Get RxCUI from RxNorm
# ------------------------------------------------------------

def get_rxcui(ingredient_name):
    """
    Retrieve the RxCUI identifier for a drug/active ingredient
    from the RxNorm API.

    Parameters:
        ingredient_name (str): Drug or active ingredient name.

    Returns:
        str or None: RxCUI if found, otherwise None.
    """

    params = {
        "name": ingredient_name
    }

    try:
        response = requests.get(
            RXNORM_URL,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        rxnorm_ids = data.get("idGroup", {}).get("rxnormId", [])

        if rxnorm_ids:
            return rxnorm_ids[0]

        logger.warning(f"No RxCUI found for: {ingredient_name}")
        return None

    except requests.exceptions.Timeout:
        logger.error("RxNorm API request timed out.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"RxNorm API request failed: {e}")
        return None

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Unexpected RxNorm response: {e}")
        return None


# ------------------------------------------------------------
# 2. Search OpenFDA Drug Label
# ------------------------------------------------------------

def search_fda_by_ingredient(ingredient_name):
    """
    Search OpenFDA drug labels using the active ingredient name.

    Returns:
        dict or None: First matching FDA drug label.
    """

    params = {
        "search": f"openfda.substance_name:{ingredient_name}",
        "limit": 1
    }

    try:
        response = requests.get(
            FDA_LABEL_URL,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        # 404 usually means that OpenFDA found no matching records.
        if response.status_code == 404:
            return None

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if results:
            return results[0]

        return None

    except requests.exceptions.Timeout:
        logger.error("OpenFDA API request timed out.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenFDA API request failed: {e}")
        return None

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Unexpected OpenFDA response: {e}")
        return None


# ------------------------------------------------------------
# 3. Search OpenFDA by RxCUI
# ------------------------------------------------------------

def search_fda_by_rxcui(rxcui):
    """
    Search OpenFDA drug labels using RxCUI.

    Returns:
        dict or None: First matching FDA drug label.
    """

    params = {
        "search": f"openfda.rxcui:{rxcui}",
        "limit": 1
    }

    try:
        response = requests.get(
            FDA_LABEL_URL,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT
        )

        if response.status_code == 404:
            return None

        response.raise_for_status()

        data = response.json()

        results = data.get("results", [])

        if results:
            return results[0]

        return None

    except requests.exceptions.Timeout:
        logger.error("OpenFDA RxCUI request timed out.")
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f"OpenFDA RxCUI request failed: {e}")
        return None

    except (KeyError, TypeError, ValueError) as e:
        logger.error(f"Unexpected OpenFDA response: {e}")
        return None


# ------------------------------------------------------------
# 4. Extract Safety Information
# ------------------------------------------------------------

def extract_safety_information(fda_record):
    """
    Extract relevant safety information from an FDA drug label.

    Returns:
        dict: Structured safety information.
    """

    if not fda_record:
        return None

    def extract_field(field_name):
        value = fda_record.get(field_name, [])

        if isinstance(value, list):
            return " ".join(value)

        return str(value)

    safety_data = {
        "warnings": extract_field("warnings"),
        "warnings_and_cautions": extract_field("warnings_and_cautions"),
        "contraindications": extract_field("contraindications"),
        "adverse_reactions": extract_field("adverse_reactions"),
        "drug_interactions": extract_field("drug_interactions"),
        "boxed_warning": extract_field("boxed_warning")
    }

    return safety_data


# ------------------------------------------------------------
# 5. Main Drug Safety Function
# ------------------------------------------------------------

def get_drug_safety_info(ingredient_name):
    """
    Complete RxVision prototype workflow.

    Workflow:
        Ingredient
            ↓
        RxNorm → RxCUI
            ↓
        OpenFDA
            ↓
        Safety Information

    Returns:
        dict: Structured drug safety information.
    """

    logger.info(f"Starting safety search for ingredient: {ingredient_name}")

    # Step 1: Get RxCUI
    rxcui = get_rxcui(ingredient_name)

    if rxcui:
        logger.info(f"RxCUI retrieved: {rxcui}")
    else:
        logger.warning("RxCUI not found, proceeding with raw name fallback.")

    # Step 2: Search FDA by ingredient
    logger.info("Querying OpenFDA by substance name...")
    fda_record = search_fda_by_ingredient(ingredient_name)

    # Step 3: Fallback to RxCUI
    if not fda_record and rxcui:
        logger.info("Substance search yielded no results. Attempting fallback via RxCUI...")
        fda_record = search_fda_by_rxcui(rxcui)

    # Step 4: No FDA result
    if not fda_record:
        logger.warning("No FDA drug label match found across endpoints.")
        return {
            "ingredient": ingredient_name,
            "rxcui": rxcui,
            "fda_found": False,
            "safety_information": None
        }

    logger.info("FDA drug label record successfully retrieved.")

    # Step 5: Extract safety information
    safety_information = extract_safety_information(fda_record)

    return {
        "ingredient": ingredient_name,
        "rxcui": rxcui,
        "fda_found": True,
        "safety_information": safety_information
    }


# ------------------------------------------------------------
# 6. Test the Prototype
# ------------------------------------------------------------

if __name__ == "__main__":

    test_ingredient = "Ibuprofen"

    result = get_drug_safety_info(test_ingredient)

    print("\n" + "=" * 60)
    print("RxVision Prototype Result")
    print("=" * 60)

    print(f"Ingredient: {result['ingredient']}")
    print(f"RxCUI: {result['rxcui']}")
    print(f"FDA Record Found: {result['fda_found']}")

    if result["safety_information"]:

        safety = result["safety_information"]

        print("\nFDA Safety Information Preview:")
        print("-" * 40)

        for field, value in safety.items():
            if value:
                print(f"\n[{field.upper()}]:")
                print(value[:300] + "...")

    else:
        print("\nNo safety information available.")

    
    print("Prototype execution completed.")
    