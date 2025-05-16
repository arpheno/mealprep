import pytest
import json
import shutil
from pathlib import Path
from io import StringIO

from django.core.management import call_command, CommandError
from django.db import connection

from api.models import Ingredient, Nutrient, IngredientNutrientLink, FoodPortion

# Content of data/my_foods.json (Tofu example)
MY_FOODS_JSON_CONTENT = r'''
[
  {
    "fdcId": -1,
    "description": "Tofu, raw",
    "foodClass": "Custom",
    "foodCategory": {
      "description": "Custom Foods",
      "code": "9999", 
      "id": -1 
    },
    "foodNutrients": [
      {
        "nutrient": {"id": 1051, "number": "255", "name": "Water", "rank": 100, "unitName": "g"},
        "amount": 84.6
      },
      {
        "nutrient": {"id": 1008, "number": "208", "name": "Energy", "rank": 300, "unitName": "kcal"},
        "amount": 76 
      },
      {
        "nutrient": {"id": 1003, "number": "203", "name": "Protein", "rank": 600, "unitName": "g"},
        "amount": 8.08
      },
      {
        "nutrient": {"id": 1004, "number": "204", "name": "Total lipid (fat)", "rank": 800, "unitName": "g"},
        "amount": 4.78
      },
      {
        "nutrient": {"id": 1007, "number": "207", "name": "Ash", "rank": 1000, "unitName": "g"},
        "amount": 0.72
      },
      {
        "nutrient": {"id": 1005, "number": "205", "name": "Carbohydrate, by difference", "rank": 1110, "unitName": "g"},
        "amount": 1.87
      },
      {
        "nutrient": {"id": 1079, "number": "291", "name": "Fiber, total dietary", "rank": 1200, "unitName": "g"},
        "amount": 0.3
      },
      {
        "nutrient": {"id": 2000, "number": "269", "name": "Sugars, total including NLEA", "rank": 1510, "unitName": "g"},
        "amount": 0.62
      },
      {
        "nutrient": {"id": 1087, "number": "301", "name": "Calcium, Ca", "rank": 5300, "unitName": "mg"},
        "amount": 350
      },
      {
        "nutrient": {"id": 1089, "number": "303", "name": "Iron, Fe", "rank": 5400, "unitName": "mg"},
        "amount": 5.36
      },
      {
        "nutrient": {"id": 1090, "number": "304", "name": "Magnesium, Mg", "rank": 5500, "unitName": "mg"},
        "amount": 30
      },
      {
        "nutrient": {"id": 1091, "number": "305", "name": "Phosphorus, P", "rank": 5600, "unitName": "mg"},
        "amount": 97
      },
      {
        "nutrient": {"id": 1092, "number": "306", "name": "Potassium, K", "rank": 5700, "unitName": "mg"},
        "amount": 121
      },
      {
        "nutrient": {"id": 1093, "number": "307", "name": "Sodium, Na", "rank": 5800, "unitName": "mg"},
        "amount": 7
      },
      {
        "nutrient": {"id": 1095, "number": "309", "name": "Zinc, Zn", "rank": 5900, "unitName": "mg"},
        "amount": 0.8
      },
      {
        "nutrient": {"id": 1098, "number": "312", "name": "Copper, Cu", "rank": 6000, "unitName": "mg"},
        "amount": 0.193
      },
      {
        "nutrient": {"id": 1101, "number": "315", "name": "Manganese, Mn", "rank": 6100, "unitName": "mg"},
        "amount": 0.605
      },
      {
        "nutrient": {"id": 1103, "number": "317", "name": "Selenium, Se", "rank": 6200, "unitName": "µg"},
        "amount": 8.9
      },
      {
        "nutrient": {"id": 1162, "number": "401", "name": "Vitamin C, total ascorbic acid", "rank": 6300, "unitName": "mg"},
        "amount": 0.1
      },
      {
        "nutrient": {"id": 1165, "number": "404", "name": "Thiamin", "rank": 6400, "unitName": "mg"},
        "amount": 0.081
      },
      {
        "nutrient": {"id": 1166, "number": "405", "name": "Riboflavin", "rank": 6500, "unitName": "mg"},
        "amount": 0.052
      },
      {
        "nutrient": {"id": 1167, "number": "406", "name": "Niacin", "rank": 6600, "unitName": "mg"},
        "amount": 0.195
      },
      {
        "nutrient": {"id": 1170, "number": "410", "name": "Pantothenic acid", "rank": 6700, "unitName": "mg"},
        "amount": 0.068
      },
      {
        "nutrient": {"id": 1175, "number": "415", "name": "Vitamin B-6", "rank": 6800, "unitName": "mg"},
        "amount": 0.047
      },
      {
        "nutrient": {"id": 1185, "number": "435", "name": "Folate, DFE", "rank": 7100, "unitName": "µg"},
        "amount": 15
      },
      {
        "nutrient": {"id": 1186, "number": "437", "name": "Choline, total", "rank": 7110, "unitName": "mg"},
        "amount": 28.8
      },
      {
        "nutrient": {"id": 1178, "number": "418", "name": "Vitamin B-12", "rank": 7300, "unitName": "µg"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1104, "number": "318", "name": "Vitamin A, IU", "rank": 7410, "unitName": "IU"},
        "amount": 85
      },
      {
        "nutrient": {"id": 1109, "number": "323", "name": "Vitamin E (alpha-tocopherol)", "rank": 7900, "unitName": "mg"},
        "amount": 0.01
      },
      {
        "nutrient": {"id": 1114, "number": "328", "name": "Vitamin D (D2 + D3)", "rank": 8710, "unitName": "µg"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1187, "number": "430", "name": "Vitamin K (phylloquinone)", "rank": 8800, "unitName": "µg"},
        "amount": 2.4
      },
      {
        "nutrient": {"id": 1258, "number": "606", "name": "Fatty acids, total saturated", "rank": 9700, "unitName": "g"},
        "amount": 0.691
      },
      {
        "nutrient": {"id": -1001, "number": "CUSTOM_N_1001", "name": "SFA 4:0", "rank": 9800, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1002, "number": "CUSTOM_N_1002", "name": "SFA 6:0", "rank": 9900, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1003, "number": "CUSTOM_N_1003", "name": "SFA 8:0", "rank": 10000, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1004, "number": "CUSTOM_N_1004", "name": "SFA 10:0", "rank": 10100, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1005, "number": "CUSTOM_N_1005", "name": "SFA 12:0", "rank": 10300, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1264, "number": "612", "name": "SFA 14:0", "rank": 10500, "unitName": "g"},
        "amount": 0.013
      },
      {
        "nutrient": {"id": 1265, "number": "613", "name": "SFA 16:0", "rank": 10700, "unitName": "g"},
        "amount": 0.507
      },
      {
        "nutrient": {"id": 1266, "number": "614", "name": "SFA 18:0", "rank": 10900, "unitName": "g"},
        "amount": 0.171
      },
      {
        "nutrient": {"id": 1292, "number": "645", "name": "Fatty acids, total monounsaturated", "rank": 11400, "unitName": "g"},
        "amount": 1.06
      },
      {
        "nutrient": {"id": -1006, "number": "CUSTOM_N_1006", "name": "MUFA 16:1", "rank": 11800, "unitName": "g"},
        "amount": 0.013
      },
      {
        "nutrient": {"id": -1007, "number": "CUSTOM_N_1007", "name": "MUFA 18:1", "rank": 12200, "unitName": "g"},
        "amount": 1.04
      },
      {
        "nutrient": {"id": -1008, "number": "CUSTOM_N_1008", "name": "MUFA 20:1", "rank": 12400, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1009, "number": "CUSTOM_N_1009", "name": "MUFA 22:1", "rank": 12600, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1293, "number": "646", "name": "Fatty acids, total polyunsaturated", "rank": 12900, "unitName": "g"},
        "amount": 2.7
      },
      {
        "nutrient": {"id": -1010, "number": "CUSTOM_N_1010", "name": "PUFA 18:2", "rank": 13200, "unitName": "g"},
        "amount": 2.38
      },
      {
        "nutrient": {"id": -1011, "number": "CUSTOM_N_1011", "name": "PUFA 18:3", "rank": 14000, "unitName": "g"},
        "amount": 0.319
      },
      {
        "nutrient": {"id": -1012, "number": "CUSTOM_N_1012", "name": "PUFA 18:4", "rank": 14200, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1013, "number": "CUSTOM_N_1013", "name": "PUFA 20:4", "rank": 14700, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1278, "number": "629", "name": "PUFA 20:5 n-3 (EPA)", "rank": 15000, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1280, "number": "631", "name": "PUFA 22:5 n-3 (DPA)", "rank": 15200, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1272, "number": "621", "name": "PUFA 22:6 n-3 (DHA)", "rank": 15300, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1257, "number": "605", "name": "Fatty acids, total trans", "rank": 15400, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": 1253, "number": "601", "name": "Cholesterol", "rank": 15700, "unitName": "mg"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1014, "number": "CUSTOM_N_1014", "name": "Tryptophan", "rank": -1, "unitName": "g"},
        "amount": 0.12
      },
      {
        "nutrient": {"id": -1015, "number": "CUSTOM_N_1015", "name": "Threonine", "rank": -1, "unitName": "g"},
        "amount": 0.402
      },
      {
        "nutrient": {"id": -1016, "number": "CUSTOM_N_1016", "name": "Isoleucine", "rank": -1, "unitName": "g"},
        "amount": 0.435
      },
      {
        "nutrient": {"id": -1017, "number": "CUSTOM_N_1017", "name": "Leucine", "rank": -1, "unitName": "g"},
        "amount": 0.713
      },
      {
        "nutrient": {"id": -1018, "number": "CUSTOM_N_1018", "name": "Lysine", "rank": -1, "unitName": "g"},
        "amount": 0.452
      },
      {
        "nutrient": {"id": -1019, "number": "CUSTOM_N_1019", "name": "Methionine", "rank": -1, "unitName": "g"},
        "amount": 0.108
      },
      {
        "nutrient": {"id": -1020, "number": "CUSTOM_N_1020", "name": "Cystine", "rank": -1, "unitName": "g"},
        "amount": 0.029
      },
      {
        "nutrient": {"id": -1021, "number": "CUSTOM_N_1021", "name": "Phenylalanine", "rank": -1, "unitName": "g"},
        "amount": 0.428
      },
      {
        "nutrient": {"id": -1022, "number": "CUSTOM_N_1022", "name": "Tyrosine", "rank": -1, "unitName": "g"},
        "amount": 0.359
      },
      {
        "nutrient": {"id": -1023, "number": "CUSTOM_N_1023", "name": "Valine", "rank": -1, "unitName": "g"},
        "amount": 0.446
      },
      {
        "nutrient": {"id": -1024, "number": "CUSTOM_N_1024", "name": "Arginine", "rank": -1, "unitName": "g"},
        "amount": 0.701
      },
      {
        "nutrient": {"id": -1025, "number": "CUSTOM_N_1025", "name": "Histidine", "rank": -1, "unitName": "g"},
        "amount": 0.221
      },
      {
        "nutrient": {"id": -1026, "number": "CUSTOM_N_1026", "name": "Alanine", "rank": -1, "unitName": "g"},
        "amount": 0.396
      },
      {
        "nutrient": {"id": -1027, "number": "CUSTOM_N_1027", "name": "Aspartic acid", "rank": -1, "unitName": "g"},
        "amount": 1.04
      },
      {
        "nutrient": {"id": -1028, "number": "CUSTOM_N_1028", "name": "Glutamic acid", "rank": -1, "unitName": "g"},
        "amount": 1.68
      },
      {
        "nutrient": {"id": -1029, "number": "CUSTOM_N_1029", "name": "Glycine", "rank": -1, "unitName": "g"},
        "amount": 0.375
      },
      {
        "nutrient": {"id": -1030, "number": "CUSTOM_N_1030", "name": "Proline", "rank": -1, "unitName": "g"},
        "amount": 0.555
      },
      {
        "nutrient": {"id": -1031, "number": "CUSTOM_N_1031", "name": "Serine", "rank": -1, "unitName": "g"},
        "amount": 0.519
      },
      {
        "nutrient": {"id": -1032, "number": "CUSTOM_N_1032", "name": "Alcohol, ethyl", "rank": -1, "unitName": "g"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1033, "number": "CUSTOM_N_1033", "name": "Caffeine", "rank": -1, "unitName": "mg"},
        "amount": 0
      },
      {
        "nutrient": {"id": -1034, "number": "CUSTOM_N_1034", "name": "Theobromine", "rank": -1, "unitName": "mg"},
        "amount": 0
      }
    ],
    "foodPortions": [
      {
        "id": -101, 
        "amount": 0.5,
        "gramWeight": 124.0,
        "modifier": null,
        "portionDescription": "0.5 cup",
        "sequenceNumber": 1,
        "measureUnit": {"id": -10101, "name": "cup", "abbreviation": "cup"}
      },
      {
        "id": -102,
        "amount": 0.25,
        "gramWeight": 116.0,
        "modifier": null,
        "portionDescription": "0.25 block",
        "sequenceNumber": 2,
        "measureUnit": {"id": -10102, "name": "block", "abbreviation": "block"}
      }
    ]
  }
]
'''
# Note: Energy was 76, Protein 8.08, Fat 4.78, Carb 1.87, Fiber 0.3, Sugar 0.62 in original data.
# Manually changed some in the JSON content above for testing update functionality later.
# Energy: 76 -> 137 (for test update)
# Protein: 8.08 -> 15.0 (for test update)
# Total lipid (fat): 4.78 -> 8.0 (for test update)
# Carbohydrate, by difference: 1.87 -> 0.7 (for test update)
# Fiber, total dietary: 0.3 -> 1.0 (for test update)
# Total Sugars: 0.62 -> 0.5 (for test update)

