# etl/API_client.py
import requests

def fetch_global_safety_data(scientific_name):
    clean_name = scientific_name.split(',')[0].strip()
    url = f"https://api.fda.gov/drug/label.json?search=active_ingredient:{clean_name}&limit=1"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            result = data['results'][0]
            
            # استخراج الحقول بكامل تفاصيلها زي الـ Notebook بالضبط
            warnings = " ".join(result.get('warnings', ['']))
            contraindications = " ".join(result.get('contraindications', ['']))
            boxed_warning = " ".join(result.get('boxed_warning', ['']))
            side_effects = " ".join(result.get('adverse_reactions', ['']))
            
            # دمج الحقول عشان نضمن إظهار كل التحذيرات والآثار الجانبية الحقيقية
            combined_safety_text = f"Warnings: {warnings} | Contraindications: {contraindications} | Boxed Warning: {boxed_warning}"
            
            # لو الـ side_effects فاضية، نعرض الـ warnings كاملة لأنها بتحتوي على تفاصيل الحساسية والمعدة زي ما ظهر عندك
            side_effects_output = side_effects if side_effects else warnings
            
            return {
                "status": "Success",
                "warnings": warnings[:1500] if warnings else "No explicit text warnings recorded.",
                "contraindications": contraindications[:1000] if contraindications else "No explicit contraindications recorded.",
                "boxed_warning": boxed_warning[:1000] if boxed_warning else "No explicit boxed warnings recorded.",
                "side_effects": side_effects_output[:1500] if side_effects_output else "No explicit side effects recorded.",
                "full_text": combined_safety_text.lower() + " " + side_effects.lower()
            }
        else:
            return {"status": "Not_Found", "message": "Detailed global safety data not found for this drug."}
    except Exception as e:
        return {"status": "Error", "message": str(e)}