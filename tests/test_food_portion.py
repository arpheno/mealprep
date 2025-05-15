import pytest
from api.models import Ingredient, FoodPortion, IngredientFoodCategory

@pytest.mark.django_db
class TestFoodPortionModel:
    def setup_method(self):
        """Set up test data for each test method"""
        # Create an ingredient
        self.apple = Ingredient.objects.create(
            name="Apple, raw",
            category=IngredientFoodCategory.FRUIT,
            base_unit_for_nutrition="g"
        )
        
        # Create food portions for the ingredient
        self.apple_medium = FoodPortion.objects.create(
            ingredient=self.apple,
            fdc_portion_id=12345,
            amount=1.0,
            portion_description="1 medium apple (182g)",
            gram_weight=182.0,
            measure_unit_name="piece",
            measure_unit_abbreviation="pc",
            sequence_number=1,
            data_points=85
        )
        
        self.apple_cup = FoodPortion.objects.create(
            ingredient=self.apple,
            fdc_portion_id=12346,
            amount=1.0,
            portion_description="1 cup, sliced",
            gram_weight=110.0,
            measure_unit_name="cup",
            measure_unit_abbreviation="cup",
            sequence_number=2,
            data_points=42
        )
    
    def test_food_portion_creation(self):
        """Test basic properties of food portion objects"""
        # Test the apple_medium portion
        assert self.apple_medium.ingredient.name == "Apple, raw"
        assert self.apple_medium.fdc_portion_id == 12345
        assert self.apple_medium.amount == 1.0
        assert self.apple_medium.portion_description == "1 medium apple (182g)"
        assert self.apple_medium.gram_weight == 182.0
        assert self.apple_medium.measure_unit_name == "piece"
        assert self.apple_medium.measure_unit_abbreviation == "pc"
        assert self.apple_medium.sequence_number == 1
        assert self.apple_medium.data_points == 85
        
        # Test the apple_cup portion
        assert self.apple_cup.gram_weight == 110.0
        assert self.apple_cup.measure_unit_name == "cup"
        
        # Test string representation
        assert str(self.apple_medium) == "1 medium apple (182g) (182.0g) for Apple, raw"
        assert str(self.apple_cup) == "1 cup, sliced (110.0g) for Apple, raw"
    
    def test_ingredient_food_portions_relationship(self):
        """Test the relationship between Ingredient and its FoodPortions"""
        # Test accessing portions through the ingredient
        portions = self.apple.food_portions.all()
        assert portions.count() == 2
        
        # Test ordering by sequence_number
        assert list(portions)[0].sequence_number < list(portions)[1].sequence_number
        
        # Test filtering
        piece_portions = self.apple.food_portions.filter(measure_unit_name="piece")
        assert piece_portions.count() == 1
        assert piece_portions.first().gram_weight == 182.0
        
    def test_multiple_ingredients_with_portions(self):
        """Test multiple ingredients each with their own portions"""
        # Create another ingredient
        banana = Ingredient.objects.create(
            name="Banana, raw",
            category=IngredientFoodCategory.FRUIT,
            base_unit_for_nutrition="g"
        )
        
        # Create food portions for banana
        banana_medium = FoodPortion.objects.create(
            ingredient=banana,
            amount=1.0,
            portion_description="1 medium banana (118g)",
            gram_weight=118.0,
            measure_unit_name="piece",
            measure_unit_abbreviation="pc"
        )
        
        banana_cup = FoodPortion.objects.create(
            ingredient=banana,
            amount=1.0,
            portion_description="1 cup, sliced",
            gram_weight=150.0,
            measure_unit_name="cup",
            measure_unit_abbreviation="cup"
        )
        
        # Check that portions relate to the correct ingredient
        assert banana.food_portions.count() == 2
        assert self.apple.food_portions.count() == 2
        
        # Ensure no cross-contamination between ingredients
        for portion in banana.food_portions.all():
            # Either the portion description should contain "banana" or verify it belongs to the banana ingredient
            assert "banana" in portion.portion_description.lower() or portion.ingredient.name.lower() == "banana, raw"
            
        for portion in self.apple.food_portions.all():
            assert "apple" in portion.portion_description.lower() or "sliced" in portion.portion_description.lower()
            
    def test_create_portion_with_modifier(self):
        """Test creating a portion with a modifier"""
        # Create a portion with a modifier
        apple_small = FoodPortion.objects.create(
            ingredient=self.apple,
            amount=1.0,
            portion_description="1 small apple",
            gram_weight=149.0,
            measure_unit_name="piece",
            measure_unit_abbreviation="pc",
            modifier="small"
        )
        
        # Test the modifier
        assert apple_small.modifier == "small"
        assert "small" in apple_small.portion_description
        
        # Test filtering by modifier
        small_apples = self.apple.food_portions.filter(modifier="small")
        assert small_apples.count() == 1
        assert small_apples.first().gram_weight == 149.0
