import logging
from typing import Dict, Any, List, Tuple
from django.db import transaction
from .models import (
    Ingredient, 
    Nutrient, 
    IngredientNutrientLink, 
    FoodPortion, 
    IngredientFoodCategory
)
from .services import AIFoodGenerationService

logger = logging.getLogger(__name__)


class IngredientCreationDomainService:
    """
    Domain service responsible for creating ingredients from AI-generated data.
    Encapsulates business rules and coordinates with multiple models.
    """
    
    def __init__(self):
        """Initialize the domain service with required dependencies."""
        self.ai_service = AIFoodGenerationService()
    
    def create_ingredient_from_description(self, description: str, image_data: str = None) -> Ingredient:
        """
        Create a new ingredient from user description using AI generation.
        
        Args:
            description (str): User's description of the food
            image_data (str, optional): Base64 encoded image data
            
        Returns:
            Ingredient: The created ingredient instance
            
        Raises:
            Exception: If creation fails at any step
        """
        try:
            # Generate AI food data
            logger.info(f"Generating AI food data for: {description}")
            ai_food_data = self.ai_service.generate_food_data(description, image_data)
            
            # Create ingredient with all related data in a transaction
            with transaction.atomic():
                ingredient = self._create_ingredient_from_ai_data(ai_food_data)
                self._create_nutrient_links(ingredient, ai_food_data['foodNutrients'])
                self._create_food_portions(ingredient, ai_food_data['foodPortions'])
                
            logger.info(f"Successfully created ingredient: {ingredient.name} (ID: {ingredient.id})")
            return ingredient
            
        except Exception as e:
            logger.error(f"Failed to create ingredient from description '{description}': {e}")
            raise
    
    def _create_ingredient_from_ai_data(self, ai_data: Dict[str, Any]) -> Ingredient:
        """
        Create an Ingredient instance from AI-generated data.
        
        Args:
            ai_data (Dict[str, Any]): AI-generated food data
            
        Returns:
            Ingredient: The created ingredient instance
        """
        # Map food category description to our enum if possible
        category = self._map_food_category(ai_data.get('foodCategory', {}).get('description', ''))
        
        ingredient = Ingredient.objects.create(
            name=ai_data['description'],
            fdc_id=ai_data['fdcId'],
            food_class=ai_data['foodClass'],  # Should be 'ChatGPT'
            category=category,
            base_unit_for_nutrition='g',  # Standard for AI-generated foods
            notes=f"AI-generated ingredient. Original category: {ai_data.get('foodCategory', {}).get('description', 'Unknown')}"
        )
        
        return ingredient
    
    def _map_food_category(self, ai_category: str) -> str:
        """
        Map AI-generated food category to our IngredientFoodCategory enum.
        
        Args:
            ai_category (str): AI-generated category description
            
        Returns:
            str: Mapped category or None if no good match
        """
        ai_category_lower = ai_category.lower()
        
        # Define mapping rules
        category_mappings = {
            'poultry': IngredientFoodCategory.PROTEIN_ANIMAL,
            'meat': IngredientFoodCategory.PROTEIN_ANIMAL,
            'fish': IngredientFoodCategory.PROTEIN_ANIMAL,
            'seafood': IngredientFoodCategory.PROTEIN_ANIMAL,
            'dairy': IngredientFoodCategory.DAIRY,
            'milk': IngredientFoodCategory.DAIRY,
            'cheese': IngredientFoodCategory.DAIRY,
            'legume': IngredientFoodCategory.LEGUME,
            'bean': IngredientFoodCategory.LEGUME,
            'lentil': IngredientFoodCategory.LEGUME,
            'grain': IngredientFoodCategory.GRAIN_CEREAL,
            'cereal': IngredientFoodCategory.GRAIN_CEREAL,
            'bread': IngredientFoodCategory.GRAIN_CEREAL,
            'vegetable': IngredientFoodCategory.VEGETABLE_FRUITING,  # Default vegetable type
            'fruit': IngredientFoodCategory.FRUIT,
            'nut': IngredientFoodCategory.NUT_SEED,
            'seed': IngredientFoodCategory.NUT_SEED,
            'oil': IngredientFoodCategory.OIL_FAT,
            'fat': IngredientFoodCategory.OIL_FAT,
            'spice': IngredientFoodCategory.SPICE_HERB,
            'herb': IngredientFoodCategory.SPICE_HERB,
            'beverage': IngredientFoodCategory.BEVERAGE,
            'drink': IngredientFoodCategory.BEVERAGE,
        }
        
        for keyword, category in category_mappings.items():
            if keyword in ai_category_lower:
                return category
        
        # Default to OTHER if no match found
        return IngredientFoodCategory.OTHER
    
    def _create_nutrient_links(self, ingredient: Ingredient, ai_nutrients: List[Dict[str, Any]]) -> List[IngredientNutrientLink]:
        """
        Create IngredientNutrientLink instances from AI-generated nutrient data.
        
        Args:
            ingredient (Ingredient): The ingredient to link nutrients to
            ai_nutrients (List[Dict[str, Any]]): AI-generated nutrient data
            
        Returns:
            List[IngredientNutrientLink]: Created nutrient links
        """
        nutrient_links = []
        nutrient_mapping = self.ai_service.get_nutrient_mapping_for_database()
        
        for ai_nutrient in ai_nutrients:
            try:
                fdc_nutrient_id = str(ai_nutrient['nutrient']['id'])
                amount = float(ai_nutrient['amount'])
                
                # Find the corresponding nutrient in our database
                if fdc_nutrient_id in nutrient_mapping:
                    nutrient_id = nutrient_mapping[fdc_nutrient_id]
                    nutrient = Nutrient.objects.get(id=nutrient_id)
                    
                    # Create the link
                    link = IngredientNutrientLink.objects.create(
                        ingredient=ingredient,
                        nutrient=nutrient,
                        amount_per_100_units=amount
                    )
                    nutrient_links.append(link)
                    
                else:
                    logger.warning(f"No mapping found for FDC nutrient ID {fdc_nutrient_id}")
                    
            except (KeyError, ValueError, Nutrient.DoesNotExist) as e:
                logger.error(f"Failed to create nutrient link for {ai_nutrient}: {e}")
                continue
        
        logger.info(f"Created {len(nutrient_links)} nutrient links for ingredient {ingredient.name}")
        return nutrient_links
    
    def _create_food_portions(self, ingredient: Ingredient, ai_portions: List[Dict[str, Any]]) -> List[FoodPortion]:
        """
        Create FoodPortion instances from AI-generated portion data.
        
        Args:
            ingredient (Ingredient): The ingredient to create portions for
            ai_portions (List[Dict[str, Any]]): AI-generated portion data
            
        Returns:
            List[FoodPortion]: Created food portions
        """
        food_portions = []
        
        for i, ai_portion in enumerate(ai_portions):
            try:
                portion = FoodPortion.objects.create(
                    ingredient=ingredient,
                    fdc_portion_id=ai_portion.get('id'),
                    amount=float(ai_portion.get('amount', 1.0)),
                    portion_description=ai_portion.get('portionDescription', f"{ai_portion.get('amount', 1)} g"),
                    gram_weight=float(ai_portion.get('gramWeight', 100.0)),
                    modifier=ai_portion.get('modifier', ''),
                    measure_unit_name=ai_portion.get('measureUnit', {}).get('name', 'g'),
                    measure_unit_abbreviation=ai_portion.get('measureUnit', {}).get('abbreviation', 'g'),
                    sequence_number=ai_portion.get('sequenceNumber', i + 1),
                    data_points=None  # AI-generated, so no real data points
                )
                food_portions.append(portion)
                
            except (KeyError, ValueError) as e:
                logger.error(f"Failed to create food portion for {ai_portion}: {e}")
                continue
        
        logger.info(f"Created {len(food_portions)} food portions for ingredient {ingredient.name}")
        return food_portions
    
    def validate_ingredient_uniqueness(self, description: str) -> Tuple[bool, str]:
        """
        Check if an ingredient with similar description already exists.
        
        Args:
            description (str): Description to check
            
        Returns:
            Tuple[bool, str]: (is_unique, message)
        """
        # Check for exact matches first
        if Ingredient.objects.filter(name__iexact=description).exists():
            return False, f"An ingredient with the exact name '{description}' already exists."
        
        # Check for similar names (this could be enhanced with fuzzy matching)
        similar = Ingredient.objects.filter(name__icontains=description)[:5]
        if similar.exists():
            similar_names = [ing.name for ing in similar]
            return True, f"Similar ingredients found: {', '.join(similar_names)}"
        
        return True, "No similar ingredients found." 