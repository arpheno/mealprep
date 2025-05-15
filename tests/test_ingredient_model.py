import pytest
from api.models import Ingredient, Nutrient, IngredientNutrientLink, IngredientFoodCategory

@pytest.mark.django_db
class TestIngredientModel:
    def test_ingredient_creation(self):
        """Test if an ingredient can be created and retrieved properly"""
        ingredient = Ingredient.objects.create(
            name="Test Ingredient",
            fdc_id=12345,
            food_class="TestFoodClass",
            category=IngredientFoodCategory.FRUIT,
            base_unit_for_nutrition="g",
            common_purchase_unit="piece",
            purchase_unit_to_base_unit_conversion=150.0,
            notes="Test notes about this ingredient"
        )
        
        # Check if the ingredient was created correctly
        assert ingredient.name == "Test Ingredient"
        assert ingredient.fdc_id == 12345
        assert ingredient.food_class == "TestFoodClass"
        assert ingredient.category == IngredientFoodCategory.FRUIT
        assert ingredient.base_unit_for_nutrition == "g"
        assert ingredient.common_purchase_unit == "piece"
        assert ingredient.purchase_unit_to_base_unit_conversion == 150.0
        assert ingredient.notes == "Test notes about this ingredient"
        
        # Test string representation
        assert str(ingredient) == "Test Ingredient"
        
    def test_ingredient_nutrient_link(self):
        """Test creating and retrieving the many-to-many relationship between Ingredient and Nutrient"""
        # Create ingredient and nutrient
        ingredient = Ingredient.objects.create(
            name="Banana",
            category=IngredientFoodCategory.FRUIT,
            base_unit_for_nutrition="g"
        )
        
        nutrient1 = Nutrient.objects.create(
            name="Vitamin C",
            unit="mg",
            category="VITAMIN"
        )
        
        nutrient2 = Nutrient.objects.create(
            name="Potassium",
            unit="mg",
            category="MINERAL"
        )
        
        # Create the links with nutrient amounts
        link1 = IngredientNutrientLink.objects.create(
            ingredient=ingredient,
            nutrient=nutrient1,
            amount_per_100_units=8.7  # 8.7mg of Vitamin C per 100g
        )
        
        link2 = IngredientNutrientLink.objects.create(
            ingredient=ingredient,
            nutrient=nutrient2,
            amount_per_100_units=358.0  # 358mg of Potassium per 100g
        )
        
        # Test retrieval of nutrients through the relationship
        assert ingredient.nutrients.count() == 2
        assert nutrient1 in ingredient.nutrients.all()
        assert nutrient2 in ingredient.nutrients.all()
        
        # Test retrieval of the amounts
        ingredient_nutrients = {
            link.nutrient.name: link.amount_per_100_units 
            for link in ingredient.ingredientnutrientlink_set.all()
        }
        
        assert ingredient_nutrients["Vitamin C"] == 8.7
        assert ingredient_nutrients["Potassium"] == 358.0
        
    def test_food_portion_relationship(self):
        """Test the relationship between Ingredient and its FoodPortions"""
        # Create ingredient
        ingredient = Ingredient.objects.create(
            name="Apple",
            category=IngredientFoodCategory.FRUIT,
            base_unit_for_nutrition="g"
        )
        
        # Create food portions for the ingredient
        food_portion1 = ingredient.food_portions.create(
            amount=1.0,
            portion_description="1 medium apple",
            gram_weight=182.0,
            measure_unit_name="piece",
            measure_unit_abbreviation="pc"
        )
        
        food_portion2 = ingredient.food_portions.create(
            amount=1.0,
            portion_description="1 cup, sliced",
            gram_weight=110.0,
            measure_unit_name="cup",
            measure_unit_abbreviation="cup"
        )
        
        # Test retrieval of food portions
        assert ingredient.food_portions.count() == 2
        
        # Check specific portion information
        portions = list(ingredient.food_portions.all())
        apple_piece = next((p for p in portions if p.measure_unit_name == "piece"), None)
        apple_cup = next((p for p in portions if p.measure_unit_name == "cup"), None)
        
        assert apple_piece.gram_weight == 182.0
        assert apple_piece.portion_description == "1 medium apple"
        
        assert apple_cup.gram_weight == 110.0
        assert apple_cup.portion_description == "1 cup, sliced"
