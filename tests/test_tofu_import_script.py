import pytest
from django.db import transaction

from api.models import (
    Nutrient, Ingredient, IngredientNutrientLink, FoodPortion,
    IngredientFoodCategory, NutrientCategory
)

# --- Helper function and data from tofu_import_script.py ---

def get_nutrient_details_for_test(fdc_name, fdc_unit, all_nutrient_data_for_ingredient):
    name_map = {
        "Total lipid (fat)": "Total lipid (fat)",
        "Carbohydrate, by difference": "Carbohydrate, by difference",
        "Fiber, total dietary": "Fiber, total dietary",
        "Total Sugars": "Sugars, total",
        "Calcium, Ca": "Calcium",
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
        "Folate, total": "Folate, total",
        "Folate, DFE": "Folate, DFE",
        "Choline, total": "Choline, total",
        "Vitamin B-12": "Vitamin B12",
        "Vitamin A, IU": "Vitamin A",
        "Vitamin E (alpha-tocopherol)": "Vitamin E (alpha-tocopherol)",
        "Vitamin D (D2 + D3), International Units": "Vitamin D (IU)",
        "Vitamin D (D2 + D3)": "Vitamin D (mcg)",
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
        "Alcohol, ethyl": "Alcohol, ethyl"
    }
    nutrient_name = name_map.get(fdc_name, fdc_name)
    nutrient_unit = fdc_unit

    if fdc_name == "Energy" and fdc_unit == "kJ":
        if any(n['name'] == "Energy" and n['unit'] == "kcal" for n in all_nutrient_data_for_ingredient):
            return None, None
    if fdc_name == "Folic acid" or fdc_name == "Folate, food":
        if any(n['name'] == "Folate, DFE" for n in all_nutrient_data_for_ingredient):
            return None, None
    if fdc_name == "Vitamin B-12, added":
        if any(n['name'] == "Vitamin B-12" for n in all_nutrient_data_for_ingredient):
            return None, None
    if fdc_name == "Vitamin E, added":
        if any(n['name'] == "Vitamin E (alpha-tocopherol)" for n in all_nutrient_data_for_ingredient):
            return None, None
    if fdc_name == "Vitamin D (D2 + D3), International Units":
        if any(n['name'] == "Vitamin D (D2 + D3)" and n['unit'] == "µg" for n in all_nutrient_data_for_ingredient):
            return None, None # Skip IU if mcg version is found
    elif fdc_name == "Vitamin D (D2 + D3)" and fdc_unit == "µg": # This is mcg
        nutrient_name = name_map.get("Vitamin D (D2 + D3)", "Vitamin D (mcg)")
        nutrient_unit = "µg"
    return nutrient_name, nutrient_unit

ingredient_name_to_test = "Tofu, raw"
ingredient_fdc_id_to_test = 172476
ingredient_category_to_test = IngredientFoodCategory.LEGUME
ingredient_food_class_to_test = "SR Legacy"

