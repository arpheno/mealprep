import pytest
from django.core.exceptions import ValidationError
from api.models import (
    Ingredient, MealComponent, MealPlan, PersonProfile,
    IngredientUsage, Nutrient, IngredientNutrientLink,
    MealComponentFrequency, IngredientFoodCategory, MealPlanItem
)

@pytest.mark.django_db
class TestMealComponentModel:
    def setup_method(self):
        """Set up test data for each test method"""
        # Create sample ingredients
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            category=IngredientFoodCategory.PROTEIN_ANIMAL,
            base_unit_for_nutrition="g"
        )
        
        self.rice = Ingredient.objects.create(
            name="Brown Rice",
            category=IngredientFoodCategory.GRAIN_CEREAL,
            base_unit_for_nutrition="g"
        )
        
        self.broccoli = Ingredient.objects.create(
            name="Broccoli",
            category=IngredientFoodCategory.VEGETABLE_LEAFY,
            base_unit_for_nutrition="g"
        )
        
        # Create sample nutrients
        self.protein = Nutrient.objects.create(name="Protein", unit="g", category="MACRO")
        self.carbs = Nutrient.objects.create(name="Carbohydrates", unit="g", category="MACRO")
        self.calories = Nutrient.objects.create(name="Energy", unit="kcal", category="GENERAL")
        
        # Set up nutrient amounts for ingredients
        # Chicken breast: ~31g protein, 0g carbs, 165 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.protein,
            amount_per_100_units=31.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.carbs,
            amount_per_100_units=0.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.calories,
            amount_per_100_units=165.0
        )
        
        # Brown rice: ~2.6g protein, 23g carbs, 112 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=self.protein,
            amount_per_100_units=2.6
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=self.carbs,
            amount_per_100_units=23.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=self.calories,
            amount_per_100_units=112.0
        )
        
        # Broccoli: ~2.8g protein, 6.6g carbs, 34 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.protein,
            amount_per_100_units=2.8
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.carbs,
            amount_per_100_units=6.6
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.calories,
            amount_per_100_units=34.0
        )
        
        # Create a meal component
        self.meal_component = MealComponent.objects.create(
            name="Chicken & Rice Bowl",
            category_tag="Lunch",
            description_recipe="Simple chicken and rice bowl with broccoli",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Add ingredients to the meal component
        IngredientUsage.objects.create(
            meal_component=self.meal_component,
            ingredient=self.chicken,
            quantity=150.0  # 150g of chicken
        )
        IngredientUsage.objects.create(
            meal_component=self.meal_component,
            ingredient=self.rice,
            quantity=100.0  # 100g of rice
        )
        IngredientUsage.objects.create(
            meal_component=self.meal_component,
            ingredient=self.broccoli,
            quantity=80.0  # 80g of broccoli
        )
    
    def test_meal_component_creation(self):
        """Test if a meal component can be created with ingredients"""
        # Test basic properties
        assert self.meal_component.name == "Chicken & Rice Bowl"
        assert self.meal_component.category_tag == "Lunch"
        assert self.meal_component.description_recipe == "Simple chicken and rice bowl with broccoli"
        
        # Test ingredient relationships
        ingredient_usages = self.meal_component.ingredientusage_set.all()
        assert ingredient_usages.count() == 3
        
        # Check individual ingredients and their quantities
        ingredients_dict = {usage.ingredient.name: usage.quantity for usage in ingredient_usages}
        assert ingredients_dict["Chicken Breast"] == 150.0
        assert ingredients_dict["Brown Rice"] == 100.0
        assert ingredients_dict["Broccoli"] == 80.0
        
    def test_get_nutritional_totals(self):
        """Test calculating the nutritional totals for a meal component"""
        # Calculate nutritional totals
        nutrition = self.meal_component.get_nutritional_totals()
        
        # Expected nutrition values (based on the setup):
        # Chicken: 150g * (31g protein / 100g) = 46.5g protein
        #          150g * (0g carbs / 100g) = 0g carbs
        #          150g * (165 kcal / 100g) = 247.5 kcal
        # Rice:    100g * (2.6g protein / 100g) = 2.6g protein
        #          100g * (23g carbs / 100g) = 23g carbs
        #          100g * (112 kcal / 100g) = 112 kcal
        # Broccoli: 80g * (2.8g protein / 100g) = 2.24g protein
        #           80g * (6.6g carbs / 100g) = 5.28g carbs
        #           80g * (34 kcal / 100g) = 27.2 kcal
        # Total:   51.34g protein, 28.28g carbs, 386.7 kcal
        
        # These are rounded to 2 decimal places in get_nutritional_totals
        expected_protein = 51.34
        expected_carbs = 28.28
        expected_calories = 386.7
        
        # Check if the calculated values match expected values within a reasonable tolerance
        assert round(nutrition["Protein"]["amount"], 2) == round(expected_protein, 2)
        assert round(nutrition["Carbohydrates"]["amount"], 2) == round(expected_carbs, 2)
        assert round(nutrition["Energy"]["amount"], 2) == round(expected_calories, 2)
        
        # Check units
        assert nutrition["Protein"]["unit"] == "g"
        assert nutrition["Carbohydrates"]["unit"] == "g"
        assert nutrition["Energy"]["unit"] == "kcal"

@pytest.mark.django_db
class TestMealPlanModel:
    def setup_method(self):
        """Set up test data for each test method"""
        # Create a person profile
        self.person = PersonProfile.objects.create(
            name="Test Person",
            age_years=30,
            gender="MALE",
            weight_kg=70.0,
            height_cm=175.0,
            activity_level="MODERATE"
        )
        
        # Create some nutrients
        self.protein = Nutrient.objects.create(name="Protein", unit="g", category="MACRO")
        self.carbs = Nutrient.objects.create(name="Carbohydrates", unit="g", category="MACRO")
        self.calories = Nutrient.objects.create(name="Energy", unit="kcal", category="GENERAL")
        
        # Create sample ingredients with nutrient values
        chicken = Ingredient.objects.create(
            name="Chicken", category=IngredientFoodCategory.PROTEIN_ANIMAL
        )
        rice = Ingredient.objects.create(
            name="Rice", category=IngredientFoodCategory.GRAIN_CEREAL
        )
        
        # Add nutrient values to ingredients
        IngredientNutrientLink.objects.create(
            ingredient=chicken, nutrient=self.protein, amount_per_100_units=25.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=chicken, nutrient=self.calories, amount_per_100_units=120.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=rice, nutrient=self.carbs, amount_per_100_units=28.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=rice, nutrient=self.calories, amount_per_100_units=130.0
        )
        
        # Create meal components
        self.daily_component = MealComponent.objects.create(
            name="Daily Protein", 
            frequency=MealComponentFrequency.DAILY_TOTAL
        )
        self.meal_component = MealComponent.objects.create(
            name="Rice Bowl", 
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        self.weekly_component = MealComponent.objects.create(
            name="Weekly Treat", 
            frequency=MealComponentFrequency.WEEKLY_TOTAL
        )
        
        # Add ingredients to meal components
        IngredientUsage.objects.create(
            meal_component=self.daily_component, ingredient=chicken, quantity=200.0
        )
        IngredientUsage.objects.create(
            meal_component=self.meal_component, ingredient=rice, quantity=150.0
        )
        IngredientUsage.objects.create(
            meal_component=self.weekly_component, ingredient=chicken, quantity=100.0
        )
        
        # Create a meal plan for 7 days
        self.meal_plan = MealPlan.objects.create(
            name="Test Meal Plan",
            notes="A test meal plan for 7 days",
            duration_days=7,
            servings_per_day_per_person=2
        )
        
        # Add the person profile to the plan
        self.meal_plan.target_people_profiles.add(self.person)
        
        # Add meal components to the plan through MealPlanItem
        self.plan_item1 = MealPlanItem.objects.create(
            meal_plan=self.meal_plan,
            meal_component=self.daily_component
        )
        self.plan_item1.assigned_people.add(self.person)
        
        self.plan_item2 = MealPlanItem.objects.create(
            meal_plan=self.meal_plan,
            meal_component=self.meal_component
        )
        self.plan_item2.assigned_people.add(self.person)
        
        self.plan_item3 = MealPlanItem.objects.create(
            meal_plan=self.meal_plan,
            meal_component=self.weekly_component
        )
        self.plan_item3.assigned_people.add(self.person)
    
    def test_meal_plan_creation(self):
        """Test the basic properties of a meal plan"""
        assert self.meal_plan.name == "Test Meal Plan"
        assert self.meal_plan.notes == "A test meal plan for 7 days"
        assert self.meal_plan.duration_days == 7
        assert self.meal_plan.servings_per_day_per_person == 2
        
        # Test relationships
        assert self.meal_plan.target_people_profiles.count() == 1
        assert self.meal_plan.plan_items.count() == 3
        
    def test_get_plan_nutritional_totals(self):
        """Test calculation of nutritional totals for a meal plan"""
        nutrition = self.meal_plan.get_plan_nutritional_totals()
        
        # Expected values:
        # Daily component (chicken 200g): 
        #   - 50g protein, 240 kcal per day
        #   - For 7 days: 350g protein, 1680 kcal
        
        # Meal component (rice 150g):
        #   - 0g protein, 42g carbs, 195 kcal per serving
        #   - For 2 servings/day, 7 days = 14 servings total: 0g protein, 588g carbs, 2730 kcal
        
        # Weekly component (chicken 100g):
        #   - 25g protein, 120 kcal per week
        #   - For 1 week: 25g protein, 120 kcal
        
        # Totals: 375g protein, 588g carbs, 4530 kcal
        
        # Check if the calculated values are close to expected
        assert round(nutrition["Protein"]["amount"], 1) == 375.0
        assert round(nutrition["Carbohydrates"]["amount"], 1) == 588.0
        assert round(nutrition["Energy"]["amount"], 1) == 4530.0
        
        # Check units
        assert nutrition["Protein"]["unit"] == "g"
        assert nutrition["Carbohydrates"]["unit"] == "g"
        assert nutrition["Energy"]["unit"] == "kcal"
