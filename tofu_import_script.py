from django.db import transaction
from api.models import Nutrient, Ingredient, IngredientNutrientLink, FoodPortion, IngredientFoodCategory, NutrientCategory

# Helper function to map FDC nutrient names to your Nutrient model names/units if needed
def get_nutrient_details(fdc_name, fdc_unit, all_nutrient_data_for_ingredient):
    name_map = {
        "Total lipid (fat)": "Total lipid (fat)", # Keeping FDC version as it's descriptive
        "Carbohydrate, by difference": "Carbohydrate, by difference",
        "Fiber, total dietary": "Fiber, total dietary",
        "Total Sugars": "Sugars, total",
        "Calcium, Ca": "Calcium", # Assuming your model stores "Calcium" not "Calcium, Ca"
        "Iron, Fe": "Iron",
        "Magnesium, Mg": "Magnesium",
        "Phosphorus, P": "Phosphorus",
        "Potassium, K": "Potassium",
        "Sodium, Na": "Sodium",
        "Zinc, Zn": "Zinc",
        "Copper, Cu": "Copper",
        "Manganese, Mn": "Manganese",
        "Selenium, Se": "Selenium",
        "Vitamin C, total ascorbic acid": "Vitamin C",
        "Vitamin B-6": "Vitamin B6",
        "Folate, total": "Folate, total", # General folate entry from FDC
        "Folate, DFE": "Folate, DFE", # Often preferred for calculations
        "Choline, total": "Choline, total", # Keeping FDC version
        "Vitamin B-12": "Vitamin B12",
        "Vitamin A, IU": "Vitamin A", # Consider if you store as RAE mcg
        "Vitamin E (alpha-tocopherol)": "Vitamin E (alpha-tocopherol)",
        "Vitamin D (D2 + D3), International Units": "Vitamin D (IU)", # Specific for IU
        "Vitamin D (D2 + D3)": "Vitamin D (mcg)", # Specific for mcg
        "Vitamin K (phylloquinone)": "Vitamin K (phylloquinone)",
        "Fatty acids, total saturated": "Fatty acids, total saturated",
        "SFA 4:0": "SFA 4:0 (Butyric acid)",
        "SFA 6:0": "SFA 6:0 (Caproic acid)",
        "SFA 8:0": "SFA 8:0 (Caprylic acid)",
        "SFA 10:0": "SFA 10:0 (Capric acid)",
        "SFA 12:0": "SFA 12:0 (Lauric acid)",
        "SFA 14:0": "SFA 14:0 (Myristic acid)",
        "SFA 16:0": "SFA 16:0 (Palmitic acid)",
        "SFA 18:0": "SFA 18:0 (Stearic acid)",
        "Fatty acids, total monounsaturated": "Fatty acids, total monounsaturated",
        "MUFA 16:1": "MUFA 16:1 (Palmitoleic acid)",
        "MUFA 18:1": "MUFA 18:1 (Oleic acid)",
        "MUFA 20:1": "MUFA 20:1 (Gadoleic acid)",
        "MUFA 22:1": "MUFA 22:1 (Erucic acid)",
        "Fatty acids, total polyunsaturated": "Fatty acids, total polyunsaturated",
        "PUFA 18:2": "PUFA 18:2 (Linoleic acid)",
        "PUFA 18:3": "PUFA 18:3 (Linolenic acid)",
        "PUFA 18:4": "PUFA 18:4 (Stearidonic acid)",
        "PUFA 20:4": "PUFA 20:4 (Arachidonic acid)",
        "PUFA 20:5 n-3 (EPA)": "PUFA 20:5 n-3 (EPA)",
        "PUFA 22:5 n-3 (DPA)": "PUFA 22:5 n-3 (DPA)",
        "PUFA 22:6 n-3 (DHA)": "PUFA 22:6 n-3 (DHA)",
        "Fatty acids, total trans": "Fatty acids, total trans",
        "Alcohol, ethyl": "Alcohol, ethyl" # Or just "Alcohol"
    }
    nutrient_name = name_map.get(fdc_name, fdc_name) # Default to FDC name if not in map
    nutrient_unit = fdc_unit

    # Skip Energy in kJ if Energy in kcal is also present for this ingredient
    if fdc_name == "Energy" and fdc_unit == "kJ":
        if any(n['name'] == "Energy" and n['unit'] == "kcal" for n in all_nutrient_data_for_ingredient):
            return None, None 
    
    # Skip Folic acid and Folate, food if Folate, DFE is present
    if fdc_name == "Folic acid" or fdc_name == "Folate, food":
        if any(n['name'] == "Folate, DFE" for n in all_nutrient_data_for_ingredient):
            return None, None

    # Skip Vitamin B-12, added if Vitamin B-12 is present
    if fdc_name == "Vitamin B-12, added":
        if any(n['name'] == "Vitamin B-12" for n in all_nutrient_data_for_ingredient):
            return None, None

    # Skip Vitamin E, added if Vitamin E (alpha-tocopherol) is present
    if fdc_name == "Vitamin E, added":
        if any(n['name'] == "Vitamin E (alpha-tocopherol)" for n in all_nutrient_data_for_ingredient):
            return None, None

    # Skip Vitamin D (IU) if Vitamin D (mcg) is present
    if fdc_name == "Vitamin D (D2 + D3), International Units": # This is IU
        if any(n['name'] == "Vitamin D (D2 + D3)" and n['unit'] == "µg" for n in all_nutrient_data_for_ingredient):
            nutrient_name = name_map.get("Vitamin D (D2 + D3)", "Vitamin D (mcg)") # Ensure mapped name for mcg
            nutrient_unit = "µg" # Ensure unit is mcg
            # This effectively skips the IU entry by returning None, None if µg version is found
            # The µg version itself will be processed when its turn comes.
            return None, None # Skip IU if mcg version is found
    elif fdc_name == "Vitamin D (D2 + D3)" and fdc_unit == "µg": # This is mcg
        nutrient_name = name_map.get("Vitamin D (D2 + D3)", "Vitamin D (mcg)")
        nutrient_unit = "µg"


    return nutrient_name, nutrient_unit

