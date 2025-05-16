import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.models import Nutrient, Ingredient, IngredientNutrientLink, FoodPortion

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
            Nutrient.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing data deleted.'))

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

        nutrients_created = 0
        nutrients_updated = 0
        ingredients_created = 0
        ingredients_updated = 0
        links_created = 0
        portions_created = 0
        portions_updated = 0
        portions_skipped = 0

        for food_item in food_items_list:
            fdc_id_food = food_item.get('fdcId')
            description = food_item.get('description')
            food_class = food_item.get('foodClass') # e.g. "FinalFood"

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
                    self.stdout.write(self.style.SUCCESS(f'Created Ingredient: "{description}" (FDC ID: {fdc_id_food})'))
                elif update_existing:
                    ingredient_obj.name = description
                    ingredient_obj.food_class = food_class
                    ingredient_obj.save()
                    ingredients_updated += 1
                    self.stdout.write(f'Updated Ingredient: "{description}" (FDC ID: {fdc_id_food})')
                else: # Not created and not updating existing
                    self.stdout.write(f'Skipped existing Ingredient: "{description}" (FDC ID: {fdc_id_food})')
                    continue
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Error processing ingredient {fdc_id_food} ("{description}"): {e}'))
                continue

            if not created_ingredient and update_existing:
                IngredientNutrientLink.objects.filter(ingredient=ingredient_obj).delete()
                FoodPortion.objects.filter(ingredient=ingredient_obj).delete() # Delete old portions if updating

            for food_nutrient in food_item.get('foodNutrients', []):
                nutrient_data = food_nutrient.get('nutrient')
                if not nutrient_data:
                    self.stdout.write(self.style.WARNING(f'Skipping nutrient in "{description}" due to missing nutrient data block.'))
                    continue

                fdc_nutrient_id = nutrient_data.get('id')
                nutrient_name = nutrient_data.get('name')
                unit_name = nutrient_data.get('unitName')
                nutrient_number = nutrient_data.get('number')
                amount = food_nutrient.get('amount')

                if fdc_nutrient_id is None or nutrient_name is None or unit_name is None or amount is None:
                    self.stdout.write(self.style.WARNING(f'Skipping nutrient in "{description}" due to missing id, name, unitName, or amount.'))
                    continue
                
                nutrient_obj, created_nutrient = Nutrient.objects.get_or_create(
                    fdc_nutrient_id=fdc_nutrient_id,
                    defaults={
                        'name': nutrient_name,
                        'unit': unit_name,
                        'fdc_nutrient_number': nutrient_number,
                    }
                )

                if created_nutrient:
                    nutrients_created += 1
                elif update_existing:
                    nutrient_obj.name = nutrient_name
                    nutrient_obj.unit = unit_name
                    nutrient_obj.fdc_nutrient_number = nutrient_number
                    nutrient_obj.save()
                    nutrients_updated +=1
                
                IngredientNutrientLink.objects.create(
                    ingredient=ingredient_obj,
                    nutrient=nutrient_obj,
                    amount_per_100_units=amount
                )
                links_created += 1
            
            # Process FoodPortions
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
                    fdc_portion_id=fdc_pid, # Use FDC portion ID as part of the key
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
                else: # It was updated
                    portions_updated += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Import finished. \n'
            f'Nutrients: {nutrients_created} created, {nutrients_updated} updated. \n'
            f'Ingredients: {ingredients_created} created, {ingredients_updated} updated. \n'
            f'Nutrient Links: {links_created} created. \n'
            f'Food Portions: {portions_created} created, {portions_updated} updated, {portions_skipped} skipped.'
        )) 