@pytest.fixture
def temp_json_file(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "my_foods_test.json"
    
    # Initial content for the first import run
    initial_data = json.loads(MY_FOODS_JSON_CONTENT)
    initial_data[0]['foodNutrients'][1]['amount'] = 76 # Energy
    initial_data[0]['foodNutrients'][2]['amount'] = 8.08 # Protein
    initial_data[0]['foodNutrients'][3]['amount'] = 4.78 # Fat
    initial_data[0]['foodNutrients'][5]['amount'] = 1.87 # Carb
    initial_data[0]['foodNutrients'][6]['amount'] = 0.3  # Fiber
    initial_data[0]['foodNutrients'][7]['amount'] = 0.62 # Sugar


    with open(file_path, 'w') as f:
        json.dump(initial_data, f)
    return file_path

@pytest.mark.django_db
class TestImportFDCFoundationalCommand:

    def test_import_custom_tofu_data_successful(self, temp_json_file):
        stdout = StringIO()
        stderr = StringIO()
        
        # Initial import
        call_command('import_fdc_foundational', str(temp_json_file), stdout=stdout, stderr=stderr)

        # Check stdout for success messages (optional, but good for debugging)
        # self.assertIn("Successfully imported", stdout.getvalue())
        assert Ingredient.objects.count() == 1
        tofu_ingredient = Ingredient.objects.get(fdc_id=-1)
        assert tofu_ingredient.name == "Tofu, raw"
        assert tofu_ingredient.food_class == "Custom"

        # Expected number of nutrients from the JSON.
        # The MY_FOODS_JSON_CONTENT has 76 unique nutrient entries.
        assert Nutrient.objects.count() == 76 
        assert IngredientNutrientLink.objects.filter(ingredient=tofu_ingredient).count() == 76

        # Check specific nutrient links
        protein = Nutrient.objects.get(fdc_nutrient_id=1003) # Protein FDC ID
        protein_link = IngredientNutrientLink.objects.get(ingredient=tofu_ingredient, nutrient=protein)
        assert protein_link.amount_per_100_units == 8.08

        calcium = Nutrient.objects.get(fdc_nutrient_id=1087) # Calcium FDC ID
        calcium_link = IngredientNutrientLink.objects.get(ingredient=tofu_ingredient, nutrient=calcium)
        assert calcium_link.amount_per_100_units == 350

        # Check custom nutrient (negative FDC ID)
        sfa_4_0 = Nutrient.objects.get(fdc_nutrient_id=-1001) 
        assert sfa_4_0.name == "SFA 4:0"
        sfa_4_0_link = IngredientNutrientLink.objects.get(ingredient=tofu_ingredient, nutrient=sfa_4_0)
        assert sfa_4_0_link.amount_per_100_units == 0

        assert FoodPortion.objects.filter(ingredient=tofu_ingredient).count() == 2
        cup_portion = FoodPortion.objects.get(ingredient=tofu_ingredient, fdc_portion_id=-101)
        assert cup_portion.portion_description == "0.5 cup"
        assert cup_portion.gram_weight == 124.0
        assert cup_portion.measure_unit_name == "cup"

        # Check that no errors were written to stderr
        assert stderr.getvalue() == ""

    def test_import_update_existing_and_idempotency(self, temp_json_file):
        stdout = StringIO()
        stderr = StringIO()

        # First import
        call_command('import_fdc_foundational', str(temp_json_file), '--update-existing', stdout=stdout, stderr=stderr)
        
        initial_ingredient_count = Ingredient.objects.count()
        initial_nutrient_count = Nutrient.objects.count()
        initial_link_count = IngredientNutrientLink.objects.count()
        initial_portion_count = FoodPortion.objects.count()

        assert initial_ingredient_count == 1
        assert initial_nutrient_count == 76 
        assert initial_link_count == 76
        assert initial_portion_count == 2
        
        # Modify the JSON file for update
        updated_data = json.loads(MY_FOODS_JSON_CONTENT) # Load the master template
        # Change some values from the original master values
        updated_data[0]['description'] = "Tofu, raw (Updated)" 
        updated_data[0]['foodNutrients'][1]['amount'] = 137.0 # Energy (Original master had 76, fixture set to 76, now updating to 137)
        updated_data[0]['foodNutrients'][2]['amount'] = 15.0  # Protein (Original master had 8.08, fixture set to 8.08, now updating to 15.0)
        updated_data[0]['foodPortions'][0]['gramWeight'] = 130.0 # Update cup portion gram weight
        
        with open(temp_json_file, 'w') as f:
            json.dump(updated_data, f)

        # Second import with --update-existing
        call_command('import_fdc_foundational', str(temp_json_file), '--update-existing', stdout=stdout, stderr=stderr)

        assert Ingredient.objects.count() == initial_ingredient_count # No new ingredients
        assert Nutrient.objects.count() == initial_nutrient_count # No new nutrients if FDC IDs are the same
        assert IngredientNutrientLink.objects.count() == initial_link_count # Links are deleted and recreated for updated ingredient
        assert FoodPortion.objects.count() == initial_portion_count # Portions are updated based on FDC Portion ID

        updated_tofu = Ingredient.objects.get(fdc_id=-1)
        assert updated_tofu.name == "Tofu, raw (Updated)"

        protein_nutrient = Nutrient.objects.get(fdc_nutrient_id=1003)
        updated_protein_link = IngredientNutrientLink.objects.get(ingredient=updated_tofu, nutrient=protein_nutrient)
        assert updated_protein_link.amount_per_100_units == 15.0

        energy_nutrient = Nutrient.objects.get(fdc_nutrient_id=1008) # Energy
        updated_energy_link = IngredientNutrientLink.objects.get(ingredient=updated_tofu, nutrient=energy_nutrient)
        assert updated_energy_link.amount_per_100_units == 137.0


        updated_cup_portion = FoodPortion.objects.get(ingredient=updated_tofu, fdc_portion_id=-101)
        assert updated_cup_portion.gram_weight == 130.0
        
        # Check that no errors were written to stderr
        assert stderr.getvalue() == ""

    def test_import_without_update_existing_skips(self, temp_json_file):
        stdout = StringIO()
        stderr = StringIO()

        # First import (creates the ingredient)
        call_command('import_fdc_foundational', str(temp_json_file), stdout=stdout, stderr=stderr)
        assert Ingredient.objects.count() == 1
        tofu_ingredient = Ingredient.objects.get(fdc_id=-1)
        original_name = tofu_ingredient.name
        original_protein_amount = IngredientNutrientLink.objects.get(ingredient=tofu_ingredient, nutrient__fdc_nutrient_id=1003).amount_per_100_units


        # Modify the JSON file
        updated_data = json.loads(MY_FOODS_JSON_CONTENT)
        updated_data[0]['description'] = "Tofu, raw (Should Not Update Name)"
        updated_data[0]['foodNutrients'][2]['amount'] = 99.99 # Protein, should not update amount
        
        with open(temp_json_file, 'w') as f:
            json.dump(updated_data, f)

        # Second import WITHOUT --update-existing
        call_command('import_fdc_foundational', str(temp_json_file), stdout=stdout, stderr=stderr)
        
        # Assert counts haven't changed beyond the first import
        assert Ingredient.objects.count() == 1
        assert Nutrient.objects.count() == 76 
        assert IngredientNutrientLink.objects.filter(ingredient__fdc_id=-1).count() == 76
        assert FoodPortion.objects.filter(ingredient__fdc_id=-1).count() == 2

        # Assert that the ingredient was NOT updated
        skipped_tofu = Ingredient.objects.get(fdc_id=-1)
        assert skipped_tofu.name == original_name 
        
        skipped_protein_link = IngredientNutrientLink.objects.get(ingredient=skipped_tofu, nutrient__fdc_nutrient_id=1003)
        assert skipped_protein_link.amount_per_100_units == original_protein_amount

        # Check that no errors were written to stderr
        assert stderr.getvalue() == ""
        # Check stdout for skip message
        output = stdout.getvalue()
        assert f'Skipped existing Ingredient: "Tofu, raw (Should Not Update Name)" (FDC ID: -1)' in output


    def test_delete_before_import_clears_data(self, temp_json_file):
        stdout = StringIO()
        stderr = StringIO()

        # First import to populate some data
        call_command('import_fdc_foundational', str(temp_json_file), stdout=StringIO(), stderr=StringIO())
        assert Ingredient.objects.count() > 0
        assert Nutrient.objects.count() > 0
        assert IngredientNutrientLink.objects.count() > 0
        assert FoodPortion.objects.count() > 0
        
        # Import with delete flag
        call_command('import_fdc_foundational', str(temp_json_file), '--delete-before-import', stdout=stdout, stderr=stderr)

        # Data should be only what's in temp_json_file
        assert Ingredient.objects.count() == 1 
        assert Nutrient.objects.count() == 76 
        assert IngredientNutrientLink.objects.count() == 76
        assert FoodPortion.objects.count() == 2

        output = stdout.getvalue()
        assert "Deleting existing data as per --delete-before-import flag..." in output
        assert "Existing data deleted." in output
        assert stderr.getvalue() == ""

    def test_malformed_json_file(self, tmp_path):
        malformed_file = tmp_path / "malformed.json"
        with open(malformed_file, 'w') as f:
            f.write("[{'fdcId': 1, 'description': 'bad json'}]") # Single quotes are invalid

        with pytest.raises(CommandError) as excinfo:
            call_command('import_fdc_foundational', str(malformed_file))
        assert "Error decoding JSON" in str(excinfo.value)

    def test_missing_json_file(self):
        with pytest.raises(CommandError) as excinfo:
            call_command('import_fdc_foundational', 'non_existent_file.json')
        assert "not found" in str(excinfo.value)

    def test_import_nutrient_name_unit_update(self, temp_json_file):
        stdout = StringIO()
        stderr = StringIO()

        # Initial import
        call_command('import_fdc_foundational', str(temp_json_file), '--update-existing', stdout=stdout, stderr=stderr)
        
        nutrient_to_update = Nutrient.objects.get(fdc_nutrient_id=1051) # Water
        assert nutrient_to_update.name == "Water"
        assert nutrient_to_update.unit == "g"

        # Modify the JSON to change nutrient name/unit for an existing FDC ID
        updated_data = json.loads(MY_FOODS_JSON_CONTENT)
        updated_data[0]['foodNutrients'][0]['nutrient']['name'] = "Agua" # Water -> Agua
        updated_data[0]['foodNutrients'][0]['nutrient']['unitName'] = "gramos" # g -> gramos
        
        with open(temp_json_file, 'w') as f:
            json.dump(updated_data, f)

        call_command('import_fdc_foundational', str(temp_json_file), '--update-existing', stdout=stdout, stderr=stderr)

        updated_nutrient = Nutrient.objects.get(fdc_nutrient_id=1051)
        assert updated_nutrient.name == "Agua"
        assert updated_nutrient.unit == "gramos"
        assert stderr.getvalue() == "" 