# Data for Tofu, raw (per 100g)
ingredient_name = "Tofu, raw"
ingredient_fdc_id = 172476
# FDC Food Category: Legumes and Legume Products
# Based on IngredientFoodCategory choices, LEGUME seems appropriate
ingredient_category_value = IngredientFoodCategory.LEGUME 
# From FDC foodClass for this item: "Survey (FNDDS)" or "Branded Food" often.
# FDC ID 172476 is 'Tofu, raw' from SR Legacy, often mapping to 'FinalFood' or similar.
# Assuming 'FinalFood' if needed, or leave blank if not critical for your model.
ingredient_food_class = "SR Legacy" # Placeholder, adjust as needed or remove if not used

tofu_nutrients_data = [
    {"name": "Water", "amount": 84.6, "unit": "g"},
    {"name": "Energy", "amount": 76, "unit": "kcal"},
    {"name": "Energy", "amount": 317, "unit": "kJ"},
    {"name": "Protein", "amount": 8.08, "unit": "g"},
    {"name": "Total lipid (fat)", "amount": 4.78, "unit": "g"},
    {"name": "Ash", "amount": 0.72, "unit": "g"},
    {"name": "Carbohydrate, by difference", "amount": 1.87, "unit": "g"},
    {"name": "Fiber, total dietary", "amount": 0.3, "unit": "g"},
    {"name": "Total Sugars", "amount": 0.62, "unit": "g"},
    {"name": "Calcium, Ca", "amount": 350, "unit": "mg"},
    {"name": "Iron, Fe", "amount": 5.36, "unit": "mg"},
    {"name": "Magnesium, Mg", "amount": 30, "unit": "mg"},
    {"name": "Phosphorus, P", "amount": 97, "unit": "mg"},
    {"name": "Potassium, K", "amount": 121, "unit": "mg"},
    {"name": "Sodium, Na", "amount": 7, "unit": "mg"},
    {"name": "Zinc, Zn", "amount": 0.8, "unit": "mg"},
    {"name": "Copper, Cu", "amount": 0.193, "unit": "mg"},
    {"name": "Manganese, Mn", "amount": 0.605, "unit": "mg"},
    {"name": "Selenium, Se", "amount": 8.9, "unit": "µg"},
    {"name": "Vitamin C, total ascorbic acid", "amount": 0.1, "unit": "mg"},
    {"name": "Thiamin", "amount": 0.081, "unit": "mg"},
    {"name": "Riboflavin", "amount": 0.052, "unit": "mg"},
    {"name": "Niacin", "amount": 0.195, "unit": "mg"},
    {"name": "Pantothenic acid", "amount": 0.068, "unit": "mg"},
    {"name": "Vitamin B-6", "amount": 0.047, "unit": "mg"},
    {"name": "Folate, total", "amount": 15, "unit": "µg"},
    {"name": "Folic acid", "amount": 0, "unit": "µg"},
    {"name": "Folate, food", "amount": 15, "unit": "µg"},
    {"name": "Folate, DFE", "amount": 15, "unit": "µg"},
    {"name": "Choline, total", "amount": 28.8, "unit": "mg"},
    {"name": "Vitamin B-12", "amount": 0, "unit": "µg"},
    {"name": "Vitamin B-12, added", "amount": 0, "unit": "µg"},
    {"name": "Vitamin A, IU", "amount": 85, "unit": "IU"},
    {"name": "Vitamin E (alpha-tocopherol)", "amount": 0.01, "unit": "mg"},
    {"name": "Vitamin E, added", "amount": 0, "unit": "mg"},
    {"name": "Vitamin D (D2 + D3), International Units", "amount": 0, "unit": "IU"},
    {"name": "Vitamin D (D2 + D3)", "amount": 0, "unit": "µg"}, # µg version
    {"name": "Vitamin K (phylloquinone)", "amount": 2.4, "unit": "µg"},
    {"name": "Fatty acids, total saturated", "amount": 0.691, "unit": "g"},
    {"name": "SFA 4:0", "amount": 0, "unit": "g"},
    {"name": "SFA 6:0", "amount": 0, "unit": "g"},
    {"name": "SFA 8:0", "amount": 0, "unit": "g"},
    {"name": "SFA 10:0", "amount": 0, "unit": "g"},
    {"name": "SFA 12:0", "amount": 0, "unit": "g"},
    {"name": "SFA 14:0", "amount": 0.013, "unit": "g"},
    {"name": "SFA 16:0", "amount": 0.507, "unit": "g"},
    {"name": "SFA 18:0", "amount": 0.171, "unit": "g"},
    {"name": "Fatty acids, total monounsaturated", "amount": 1.06, "unit": "g"},
    {"name": "MUFA 16:1", "amount": 0.013, "unit": "g"},
    {"name": "MUFA 18:1", "amount": 1.04, "unit": "g"},
    {"name": "MUFA 20:1", "amount": 0, "unit": "g"},
    {"name": "MUFA 22:1", "amount": 0, "unit": "g"},
    {"name": "Fatty acids, total polyunsaturated", "amount": 2.7, "unit": "g"},
    {"name": "PUFA 18:2", "amount": 2.38, "unit": "g"},
    {"name": "PUFA 18:3", "amount": 0.319, "unit": "g"},
    {"name": "PUFA 18:4", "amount": 0, "unit": "g"},
    {"name": "PUFA 20:4", "amount": 0, "unit": "g"},
    {"name": "PUFA 20:5 n-3 (EPA)", "amount": 0, "unit": "g"},
    {"name": "PUFA 22:5 n-3 (DPA)", "amount": 0, "unit": "g"},
    {"name": "PUFA 22:6 n-3 (DHA)", "amount": 0, "unit": "g"},
    {"name": "Fatty acids, total trans", "amount": 0, "unit": "g"},
    {"name": "Cholesterol", "amount": 0, "unit": "mg"},
    {"name": "Tryptophan", "amount": 0.12, "unit": "g"},
    {"name": "Threonine", "amount": 0.402, "unit": "g"},
    {"name": "Isoleucine", "amount": 0.435, "unit": "g"},
    {"name": "Leucine", "amount": 0.713, "unit": "g"},
    {"name": "Lysine", "amount": 0.452, "unit": "g"},
    {"name": "Methionine", "amount": 0.108, "unit": "g"},
    {"name": "Cystine", "amount": 0.029, "unit": "g"},
    {"name": "Phenylalanine", "amount": 0.428, "unit": "g"},
    {"name": "Tyrosine", "amount": 0.359, "unit": "g"},
    {"name": "Valine", "amount": 0.446, "unit": "g"},
    {"name": "Arginine", "amount": 0.701, "unit": "g"},
    {"name": "Histidine", "amount": 0.221, "unit": "g"},
    {"name": "Alanine", "amount": 0.396, "unit": "g"},
    {"name": "Aspartic acid", "amount": 1.04, "unit": "g"},
    {"name": "Glutamic acid", "amount": 1.68, "unit": "g"},
    {"name": "Glycine", "amount": 0.375, "unit": "g"},
    {"name": "Proline", "amount": 0.555, "unit": "g"},
    {"name": "Serine", "amount": 0.519, "unit": "g"},
    {"name": "Alcohol, ethyl", "amount": 0, "unit": "g"},
    {"name": "Caffeine", "amount": 0, "unit": "mg"},
    {"name": "Theobromine", "amount": 0, "unit": "mg"}
]