tofu_nutrients_data_for_test = [
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
    {"name": "Vitamin D (D2 + D3)", "amount": 0, "unit": "µg"}, 
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

tofu_portions_data_for_test = [
    {
        "amount": 0.5, "measure_unit_name": "cup", "portion_description": "0.5 cup",
        "gram_weight": 124, "modifier": None, "measure_unit_abbreviation": "cup"
    },
    {
        "amount": 0.25, "measure_unit_name": "block", "portion_description": "0.25 block",
        "gram_weight": 116, "modifier": None, "measure_unit_abbreviation": "block"
    }
]

@pytest.mark.django_db
class TestTofuImportScriptLogic:

    def _run_import_logic(self):
        """Helper method to encapsulate the script's core logic for reuse in tests."""
        with transaction.atomic(): # Ensure test operations are atomic if not default
            ingredient_obj, _ = Ingredient.objects.update_or_create(
                name=ingredient_name_to_test,
                defaults={
                    'fdc_id': ingredient_fdc_id_to_test,
                    'category': ingredient_category_to_test,
                    'base_unit_for_nutrition': 'g',
                    'food_class': ingredient_food_class_to_test,
                }
            )

            for nutrient_data in tofu_nutrients_data_for_test:
                fdc_name = nutrient_data["name"]
                fdc_unit = nutrient_data["unit"]
                amount = nutrient_data["amount"]

                db_nutrient_name, db_nutrient_unit = get_nutrient_details_for_test(
                    fdc_name, fdc_unit, tofu_nutrients_data_for_test
                )

                if db_nutrient_name is None or db_nutrient_unit is None:
                    continue

                nutrient_obj, _ = Nutrient.objects.get_or_create(
                    name=db_nutrient_name,
                    unit=db_nutrient_unit,
                    # Nutrient.category defaults to GENERAL, so no need to specify here
                    # unless a different category is desired for a specific nutrient.
                )
                IngredientNutrientLink.objects.update_or_create(
                    ingredient=ingredient_obj,
                    nutrient=nutrient_obj,
                    defaults={'amount_per_100_units': amount}
                )
                    
            for i, portion_data in enumerate(tofu_portions_data_for_test):
                FoodPortion.objects.update_or_create(
                    ingredient=ingredient_obj,
                    amount=portion_data["amount"],
                    measure_unit_name=portion_data["measure_unit_name"],
                    gram_weight=portion_data["gram_weight"], # Part of key for update_or_create
                    defaults={
                        'portion_description': portion_data["portion_description"],
                        'modifier': portion_data.get("modifier"),
                        'measure_unit_abbreviation': portion_data.get("measure_unit_abbreviation"),
                        'sequence_number': i + 1 
                    }
                )
        return ingredient_obj

    def test_tofu_ingredient_created_correctly(self):
        self._run_import_logic()
        
        assert Ingredient.objects.count() == 1
        tofu = Ingredient.objects.get(name=ingredient_name_to_test)
        assert tofu.fdc_id == ingredient_fdc_id_to_test
        assert tofu.category == ingredient_category_to_test
        assert tofu.food_class == ingredient_food_class_to_test
        assert tofu.base_unit_for_nutrition == 'g'

    def test_tofu_nutrient_links_count_is_correct(self):
        tofu = self._run_import_logic()
        
        expected_nutrient_links = 0
        # Determine how many unique (name, unit) pairs result after get_nutrient_details_for_test processing
        processed_nutrient_set = set()
        for nd_item in tofu_nutrients_data_for_test:
            name, unit = get_nutrient_details_for_test(nd_item['name'], nd_item['unit'], tofu_nutrients_data_for_test)
            if name and unit: # Ensure both are not None
                processed_nutrient_set.add((name, unit))
        expected_nutrient_links = len(processed_nutrient_set)

        assert IngredientNutrientLink.objects.filter(ingredient=tofu).count() == expected_nutrient_links
        # Also check the M2M relationship count via ingredient.nutrients
        assert tofu.nutrients.count() == expected_nutrient_links


    def test_specific_nutrient_values_and_skipped_nutrients(self):
        tofu = self._run_import_logic()

        # Test Protein
        protein_nutrient = Nutrient.objects.get(name="Protein", unit="g")
        protein_link = IngredientNutrientLink.objects.get(ingredient=tofu, nutrient=protein_nutrient)
        assert protein_link.amount_per_100_units == 8.08

        # Test Calcium
        calcium_nutrient = Nutrient.objects.get(name="Calcium", unit="mg")
        calcium_link = IngredientNutrientLink.objects.get(ingredient=tofu, nutrient=calcium_nutrient)
        assert calcium_link.amount_per_100_units == 350

        # Test Energy (kcal)
        energy_kcal_nutrient = Nutrient.objects.get(name="Energy", unit="kcal")
        energy_kcal_link = IngredientNutrientLink.objects.get(ingredient=tofu, nutrient=energy_kcal_nutrient)
        assert energy_kcal_link.amount_per_100_units == 76
        
        # Assert Energy (kJ) was skipped (no link, and Nutrient object might not exist if only Tofu uses it)
        with pytest.raises(IngredientNutrientLink.DoesNotExist):
            IngredientNutrientLink.objects.get(ingredient=tofu, nutrient__name="Energy", nutrient__unit="kJ")
        # Depending on whether "Energy (kJ)" nutrient existed before from other ingredients,
        # Nutrient.DoesNotExist might be too strong. Better to check the link.

        # Test Folate, DFE
        folate_dfe_nutrient = Nutrient.objects.get(name="Folate, DFE", unit="µg")
        folate_dfe_link = IngredientNutrientLink.objects.get(ingredient=tofu, nutrient=folate_dfe_nutrient)
        assert folate_dfe_link.amount_per_100_units == 15

        # Assert Folic acid was skipped
        with pytest.raises(IngredientNutrientLink.DoesNotExist):
            # Check by mapped name from get_nutrient_details_for_test if it differs, but here it's "Folic acid"
            IngredientNutrientLink.objects.get(ingredient=tofu, nutrient__name="Folic acid")


        # Test Vitamin D (mcg)
        # The name mapping for "Vitamin D (D2 + D3)" with unit µg is "Vitamin D (mcg)"
        vit_d_mcg_nutrient = Nutrient.objects.get(name="Vitamin D (mcg)", unit="µg")
        vit_d_mcg_link = IngredientNutrientLink.objects.get(ingredient=tofu, nutrient=vit_d_mcg_nutrient)
        assert vit_d_mcg_link.amount_per_100_units == 0.0 # Original data is 0

        # Assert Vitamin D (IU) was skipped
        with pytest.raises(IngredientNutrientLink.DoesNotExist):
            IngredientNutrientLink.objects.get(ingredient=tofu, nutrient__name="Vitamin D (IU)")


    def test_tofu_food_portions_are_created(self):
        tofu = self._run_import_logic()
        assert FoodPortion.objects.filter(ingredient=tofu).count() == 2

        cup_portion = FoodPortion.objects.get(ingredient=tofu, portion_description="0.5 cup")
        assert cup_portion.amount == 0.5
        assert cup_portion.gram_weight == 124
        assert cup_portion.measure_unit_name == "cup"

        block_portion = FoodPortion.objects.get(ingredient=tofu, portion_description="0.25 block")
        assert block_portion.amount == 0.25
        assert block_portion.gram_weight == 116
        assert block_portion.measure_unit_name == "block" 