import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from api.models import Ingredient, IngredientNutrientLink, FoodPortion


class Command(BaseCommand):
    """
    Management command to export all ChatGPT-generated foods to JSON.
    
    This allows version control of custom AI-generated food data separately
    from the main USDA FDC database imports.
    """
    
    help = 'Export all ChatGPT-generated foods to JSON for version control'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-file',
            type=str,
            default='data/chatgpt_foods.json',
            help='Output file path (default: data/chatgpt_foods.json)'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            help='Pretty print JSON output with indentation'
        )
        parser.add_argument(
            '--include-metadata',
            action='store_true',
            help='Include export metadata in the output'
        )

    def handle(self, *args, **options):
        """
        Export ChatGPT foods to JSON file.
        
        Args:
            *args: Command line arguments
            **options: Command options
        """
        output_file = options['output_file']
        pretty_print = options['pretty']
        include_metadata = options['include_metadata']
        
        try:
            # Query all ChatGPT-generated ingredients
            chatgpt_ingredients = Ingredient.objects.filter(
                food_class='ChatGPT'
            ).prefetch_related(
                'ingredientnutrientlink_set__nutrient',
                'food_portions'
            ).order_by('id')
            
            if not chatgpt_ingredients.exists():
                self.stdout.write(
                    self.style.WARNING('No ChatGPT-generated ingredients found.')
                )
                return
            
            # Build export data structure
            export_data = []
            
            for ingredient in chatgpt_ingredients:
                ingredient_data = self._serialize_ingredient(ingredient)
                export_data.append(ingredient_data)
            
            # Prepare final output
            if include_metadata:
                final_output = {
                    "metadata": {
                        "export_timestamp": datetime.now().isoformat(),
                        "total_ingredients": len(export_data),
                        "export_version": "1.0",
                        "description": "ChatGPT-generated food database entries"
                    },
                    "ingredients": export_data
                }
            else:
                final_output = export_data
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                if pretty_print:
                    json.dump(final_output, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(final_output, f, ensure_ascii=False)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully exported {len(export_data)} ChatGPT ingredients to {output_file}'
                )
            )
            
        except Exception as e:
            raise CommandError(f'Export failed: {str(e)}')

    def _serialize_ingredient(self, ingredient):
        """
        Serialize an ingredient to JSON format.
        
        Args:
            ingredient (Ingredient): The ingredient to serialize
            
        Returns:
            dict: Serialized ingredient data
        """
        # Get nutrient data
        nutrient_links = ingredient.ingredientnutrientlink_set.all()
        food_nutrients = []
        
        for link in nutrient_links:
            nutrient_data = {
                "nutrient": {
                    "id": link.nutrient.fdc_nutrient_id or -1,  # Use FDC ID if available
                    "name": link.nutrient.name,
                    "unitName": link.nutrient.unit
                },
                "amount": float(link.amount_per_100_units)
            }
            food_nutrients.append(nutrient_data)
        
        # Get food portions
        portions = ingredient.food_portions.all()
        food_portions = []
        
        for portion in portions:
            portion_data = {
                "id": portion.fdc_portion_id or -1,
                "amount": float(portion.amount),
                "gramWeight": float(portion.gram_weight),
                "modifier": portion.modifier or "",
                "portionDescription": portion.portion_description,
                "sequenceNumber": portion.sequence_number or 1,
                "measureUnit": {
                    "id": -1,  # No real measure unit ID for AI-generated
                    "name": portion.measure_unit_name or "g",
                    "abbreviation": portion.measure_unit_abbreviation or "g"
                }
            }
            food_portions.append(portion_data)
        
        # Build ingredient data
        ingredient_data = {
            "fdcId": ingredient.fdc_id,
            "description": ingredient.name,
            "foodClass": ingredient.food_class,
            "foodCategory": {
                "description": ingredient.get_category_display() if ingredient.category else "Unknown",
                "code": ingredient.category or "OTHER",
                "id": -1
            },
            "foodNutrients": food_nutrients,
            "foodPortions": food_portions,
            "notes": ingredient.notes or "",
            "createdAt": ingredient.id,  # Use ID as creation indicator since we don't have timestamp
            "baseUnit": ingredient.base_unit_for_nutrition
        }
        
        return ingredient_data 