tofu_portions_data = [
    {
        "amount": 0.5, "measure_unit_name": "cup", "portion_description": "0.5 cup",
        "gram_weight": 124, "modifier": None, "measure_unit_abbreviation": "cup"
    },
    {
        "amount": 0.25, "measure_unit_name": "block", "portion_description": "0.25 block",
        "gram_weight": 116, "modifier": None, "measure_unit_abbreviation": "block"
    }
]

print("Starting Tofu data import...")

try:
    with transaction.atomic():
        # Create/Update Ingredient
        ingredient_obj, created_ingredient = Ingredient.objects.update_or_create(
            name=ingredient_name,
            defaults={
                'fdc_id': ingredient_fdc_id,
                'category': ingredient_category_value,
                'base_unit_for_nutrition': 'g',
                'food_class': ingredient_food_class, # Add food_class if you use it
            }
        )
        if created_ingredient:
            print(f"Created ingredient: {ingredient_obj.name}")
        else:
            print(f"Updated ingredient: {ingredient_obj.name}")

        # Add Nutrients and Links
        for nutrient_data in tofu_nutrients_data:
            fdc_name = nutrient_data["name"]
            fdc_unit = nutrient_data["unit"]
            amount = nutrient_data["amount"]

            # Pass the full list for contextual decisions (e.g. skipping kJ if kcal exists for this item)
            db_nutrient_name, db_nutrient_unit = get_nutrient_details(fdc_name, fdc_unit, tofu_nutrients_data)

            if db_nutrient_name is None or db_nutrient_unit is None:
                print(f"Skipping nutrient: {fdc_name} ({fdc_unit}) due to filter rules.")
                continue
            
            # --- Modified Nutrient Handling ---
            nutrient_candidates = Nutrient.objects.filter(name=db_nutrient_name, unit=db_nutrient_unit)
            nutrient_obj = None
            created_nutrient = False

            if nutrient_candidates.exists():
                if nutrient_candidates.count() > 1:
                    print(f"WARNING: Multiple existing Nutrient objects found for name='{db_nutrient_name}', unit='{db_nutrient_unit}'. Using the first one found.")
                nutrient_obj = nutrient_candidates.first()
            else:
                nutrient_obj = Nutrient.objects.create(
                    name=db_nutrient_name,
                    unit=db_nutrient_unit,
                    category=NutrientCategory.GENERAL # Default, adjust if specific category logic exists
                )
                created_nutrient = True
            # --- End Modified Nutrient Handling ---

            if created_nutrient:
                print(f"  Created nutrient: {db_nutrient_name} ({db_nutrient_unit})")
            
            IngredientNutrientLink.objects.update_or_create(
                ingredient=ingredient_obj,
                nutrient=nutrient_obj,
                defaults={'amount_per_100_units': amount}
            )
                
        print(f"Processed nutrient links for {ingredient_obj.name}.")

        # Add Food Portions
        for i, portion_data in enumerate(tofu_portions_data):
            portion_obj, created_portion = FoodPortion.objects.update_or_create(
                ingredient=ingredient_obj,
                # Using more fields to define uniqueness for update_or_create for portions,
                # as portion_description alone might not be unique enough if gram_weight changes.
                amount=portion_data["amount"],
                measure_unit_name=portion_data["measure_unit_name"],
                gram_weight=portion_data["gram_weight"], # Consider if gram_weight should be part of key or just a default
                defaults={
                    'portion_description': portion_data["portion_description"],
                    'modifier': portion_data.get("modifier"),
                    'measure_unit_abbreviation': portion_data.get("measure_unit_abbreviation"),
                    'sequence_number': i + 1 
                }
            )
            if created_portion:
                print(f"  Created portion: {portion_obj.portion_description} ({portion_obj.gram_weight}g) for {ingredient_obj.name}")
            else:
                print(f"  Updated portion: {portion_obj.portion_description} ({portion_obj.gram_weight}g) for {ingredient_obj.name}")
        
        print(f"Processed portions for {ingredient_obj.name}.")

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    print(traceback.format_exc())


print("Tofu data import script finished.") 