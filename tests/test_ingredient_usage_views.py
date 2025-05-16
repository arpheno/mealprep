"""Tests for the IngredientUsageViewSet API endpoints."""
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    Ingredient, MealComponent, IngredientUsage, MealComponentFrequency
)


class IngredientUsageViewSetTests(APITestCase):
    """Tests for the IngredientUsageViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some ingredients
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        self.rice = Ingredient.objects.create(
            name="White Rice",
            notes="Long grain white rice"
        )
        self.broccoli = Ingredient.objects.create(
            name="Broccoli",
            notes="Fresh green broccoli"
        )
        
        # Create some meal components
        self.meal1 = MealComponent.objects.create(
            name="Chicken and Rice Bowl",
            category_tag="Lunch",
            description_recipe="A simple lunch bowl with chicken and rice",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        self.meal2 = MealComponent.objects.create(
            name="Chicken Stir Fry",
            category_tag="Dinner",
            description_recipe="A simple stir fry with chicken and vegetables",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Create some ingredient usages
        self.usage1 = IngredientUsage.objects.create(
            meal_component=self.meal1,
            ingredient=self.chicken,
            quantity=150.0  # 150g
        )
        self.usage2 = IngredientUsage.objects.create(
            meal_component=self.meal1,
            ingredient=self.rice,
            quantity=200.0  # 200g
        )
        self.usage3 = IngredientUsage.objects.create(
            meal_component=self.meal2,
            ingredient=self.chicken,
            quantity=120.0  # 120g
        )
        
        self.client = APIClient()
    
    def test_list_ingredient_usages(self):
        """Test retrieving a list of ingredient usages."""
        url = reverse('ingredientusage-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('results' in response.data, "Response should be paginated and contain 'results' key")
        self.assertEqual(response.data['count'], 3)
        
        results = response.data['results']
        self.assertEqual(len(results), 3)
        
        # Check that the usages match what we expect
        meal_components = [usage['meal_component'] for usage in results]
        ingredients = [usage['ingredient'] for usage in results]
        
        self.assertIn(self.meal1.id, meal_components)
        self.assertIn(self.meal2.id, meal_components)
        self.assertIn(self.chicken.id, ingredients)
        self.assertIn(self.rice.id, ingredients)
    
    def test_retrieve_ingredient_usage(self):
        """Test retrieving a specific ingredient usage by its ID."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['meal_component'], self.meal1.id)
        self.assertEqual(response.data['ingredient'], self.chicken.id)
        self.assertEqual(response.data['quantity'], 150.0)
    
    def test_create_ingredient_usage(self):
        """Test creating a new ingredient usage."""
        url = reverse('ingredientusage-list')
        data = {
            'meal_component': self.meal2.id,
            'ingredient': self.broccoli.id,
            'quantity': 100.0
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IngredientUsage.objects.count(), 4)
        
        # Check that our new usage exists in the database
        new_usage = IngredientUsage.objects.get(
            meal_component=self.meal2, 
            ingredient=self.broccoli
        )
        self.assertEqual(new_usage.quantity, 100.0)
    
    def test_update_ingredient_usage(self):
        """Test updating an existing ingredient usage."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage2.pk})
        data = {
            'meal_component': self.meal1.id,
            'ingredient': self.rice.id,
            'quantity': 150.0  # Changed from 200.0
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the usage from the database
        self.usage2.refresh_from_db()
        self.assertEqual(self.usage2.quantity, 150.0)
    
    def test_partial_update_ingredient_usage(self):
        """Test partially updating an ingredient usage."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage3.pk})
        data = {
            'quantity': 130.0  # Changed from 120.0
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the usage from the database
        self.usage3.refresh_from_db()
        self.assertEqual(self.usage3.quantity, 130.0)
    
    def test_delete_ingredient_usage(self):
        """Test deleting an existing ingredient usage."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage3.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(IngredientUsage.objects.count(), 2)
        
        # Check that the deleted usage does not exist
        with self.assertRaises(IngredientUsage.DoesNotExist):
            IngredientUsage.objects.get(pk=self.usage3.pk)
