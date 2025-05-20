import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.management.commands.NutrientProcessorFactory import NutrientProcessorFactory
from api.models import Nutrient, Ingredient, IngredientNutrientLink, FoodPortion
import abc # Added for Abstract Base Class

# Conversion factor for kJ to kcal
KCAL_PER_KJ = 1 / 4.184

# --- Nutrient Processor Classes ---

class BaseNutrientProcessor(abc.ABC):
    """
    Abstract base class for nutrient processors.
    Each processor handles the logic for a specific type of nutrient or a default case.
    """
    def __init__(self, command_stdout, command_stderr, update_existing_flag):
        self.stdout = command_stdout
        self.stderr = command_stderr
        self.update_existing = update_existing_flag

    @abc.abstractmethod
    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        """
        Processes the given nutrient data.

        Args:
            nutrient_data_from_fdc (dict): The nutrient block from FDC JSON (e.g., food_nutrient['nutrient']).
            food_item_description (str): Description of the food item for logging.
            original_amount_from_fdc (float): The original amount of the nutrient from FDC.

        Returns:
            tuple: (Nutrient_obj_or_None, final_amount_or_None, created_flag, updated_flag, skipped_flag)
                   - Nutrient_obj_or_None: The Django Nutrient model instance, or None if skipped.
                   - final_amount_or_None: The processed amount for the nutrient link, or None if skipped.
                   - created_flag (bool): True if a new Nutrient object was created.
                   - updated_flag (bool): True if an existing Nutrient object was updated.
                   - skipped_flag (bool): True if this nutrient was skipped (e.g., unsupported unit).
        """
        pass

class EnergyNutrientProcessor(BaseNutrientProcessor):
    TARGET_FDC_ID = 1008
    TARGET_FDC_NUMBER = "208"
    TARGET_NAME = "Energy"
    TARGET_UNIT = "kcal"

    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_nutrient_name = nutrient_data_from_fdc.get('name')
        original_unit_name = nutrient_data_from_fdc.get('unitName')
        current_amount = float(original_amount_from_fdc)
        created_nutrient = False
        updated_nutrient = False
        skipped = False

        if original_unit_name.lower() == "kj":
            current_amount = original_amount_from_fdc * KCAL_PER_KJ
            self.stdout.write(f'Converted Energy ({original_nutrient_name}) for "{food_item_description}": {original_amount_from_fdc} kJ -> {current_amount:.2f} kcal')
        elif original_unit_name.lower() == "kcal":
            pass # Amount is already in kcal
        else:
            self.stdout.write(self.stdout.style.WARNING(
                f'Energy variant ({original_nutrient_name}) for "{food_item_description}" has an unsupported unit: {original_unit_name}. Amount {original_amount_from_fdc} not converted. Skipping link.'
            ))
            return None, None, False, False, True # Skipped

        nutrient_obj, created = Nutrient.objects.get_or_create(
            name=self.TARGET_NAME,
            defaults={
                'unit': self.TARGET_UNIT,
                'fdc_nutrient_id': self.TARGET_FDC_ID,
                'fdc_nutrient_number': self.TARGET_FDC_NUMBER,
            }
        )
        created_nutrient = created
        if created:
            self.stdout.write(
                f'Created canonical Nutrient: "{nutrient_obj.name}" (Unit: {nutrient_obj.unit}, FDC ID: {nutrient_obj.fdc_nutrient_id})'
            )
        else: # Check if update is needed for the found canonical energy nutrient
            needs_save = False
            if nutrient_obj.unit != self.TARGET_UNIT:
                nutrient_obj.unit = self.TARGET_UNIT; needs_save = True
            if nutrient_obj.fdc_nutrient_id != self.TARGET_FDC_ID: # Should ideally not happen if name is unique key
                nutrient_obj.fdc_nutrient_id = self.TARGET_FDC_ID; needs_save = True
            if nutrient_obj.fdc_nutrient_number != self.TARGET_FDC_NUMBER:
                nutrient_obj.fdc_nutrient_number = self.TARGET_FDC_NUMBER; needs_save = True
            
            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(
                    f'Updated canonical Nutrient: "{nutrient_obj.name}" to ensure (Unit: {nutrient_obj.unit}, FDC ID: {nutrient_obj.fdc_nutrient_id})'
                )
        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped

