import json
import os
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.models import Ingredient, Nutrient, IngredientNutrientLink, FoodPortion
from api.domain_services import IngredientCreationDomainService


class Command(BaseCommand):
    """
    Management command to import ChatGPT-generated foods from JSON.
    
    This allows teams to sync AI-generated food data from version control.
    """
    
    help = 'Import ChatGPT-generated foods from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            help='Path to JSON file containing ChatGPT foods'
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing ingredients instead of skipping them'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without actually importing'
        )

    def handle(self, *args, **options):
        """
        Import ChatGPT foods from JSON file.
        
        Args:
            *args: Command line arguments
            **options: Command options
        """
        json_file = options['json_file']
        update_existing = options['update_existing']
        dry_run = options['dry_run']
        
        if not os.path.exists(json_file):
            raise CommandError(f'JSON file not found: {json_file}')
        
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both metadata format and direct array format
            if isinstance(data, dict) and 'ingredients' in data:
                ingredients_data = data['ingredients']
                metadata = data.get('metadata', {})
                self.stdout.write(f"Import metadata: {metadata}")
            else:
                ingredients_data = data
            
            if not isinstance(ingredients_data, list):
                raise CommandError('JSON data must be a list of ingredients or object with "ingredients" key')
            
            if dry_run:
                self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
            
            imported_count = 0
            updated_count = 0
            skipped_count = 0
            
            for ingredient_data in ingredients_data:
                try:
                    result = self._import_ingredient(ingredient_data, update_existing, dry_run)
                    if result == 'imported':
                        imported_count += 1
                    elif result == 'updated':
                        updated_count += 1
                    elif result == 'skipped':
                        skipped_count += 1
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'Failed to import ingredient {ingredient_data.get("description", "Unknown")}: {e}'
                        )
                    )
                    continue
            
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'DRY RUN COMPLETE: Would import {imported_count}, update {updated_count}, skip {skipped_count} ingredients'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Import complete: {imported_count} imported, {updated_count} updated, {skipped_count} skipped'
                    )
                )
                
        except json.JSONDecodeError as e:
            raise CommandError(f'Invalid JSON file: {e}')
        except Exception as e:
            raise CommandError(f'Import failed: {str(e)}')

    def _import_ingredient(self, ingredient_data, update_existing, dry_run):
        """
        Import a single ingredient from JSON data.
        
        Args:
            ingredient_data (dict): Ingredient data from JSON
            update_existing (bool): Whether to update existing ingredients
            dry_run (bool): Whether this is a dry run
            
        Returns:
            str: 'imported', 'updated', or 'skipped'
        """
        description = ingredient_data.get('description')
        fdc_id = ingredient_data.get('fdcId')
        
        if not description:
            raise ValueError('Ingredient description is required')
        
        # Check if ingredient already exists
        existing = None
        if fdc_id:
            existing = Ingredient.objects.filter(fdc_id=fdc_id).first()
        
        if not existing:
            existing = Ingredient.objects.filter(name=description).first()
        
        if existing:
            if not update_existing:
                self.stdout.write(f'Skipping existing ingredient: {description}')
                return 'skipped'
            
            if dry_run:
                self.stdout.write(f'Would update existing ingredient: {description}')
                return 'updated'
            
            # Update existing ingredient
            return self._update_ingredient(existing, ingredient_data)
        else:
            if dry_run:
                self.stdout.write(f'Would import new ingredient: {description}')
                return 'imported'
            
            # Create new ingredient
            return self._create_ingredient(ingredient_data)

    def _create_ingredient(self, ingredient_data):
        """
        Create a new ingredient from JSON data.
        
        Args:
            ingredient_data (dict): Ingredient data from JSON
            
        Returns:
            str: 'imported'
        """
        domain_service = IngredientCreationDomainService()
        
        with transaction.atomic():
            # Create basic ingredient
            ingredient = Ingredient.objects.create(
                name=ingredient_data['description'],
                fdc_id=ingredient_data.get('fdcId'),
                food_class=ingredient_data.get('foodClass', 'ChatGPT'),
                category=self._map_category_code(ingredient_data.get('foodCategory', {}).get('code')),
                base_unit_for_nutrition=ingredient_data.get('baseUnit', 'g'),
                notes=ingredient_data.get('notes', 'Imported from ChatGPT foods JSON')
            )
            
            # Create nutrient links
            for nutrient_data in ingredient_data.get('foodNutrients', []):
                self._create_nutrient_link(ingredient, nutrient_data)
            
            # Create food portions
            for portion_data in ingredient_data.get('foodPortions', []):
                self._create_food_portion(ingredient, portion_data)
        
        self.stdout.write(f'Imported ingredient: {ingredient.name}')
        return 'imported'

    def _update_ingredient(self, ingredient, ingredient_data):
        """
        Update an existing ingredient from JSON data.
        
        Args:
            ingredient (Ingredient): Existing ingredient to update
            ingredient_data (dict): New ingredient data from JSON
            
        Returns:
            str: 'updated'
        """
        with transaction.atomic():
            # Update basic fields
            ingredient.name = ingredient_data['description']
            ingredient.food_class = ingredient_data.get('foodClass', 'ChatGPT')
            ingredient.category = self._map_category_code(ingredient_data.get('foodCategory', {}).get('code'))
            ingredient.base_unit_for_nutrition = ingredient_data.get('baseUnit', 'g')
            ingredient.notes = ingredient_data.get('notes', 'Updated from ChatGPT foods JSON')
            ingredient.save()
            
            # Clear and recreate nutrient links
            ingredient.ingredientnutrientlink_set.all().delete()
            for nutrient_data in ingredient_data.get('foodNutrients', []):
                self._create_nutrient_link(ingredient, nutrient_data)
            
            # Clear and recreate food portions
            ingredient.food_portions.all().delete()
            for portion_data in ingredient_data.get('foodPortions', []):
                self._create_food_portion(ingredient, portion_data)
        
        self.stdout.write(f'Updated ingredient: {ingredient.name}')
        return 'updated'

    def _create_nutrient_link(self, ingredient, nutrient_data):
        """Create a nutrient link from JSON data."""
        nutrient_name = nutrient_data['nutrient']['name']
        fdc_nutrient_id = nutrient_data['nutrient']['id']
        amount = nutrient_data['amount']
        
        # Find nutrient by name or FDC ID
        nutrient = None
        if fdc_nutrient_id and fdc_nutrient_id > 0:
            nutrient = Nutrient.objects.filter(fdc_nutrient_id=fdc_nutrient_id).first()
        
        if not nutrient:
            nutrient = Nutrient.objects.filter_by_name_or_alias(nutrient_name).first()
        
        if nutrient:
            IngredientNutrientLink.objects.create(
                ingredient=ingredient,
                nutrient=nutrient,
                amount_per_100_units=amount
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'Nutrient not found: {nutrient_name} (FDC ID: {fdc_nutrient_id})')
            )

    def _create_food_portion(self, ingredient, portion_data):
        """Create a food portion from JSON data."""
        FoodPortion.objects.create(
            ingredient=ingredient,
            fdc_portion_id=portion_data.get('id') if portion_data.get('id', -1) > 0 else None,
            amount=portion_data.get('amount', 1.0),
            portion_description=portion_data.get('portionDescription', '100 g'),
            gram_weight=portion_data.get('gramWeight', 100.0),
            modifier=portion_data.get('modifier', ''),
            measure_unit_name=portion_data.get('measureUnit', {}).get('name', 'g'),
            measure_unit_abbreviation=portion_data.get('measureUnit', {}).get('abbreviation', 'g'),
            sequence_number=portion_data.get('sequenceNumber', 1)
        )

    def _map_category_code(self, code):
        """Map category code to enum value."""
        from api.models import IngredientFoodCategory
        
        if not code:
            return IngredientFoodCategory.OTHER
        
        # Map known codes
        code_mapping = {
            'PRO_ANIMAL': IngredientFoodCategory.PROTEIN_ANIMAL,
            'PRO_PLANT': IngredientFoodCategory.PROTEIN_PLANT,
            'GRAIN': IngredientFoodCategory.GRAIN_CEREAL,
            'LEGUME': IngredientFoodCategory.LEGUME,
            'VEG_LEAFY': IngredientFoodCategory.VEGETABLE_LEAFY,
            'VEG_ROOT': IngredientFoodCategory.VEGETABLE_ROOT,
            'VEG_FRUIT': IngredientFoodCategory.VEGETABLE_FRUITING,
            'FRUIT': IngredientFoodCategory.FRUIT,
            'NUT_SEED': IngredientFoodCategory.NUT_SEED,
            'OIL_FAT': IngredientFoodCategory.OIL_FAT,
            'DAIRY': IngredientFoodCategory.DAIRY,
            'DAIRY_ALT': IngredientFoodCategory.DAIRY_ALTERNATIVE,
            'SPICE_HERB': IngredientFoodCategory.SPICE_HERB,
            'CONDIMENT': IngredientFoodCategory.CONDIMENT_SAUCE,
            'BEVERAGE': IngredientFoodCategory.BEVERAGE,
            'OTHER': IngredientFoodCategory.OTHER,
        }
        
        return code_mapping.get(code, IngredientFoodCategory.OTHER) 