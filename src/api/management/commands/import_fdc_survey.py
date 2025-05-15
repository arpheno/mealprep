import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.models import Nutrient, Ingredient, IngredientNutrientLink

class Command(BaseCommand):
    help = 'Imports FDC Survey (NHANES) Foods data from a FoodData Central JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str, help='The path to the FDC Survey JSON file to import.')
        parser.add_argument(
            '--update-existing', 
            action='store_true',
            help='Update existing ingredients and nutrients if found by FDC ID, otherwise skip.'
        )

    @transaction.atomic # Ensures all DB operations in handle are one transaction
    def handle(self, *args, **options):
        json_file_path = options['json_file']
        update_existing = options['update_existing']
        self.stdout.write(self.style.SUCCESS(f'Starting FDC Survey import from {json_file_path}'))

        try:
            with open(json_file_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'JSON file "{json_file_path}" not found.')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from "{json_file_path}". Make sure it is valid JSON.')

        if 'SurveyFoods' in data: # Common key for Survey data
            food_items_list = data['SurveyFoods']
        elif 'SRLegacyFoods' in data: # Another possible FDC key
             food_items_list = data['SRLegacyFoods']
        elif isinstance(data, list): # If the JSON file is directly an array of foods
            food_items_list = data
        else:
            raise CommandError('Could not find a list of food items. Expected a top-level key like "SurveyFoods", "SRLegacyFoods" or a direct list.')

        nutrients_created = 0
        nutrients_updated = 0
        ingredients_created = 0
        ingredients_updated = 0
        links_created = 0
        links_skipped_existing = 0

        for food_item in food_items_list:
            fdc_id_food = food_item.get('fdcId')
            description = food_item.get('description')
            # Survey data might have 'foodCategory' or 'wweiaFoodCategory' instead of 'foodClass'
            # Or it might not have a direct equivalent. Let's try 'foodCategory'.
            food_category = food_item.get('foodCategory') 
            # Other potentially relevant fields from Survey data (examples):
            # 'foodCode', 'startDate', 'endDate', 'wweiaFoodCategory.description'
            # For now, we'll stick to the basics matching Ingredient model fields.

            if not fdc_id_food or not description:
                self.stdout.write(self.style.WARNING(f'Skipping food item due to missing fdcId or description: {str(food_item)[:200]}...'))
                continue

            ingredient_obj, created_ingredient = Ingredient.objects.get_or_create(
                fdc_id=fdc_id_food,
                defaults={
                    'name': description,
                    'food_class': food_category, # Map food_category to food_class or create new field
                    # food_class is nullable, so this is fine if food_category is None
                }
            )

            if created_ingredient:
                ingredients_created += 1
                self.stdout.write(self.style.SUCCESS(f'Created Ingredient: "{description}" (FDC ID: {fdc_id_food})'))
            elif update_existing:
                ingredient_obj.name = description
                ingredient_obj.food_class = food_category
                ingredient_obj.save()
                ingredients_updated += 1
                self.stdout.write(f'Updated Ingredient: "{description}" (FDC ID: {fdc_id_food})')
            else: 
                self.stdout.write(f'Skipped existing Ingredient: "{description}" (FDC ID: {fdc_id_food})')
                # If not updating existing ingredient, we should also skip its nutrients
                # to avoid adding duplicate links if the script is run multiple times without --update-existing.
                # However, if nutrient definitions themselves could change, this might be too restrictive.
                # For now, if ingredient exists and not updating, we assume its links are also fine.
                # The original FDC Foundation import would continue and create links even if ingredient was skipped.
                # Let's adjust this to only create new links IF the ingredient was just created OR if we are updating.
                # If we are *not* updating an existing ingredient, we assume its links are up-to-date.
                if not (created_ingredient or update_existing):
                    # This means we're skipping an existing ingredient and not updating it.
                    # We should also skip creating its nutrient links if they might already exist.
                    # To be safe and avoid duplicates, let's only proceed with nutrient links if the ingredient
                    # was newly created OR if we are in update_existing mode (which clears old links).
                    num_existing_links = IngredientNutrientLink.objects.filter(ingredient=ingredient_obj).count()
                    if num_existing_links > 0:
                         self.stdout.write(f'Skipping {num_existing_links} nutrient links for existing, non-updated Ingredient: "{description}"')
                         links_skipped_existing += num_existing_links
                         continue # Skip to next food item


            # If updating an existing ingredient, clear its old nutrient links first
            # to accurately reflect the current data file's nutrient composition.
            if not created_ingredient and update_existing:
                IngredientNutrientLink.objects.filter(ingredient=ingredient_obj).delete()

            for food_nutrient in food_item.get('foodNutrients', []):
                nutrient_data = food_nutrient.get('nutrient')
                if not nutrient_data:
                    self.stdout.write(self.style.WARNING(f'Skipping nutrient in "{description}" due to missing nutrient data: {food_nutrient}'))
                    continue

                # Field names for nutrient details (id, name, unitName, number) are assumed to be the same.
                fdc_nutrient_id = nutrient_data.get('id') 
                nutrient_name = nutrient_data.get('name')
                unit_name = nutrient_data.get('unitName')
                nutrient_number = nutrient_data.get('number') # This field is often present
                amount = food_nutrient.get('amount')

                if fdc_nutrient_id is None or nutrient_name is None or unit_name is None or amount is None:
                    self.stdout.write(self.style.WARNING(f'Skipping nutrient in "{description}" due to missing id, name, unitName, or amount: {nutrient_data}'))
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
                
                # Create the link
                # Ensure we don't create duplicate links if the script logic allows reaching here 
                # for an existing ingredient without update_existing flag,
                # though the logic above tries to prevent this.
                # get_or_create for the link itself is safer.
                _link_obj, created_link = IngredientNutrientLink.objects.get_or_create(
                    ingredient=ingredient_obj,
                    nutrient=nutrient_obj,
                    defaults={'amount_per_100_units': amount}
                )
                if created_link:
                    links_created += 1
                elif update_existing: # If link exists, update its amount if --update-existing
                    _link_obj.amount_per_100_units = amount
                    _link_obj.save()
                    # We don't have a counter for updated links yet, but this is where it would go.

        self.stdout.write(self.style.SUCCESS(
            f'FDC Survey Import finished. '
            f'Nutrients: {nutrients_created} created, {nutrients_updated} updated. ' 
            f'Ingredients: {ingredients_created} created, {ingredients_updated} updated. ' 
            f'Nutrient Links: {links_created} created. ({links_skipped_existing} links skipped for existing ingredients not being updated).'
        )) 