class CholineNutrientProcessor(BaseNutrientProcessor):
    TARGET_FDC_ID = 1180
    TARGET_FDC_NUMBER = "421"
    TARGET_NAME = "Choline, total"
    TARGET_UNIT = "mg"

    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_fdc_number = str(nutrient_data_from_fdc.get('number'))
        # original_unit_name = nutrient_data_from_fdc.get('unitName') # Assumed 'mg' for Choline variants
        current_amount = float(original_amount_from_fdc) # No unit conversion needed for Choline (mg to mg)
        created_nutrient = False
        updated_nutrient = False
        skipped = False # Choline doesn't have skippable unit conditions here

        defaults = {
            'name': self.TARGET_NAME,
            'unit': self.TARGET_UNIT,
            'fdc_nutrient_number': self.TARGET_FDC_NUMBER,
        }
        nutrient_obj, created = Nutrient.objects.update_or_create(
            fdc_nutrient_id=self.TARGET_FDC_ID, # Use target ID for lookup and creation
            defaults=defaults
        )
        created_nutrient = created

        if created:
            self.stdout.write(
                f'Created/Mapped Choline Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Original FDC ID: {original_fdc_id})'
            )
        elif self.update_existing: # Check if update is needed for the found canonical Choline nutrient
            needs_save = False
            if nutrient_obj.name != defaults['name']:
                nutrient_obj.name = defaults['name']; needs_save = True
            if nutrient_obj.unit != defaults['unit']:
                nutrient_obj.unit = defaults['unit']; needs_save = True
            if nutrient_obj.fdc_nutrient_number != defaults['fdc_nutrient_number']:
                nutrient_obj.fdc_nutrient_number = defaults['fdc_nutrient_number']; needs_save = True
            
            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(
                    f'Updated Choline Nutrient to canonical: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Source FDC ID: {original_fdc_id})'
                )
        
        if original_fdc_id != self.TARGET_FDC_ID:
            self.stdout.write(f'Mapped Choline variant (ID: {original_fdc_id}, Num: {original_fdc_number}) to target Choline (ID: {self.TARGET_FDC_ID})')
            
        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped

class DefaultNutrientProcessor(BaseNutrientProcessor):
    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_name = nutrient_data_from_fdc.get('name')
        original_unit_name = nutrient_data_from_fdc.get('unitName')
        original_fdc_number = str(nutrient_data_from_fdc.get('number'))
        current_amount = float(original_amount_from_fdc) # No conversion for default
        created_nutrient = False
        updated_nutrient = False
        skipped = False

        defaults = {
            'name': original_name,
            'unit': original_unit_name,
            'fdc_nutrient_number': original_fdc_number,
        }
        try:
            nutrient_obj, created = Nutrient.objects.update_or_create(
                fdc_nutrient_id=original_fdc_id,
                defaults=defaults
            )
            created_nutrient = created
        except Exception as e:

            self.stderr.write(f'Error processing nutrient {original_fdc_id}{defaults} ("{original_name}"): {e}')
            return None, None, False, False, True # Skipped

        if created:
            self.stdout.write(f'Created Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id}')
        elif self.update_existing:
            needs_save = False
            # Compare all fields from defaults
            if nutrient_obj.name != defaults['name']:
                nutrient_obj.name = defaults['name']; needs_save = True
            if nutrient_obj.unit != defaults['unit']:
                nutrient_obj.unit = defaults['unit']; needs_save = True
            if nutrient_obj.fdc_nutrient_number != defaults['fdc_nutrient_number']:
                nutrient_obj.fdc_nutrient_number = defaults['fdc_nutrient_number']; needs_save = True
            
            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(f'Updated Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id}')
        
        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped

