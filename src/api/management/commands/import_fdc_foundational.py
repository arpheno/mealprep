import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.management.commands.fdc_data_schemas import FoundationFoodItemSchema, FoundationFoodsFileSchema, NutrientSchema as FdcNutrientSchema
# from .NutrientProcessorFactory import NutrientProcessorFactory # Removed
# from .FdcNutrientLinker import FdcNutrientLinker # Removed
from api.models import Nutrient, Ingredient, IngredientNutrientLink, FoodPortion
from pydantic import ValidationError

# Conversion factor for kJ to kcal
KCAL_PER_KJ = 1 / 4.184 # Removed as no longer used in this script directly

blocklist_fdc_ids = [
    1051, # "Water",
    1002, # "Nitrogen",
    1009, # "Starch",
    2038,
    2047,2048,2058,2065,1007,
    1127,1131,1130,1129,1125,1128, #Tocopherols
    1272,1278,1276,1271,#PUFA
    1259,1260,1261,1262,1263,1264,1265,1266,1267,#SFA
    1125,1226,1228,1268,1269,1270,1275,1279,1018,1057,1058,1177,1186,1187,1242,1246,1268,1269,1270,
    1280,1301,1312,1292,1293,1321,1304,1273,1108,
    1107,1013,1313,1299,1085,2026,2025,2024,2023,2010,2016,2018,2020,2009,2012,2022,1199,1196,
    1409,1411,135,1414,1334,1194,1316,1404,1300,1258,1323,1333,1012,1120,1122,1123,2014,
    1329,1330,1331,1317,1062,1075,1010,1011,1014,1126,
    1311,1314,1406,1306,1305,1277,1198,1050,1195,1197,1406,
    1210,1211,1215,1217,1218,1222,1224,1225,126,1212,1213,1214,1216,1219,1220,1221,1223,1227,1084,1082,
    1405,1105,1303,1315,1113,1112,1335,2019,1257,1119,1121,1160,1161,1159,2028,2032,2019
]
class Command(BaseCommand):
    help = 'Imports Foundational Foods data from a FoodData Central JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the FDC JSON file to import.')
        parser.add_argument(
            '--update-existing', 
            action='store_true',
            help='Update existing ingredients, nutrients and portions if found by FDC ID, otherwise skip ingredients.'
        )
        parser.add_argument(
            '--delete-before-import',
            action='store_true',
            help='USE WITH CAUTION. Deletes ALL FoodPortion, IngredientNutrientLink, Ingredient, and Nutrient records before importing.'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        json_file_path = options['json_file']
        update_existing = options['update_existing']
        delete_before_import = options['delete_before_import']

        self.stdout.write(self.style.SUCCESS(f'Starting import from {json_file_path}'))

        if delete_before_import:
            self.stdout.write(self.style.WARNING('Deleting existing data as per --delete-before-import flag...'))
            FoodPortion.objects.all().delete()
            IngredientNutrientLink.objects.all().delete()
            Ingredient.objects.all().delete()
            self.stdout.write(self.style.WARNING(
                'Nutrient records are NOT deleted by default with --delete-before-import to protect canonical nutrient list. \n'
                'They will be updated if --update-existing is also specified.'
            ))

        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'JSON file "{json_file_path}" not found.')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from "{json_file_path}". Make sure it is valid JSON.')

        food_items_list: list[FoundationFoodItemSchema] = []
        try:
            if isinstance(data, list):
                food_items_list = [FoundationFoodItemSchema(**item) for item in data]
            elif isinstance(data, dict) and len(data) == 1:
                food_items_list = [FoundationFoodItemSchema(**item) for item in data[list(data.keys())[0]]]
            else:
                raise CommandError(
                    'Could not find a list of food items. Expected a top-level key "FoundationFoods" or a direct list of food items in the JSON.'
                )
        except ValidationError as e:
            self.stderr.write(self.style.ERROR(f'JSON data validation failed:'))
            for error in e.errors():
                self.stderr.write(self.style.ERROR(f"  Error at {'.'.join(map(str, error['loc']))}: {error['msg']}"))
            raise CommandError('JSON data does not match the expected schema. See errors above.')

        nutrients_skipped_not_found_count = 0
        ingredients_created = 0
        ingredients_updated = 0
        links_created = 0
        links_updated = 0
        portions_created = 0
        portions_updated = 0


        for food_item in food_items_list:
            fdc_id_food = food_item.fdcId
            description = food_item.description
            food_class = food_item.foodClass

            if not fdc_id_food or not description:
                self.stdout.write(self.style.WARNING(f'Skipping food item due to missing fdcId or description: {food_item.fdcId if food_item.fdcId else "N/A"}'))
                continue

            try:
                ingredient_obj, created_ingredient = Ingredient.objects.get_or_create(
                    fdc_id=fdc_id_food,
                    defaults={
                        'name': description,
                        'food_class': food_class,
                    }
                )
                if created_ingredient:
                    ingredients_created += 1
                elif update_existing:
                    ingredient_obj.name = description
                    ingredient_obj.food_class = food_class
                    ingredient_obj.save()
                    ingredients_updated += 1
                else: 
                    self.stdout.write(f'Skipped existing Ingredient (no update): "{description}" (FDC ID: {fdc_id_food})')
                    continue
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error processing ingredient {fdc_id_food} ("{description}"): {e}'))
                continue

            if not created_ingredient and update_existing:
                IngredientNutrientLink.objects.filter(ingredient=ingredient_obj).delete()

            for food_nutrient_entry in food_item.foodNutrients:
                nutrient_data_block = food_nutrient_entry.nutrient # This is NutrientSchema
                
                if nutrient_data_block.id is None:
                    self.stdout.write(self.style.WARNING(
                        f'Skipping nutrient ({nutrient_data_block.name if nutrient_data_block.name else "Unknown Name"}) in "{description}" because its FDC ID is missing in the (already filtered) nutrient data.'
                    ))
                    nutrients_skipped_not_found_count += 1 # Count as 'not found' or 'skipped due to bad data'
                    continue
                
                try:
                    nutrient_obj = Nutrient.objects.get(fdc_nutrient_id=nutrient_data_block.id)
                    # Logging for found nutrient can be kept if desired, or removed for less verbosity
                    # self.stdout.write(self.style.SUCCESS( f'Found nutrient "{nutrient_obj.name}" (DB FDC ID: {nutrient_obj.fdc_nutrient_id}) for input FDC ID {nutrient_data_block.id}'))
                except Nutrient.DoesNotExist:
                    if nutrient_data_block.id in blocklist_fdc_ids:
                        continue
                    self.stdout.write(self.style.WARNING( f'Nutrient with FDC ID {nutrient_data_block.id} (Name: {nutrient_data_block.name if nutrient_data_block.name else "N/A"}) not found in authoritative database. Omitting linkage for "{description}".'))
                    nutrients_skipped_not_found_count += 1
                    continue
                except Exception as e: # Catch other potential errors during DB lookup
                    self.stderr.write(self.style.ERROR( f'Error looking up nutrient with FDC ID {nutrient_data_block.id} for "{description}": {e}'))
                    # Depending on desired error handling, you might re-raise, or just count as skipped and continue
                    nutrients_skipped_not_found_count += 1
                    continue 
                
                # food_nutrient_entry.amount is now guaranteed by Pydantic validation (due to the pre-filter) to be a float.
                if food_nutrient_entry.amount > 0:
                    _link_obj, created_link = IngredientNutrientLink.objects.update_or_create(
                        ingredient=ingredient_obj,
                        nutrient=nutrient_obj,
                        defaults={'amount_per_100_units': food_nutrient_entry.amount}
                    )
                    if created_link:
                        links_created += 1
                    else:
                        links_updated += 1
            
            for portion_data in food_item.foodPortions:
                fdc_pid = portion_data.id
                portion_amount = portion_data.amount
                gram_weight = portion_data.gramWeight
                modifier = portion_data.modifier
                portion_description = portion_data.portionDescription
                sequence_number = portion_data.sequenceNumber
                data_points = portion_data.dataPoints
                
                mu_name = portion_data.measureUnit.name if portion_data.measureUnit else None
                mu_abbr = portion_data.measureUnit.abbreviation if portion_data.measureUnit else None

                # This explicit check is no longer strictly necessary for id and gramWeight
                # as Pydantic will raise an error during initial parsing if they are missing
                # and the new model_validator in FoundationFoodItemSchema will filter & log them.
                # However, we might keep a general skip for other potential issues or rely on Pydantic's earlier filtering.
                # For now, let's assume Pydantic validation handles the mandatory fields correctly before this loop.
                # If a portion_data makes it here, its `id` and `gramWeight` should be valid due to schema enforcement.

                portion_obj, created_portion = FoodPortion.objects.update_or_create(
                    ingredient=ingredient_obj,
                    fdc_portion_id=fdc_pid, # fdc_pid here is portion_data.id
                    defaults={
                        'amount': portion_amount,
                        'gram_weight': gram_weight,
                        'modifier': modifier,
                        'portion_description': portion_description,
                        'sequence_number': sequence_number,
                        'data_points': data_points,
                        'measure_unit_name': mu_name,
                        'measure_unit_abbreviation': mu_abbr,
                    }
                )
                if created_portion:
                    portions_created += 1
                else: 
                    portions_updated += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Import finished. \n'
            f'Nutrients: Handled {food_item.foodNutrients.__len__()} entries per food item (approx). Links skipped due to nutrient not in DB or missing FDC ID: {nutrients_skipped_not_found_count}. \n'
            f'Ingredients: {ingredients_created} created, {ingredients_updated} updated. \n'
            f'Nutrient Links: {links_created} created, {links_updated} updated. \n'
            f'Food Portions: {portions_created} created, {portions_updated} updated. (Invalid portions are logged and discarded during initial data validation).'
        ))

        self.stdout.write(self.style.SUCCESS('\n--- All Stored Nutrients (ID: Name) ---'))
        all_nutrients = Nutrient.objects.all().order_by('fdc_nutrient_id')
        if all_nutrients:
            for nutrient in all_nutrients:
                self.stdout.write(f'{nutrient.fdc_nutrient_id}: {nutrient.name} ({nutrient.unit})')
        else:
            self.stdout.write('No nutrients found in the database.')
        self.stdout.write(self.style.SUCCESS('--- End of Nutrient Listing ---')) 