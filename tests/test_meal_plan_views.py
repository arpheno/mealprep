"""Tests for the MealPlanViewSet API endpoints."""
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    MealPlan, PersonProfile, MealComponent, Ingredient, IngredientUsage,
    MealPlanItem, MealComponentFrequency, Gender, Nutrient, NutrientCategory,
    IngredientNutrientLink
)


class MealPlanViewSetTests(APITestCase):
    """Tests for the MealPlanViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some person profiles for testing
        self.profile1 = PersonProfile.objects.create(
            name="John",
            gender=Gender.MALE,
            age_years=25,
            weight_kg=70,
            height_cm=180,
            activity_level=1.5
        )
        self.profile2 = PersonProfile.objects.create(
            name="Jane",
            gender=Gender.FEMALE,
            age_years=30,
            weight_kg=60,
            height_cm=165,
            activity_level=1.3
        )
        
        # Create some nutrients
        self.protein = Nutrient.objects.create(
            name="Protein",
            unit="g",
            category=NutrientCategory.MACRONUTRIENT
        )
        self.calories = Nutrient.objects.create(
            name="Energy",
            unit="kcal",
            category=NutrientCategory.GENERAL
        )
        
        # Create some ingredients
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        self.rice = Ingredient.objects.create(
            name="White Rice",
            notes="Long grain white rice"
        )
        
        # Add nutrient links to ingredients
        # Chicken: 25g protein, 165 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.protein,
            amount_per_100_units=25.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.calories,
            amount_per_100_units=165.0
        )
        
        # Rice: 7g protein, 130 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=self.protein,
            amount_per_100_units=7.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=self.calories,
            amount_per_100_units=130.0
        )
        
        # Create meal components
        self.meal1 = MealComponent.objects.create(
            name="Chicken and Rice Bowl",
            category_tag="Lunch",
            description_recipe="A simple lunch bowl with chicken and rice",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Add ingredient usages to meal components
        IngredientUsage.objects.create(
            meal_component=self.meal1,
            ingredient=self.chicken,
            quantity=150.0  # 150g
        )
        IngredientUsage.objects.create(
            meal_component=self.meal1,
            ingredient=self.rice,
            quantity=200.0  # 200g
        )
        
        self.meal2 = MealComponent.objects.create(
            name="Protein Shake",
            category_tag="Snack",
            description_recipe="A simple protein shake",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Create meal plans
        self.plan1 = MealPlan.objects.create(
            name="Weekly Meal Plan",
            notes="A weekly meal plan",
            duration_days=7,
            servings_per_day_per_person=3
        )
        self.plan1.target_people_profiles.add(self.profile1)
        
        self.plan2 = MealPlan.objects.create(
            name="Weekend Meal Plan",
            notes="A weekend meal plan",
            duration_days=2,
            servings_per_day_per_person=2
        )
        self.plan2.target_people_profiles.add(self.profile1, self.profile2)
        
        # Add meal items to plans
        self.item1 = MealPlanItem.objects.create(
            meal_plan=self.plan1,
            meal_component=self.meal1
        )
        self.item1.assigned_people.add(self.profile1)
        
        self.item2 = MealPlanItem.objects.create(
            meal_plan=self.plan2,
            meal_component=self.meal1
        )
        self.item2.assigned_people.add(self.profile1, self.profile2)
        
        self.item3 = MealPlanItem.objects.create(
            meal_plan=self.plan2,
            meal_component=self.meal2
        )
        self.item3.assigned_people.add(self.profile1)
        
        self.client = APIClient()
    
    def test_list_meal_plans(self):
        """Test retrieving a list of meal plans."""
        url = reverse('mealplan-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the meal plan names match what we expect
        plan_names = [plan['name'] for plan in response.data]
        self.assertIn("Weekly Meal Plan", plan_names)
        self.assertIn("Weekend Meal Plan", plan_names)
    
    def test_retrieve_meal_plan(self):
        """Test retrieving a specific meal plan by its ID."""
        url = reverse('mealplan-detail', kwargs={'pk': self.plan1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Weekly Meal Plan")
        self.assertEqual(response.data["notes"], "A weekly meal plan")
        self.assertEqual(response.data['duration_days'], 7)
        self.assertEqual(response.data['servings_per_day_per_person'], 3)
        
        # Check that it has the correct number of related objects
        self.assertEqual(len(response.data['target_people_profiles']), 1)
        self.assertEqual(len(response.data['plan_items']), 1)
    
    def test_create_meal_plan(self):
        """Test creating a new meal plan."""
        url = reverse('mealplan-list')
        data = {
            'name': 'Daily Meal Plan',
            'notes': 'A daily meal plan',
            'duration_days': 1,
            'servings_per_day_per_person': 4,
            'target_people_profiles': [self.profile2.id]
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MealPlan.objects.count(), 3)
        
        # Check that our new meal plan exists in the database
        new_plan = MealPlan.objects.get(name='Daily Meal Plan')
        self.assertEqual(new_plan.description, 'A daily meal plan')
        self.assertEqual(new_plan.duration_days, 1)
        self.assertEqual(new_plan.servings_per_day_per_person, 4)
        self.assertEqual(new_plan.target_people_profiles.count(), 1)
        self.assertEqual(new_plan.target_people_profiles.first().id, self.profile2.id)
    
    def test_update_meal_plan(self):
        """Test updating an existing meal plan."""
        url = reverse('mealplan-detail', kwargs={'pk': self.plan2.pk})
        data = {
            'name': 'Updated Weekend Meal Plan',
            'notes': 'An updated weekend meal plan',
            'duration_days': 3,  # Changed from 2 to 3
            'servings_per_day_per_person': 3,  # Changed from 2 to 3
            'target_people_profiles': [self.profile1.id]  # Removed profile2
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the meal plan from the database
        self.plan2.refresh_from_db()
        self.assertEqual(self.plan2.name, 'Updated Weekend Meal Plan')
        self.assertEqual(self.plan2.description, 'An updated weekend meal plan')
        self.assertEqual(self.plan2.duration_days, 3)
        self.assertEqual(self.plan2.servings_per_day_per_person, 3)
        self.assertEqual(self.plan2.target_people_profiles.count(), 1)
        self.assertEqual(self.plan2.target_people_profiles.first().id, self.profile1.id)
    
    def test_partial_update_meal_plan(self):
        """Test partially updating a meal plan."""
        url = reverse('mealplan-detail', kwargs={'pk': self.plan1.pk})
        data = {
            'name': 'Updated Weekly Meal Plan',
            'duration_days': 5,  # Changed from 7 to 5
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the meal plan from the database
        self.plan1.refresh_from_db()
        self.assertEqual(self.plan1.name, 'Updated Weekly Meal Plan')
        self.assertEqual(self.plan1.description, 'A weekly meal plan')  # Unchanged
        self.assertEqual(self.plan1.duration_days, 5)
        self.assertEqual(self.plan1.servings_per_day_per_person, 3)  # Unchanged
        
    def test_delete_meal_plan(self):
        """Test deleting an existing meal plan."""
        url = reverse('mealplan-detail', kwargs={'pk': self.plan2.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MealPlan.objects.count(), 1)
        
        # Check that the deleted meal plan does not exist
        with self.assertRaises(MealPlan.DoesNotExist):
            MealPlan.objects.get(pk=self.plan2.pk)