class FolateDFENutrientProcessor(BaseNutrientProcessor):
    TARGET_FDC_ID = 1190
    TARGET_FDC_NUMBER = "435"
    TARGET_NAME = "Folate, DFE"
    TARGET_UNIT = "µg" # Standard unit for Folate DFE, FDC uses μg or UG

    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_fdc_number = str(nutrient_data_from_fdc.get('number'))
        original_name = nutrient_data_from_fdc.get('name')
        # original_unit_name = nutrient_data_from_fdc.get('unitName') # Used in factory detection
        
        current_amount = float(original_amount_from_fdc)
        created_nutrient = False
        updated_nutrient = False
        skipped = False

        defaults = {
            'name': self.TARGET_NAME,
            'unit': self.TARGET_UNIT, 
            'fdc_nutrient_number': self.TARGET_FDC_NUMBER,
        }
        
        try:
            nutrient_obj, created = Nutrient.objects.update_or_create(
                fdc_nutrient_id=self.TARGET_FDC_ID, 
                defaults=defaults
            )
            created_nutrient = created
        except Exception as e:
            self.stderr.write(f'Error processing Folate, DFE nutrient (target ID {self.TARGET_FDC_ID}) from source {original_fdc_id} (\"{original_name}\"): {e}')
            return None, None, False, False, True 

        if created:
            self.stdout.write(
                f'Created/Mapped Folate, DFE Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Original FDC ID: {original_fdc_id})'
            )
        elif self.update_existing: 
            needs_save = False
            if nutrient_obj.name != defaults['name']:
                nutrient_obj.name = defaults['name']; needs_save = True
            if nutrient_obj.unit != defaults['unit']:
                nutrient_obj.unit = defaults['unit']; needs_save = True
            if nutrient_obj.fdc_nutrient_number != defaults['fdc_nutrient_number']:
                nutrient_obj.fdc_nutrient_number = defaults['fdc_nutrient_number']; needs_save = True
            
            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(
                    f'Updated Folate, DFE Nutrient to canonical: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Source FDC ID: {original_fdc_id})'
                )
        
        if original_fdc_id != self.TARGET_FDC_ID:
            self.stdout.write(f'Mapped Folate, DFE variant (ID: {original_fdc_id}, Name: "{original_name}", Num: {original_fdc_number}) to target (ID: {self.TARGET_FDC_ID})')
            
        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped


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

        if 'FoundationFoods' in data:
            food_items_list = data['FoundationFoods']
        elif isinstance(data, list):
            food_items_list = data
        else:
            raise CommandError('Could not find a list of food items. Expected a top-level key "FoundationFoods" or a direct list.')

        nutrients_created_count = 0
        nutrients_updated_count = 0
        nutrients_skipped_conversion_count = 0
        ingredients_created = 0
        ingredients_updated = 0
        links_created = 0
        links_updated = 0
        portions_created = 0
        portions_updated = 0
        portions_skipped = 0

        # Initialize the factory
        processor_factory = NutrientProcessorFactory(self.stdout, self.stderr, update_existing)

        for food_item in food_items_list:
            fdc_id_food = food_item.get('fdcId')
            description = food_item.get('description')
            food_class = food_item.get('foodClass') 

            if not fdc_id_food or not description:
                self.stdout.write(self.style.WARNING(f'Skipping food item due to missing fdcId or description: {food_item.get("fdcId", "N/A")}'))
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

            for food_nutrient_entry in food_item.get('foodNutrients', []):
                nutrient_data_block = food_nutrient_entry.get('nutrient')
                original_amount_val = food_nutrient_entry.get('amount')
                if not nutrient_data_block:
                    self.stdout.write(self.style.WARNING(f'Skipping nutrient in "{description}" due to missing nutrient data block.'))
                    continue
                
                if (nutrient_data_block.get('id') is None or 
                    nutrient_data_block.get('name') is None or 
                    nutrient_data_block.get('unitName') is None or 
                    nutrient_data_block.get('number') is None or 
                    original_amount_val is None):

                    self.stdout.write(self.style.WARNING(f'Skipping nutrient {nutrient_data_block} in "{description}" due to incomplete data (id, name, unit, number, or amount missing).'))
                    continue
                
                try:
                    current_amount_for_link = float(original_amount_val)
                except (ValueError, TypeError):
                    self.stdout.write(self.style.WARNING(f'Skipping nutrient {nutrient_data_block.get("name")} in "{description}" due to invalid amount: {original_amount_val}.'))
                    continue

                processor = processor_factory.get_processor(nutrient_data_block)
                
                nutrient_obj, final_amount, created_n, updated_n, skipped_n = processor.process(
                    nutrient_data_block, 
                    description,
                    current_amount_for_link
                )

                if created_n: nutrients_created_count += 1
                if updated_n: nutrients_updated_count += 1
                if skipped_n: nutrients_skipped_conversion_count += 1

                if nutrient_obj and final_amount is not None:
                    if final_amount > 0:  # Check if final_amount is greater than 0
                        _link_obj, created_link = IngredientNutrientLink.objects.update_or_create(
                            ingredient=ingredient_obj,
                            nutrient=nutrient_obj,
                            defaults={'amount_per_100_units': final_amount}
                        )
                        if created_link:
                            print(f'Created link for {nutrient_data_block.get("name")} in "{description}"')
                            links_created += 1
                        else:
                            links_updated += 1
                    else:
                        self.stdout.write(self.style.NOTICE(f'Skipped zero-amount nutrient link for {nutrient_data_block.get("name")} in "{description}".'))
                else:
                    if not skipped_n:
                         self.stdout.write(self.style.WARNING(f'Nutrient object or final amount was None for {nutrient_data_block.get("name")} in "{description}" after processing, but not marked skipped. Link not created.'))
            
            for portion_data in food_item.get('foodPortions', []):
                fdc_pid = portion_data.get('id')
                portion_amount = portion_data.get('amount')
                gram_weight = portion_data.get('gramWeight')
                modifier = portion_data.get('modifier')
                portion_description = portion_data.get('portionDescription')
                sequence_number = portion_data.get('sequenceNumber')
                data_points = portion_data.get('dataPoints')
                
                measure_unit_data = portion_data.get('measureUnit', {})
                mu_name = measure_unit_data.get('name')
                mu_abbr = measure_unit_data.get('abbreviation')

                if fdc_pid is None or gram_weight is None or portion_description is None:
                    self.stdout.write(self.style.WARNING(
                        f'Skipping portion for "{description}" (FDC ID: {fdc_pid}) due to missing fdc_portion_id, gram_weight, or portion_description.'
                    ))
                    portions_skipped += 1
                    continue

                portion_obj, created_portion = FoodPortion.objects.update_or_create(
                    ingredient=ingredient_obj,
                    fdc_portion_id=fdc_pid, 
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
            f'Nutrients: {nutrients_created_count} created, {nutrients_updated_count} updated, {nutrients_skipped_conversion_count} skipped (e.g. energy unit errors). \n'
            f'Ingredients: {ingredients_created} created, {ingredients_updated} updated. \n'
            f'Nutrient Links: {links_created} created, {links_updated} updated. \n'
            f'Food Portions: {portions_created} created, {portions_updated} updated, {portions_skipped} skipped.'
        )) 