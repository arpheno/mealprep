"""Tests for the IngredientNutrientLinkViewSet API endpoints."""
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    Ingredient, Nutrient, IngredientNutrientLink, NutrientCategory
)


class IngredientNutrientLinkViewSetTests(APITestCase):
    """Tests for the IngredientNutrientLinkViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some nutrients
        self.protein = Nutrient.objects.create(
            name="Protein",
            unit="g",
            category=NutrientCategory.MACRONUTRIENT
        )
        self.vitamin_c = Nutrient.objects.create(
            name="Vitamin C",
            unit="mg",
            category=NutrientCategory.VITAMIN
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
        self.broccoli = Ingredient.objects.create(
            name="Broccoli",
            notes="Fresh green broccoli"
        )
        
        # Create some ingredient-nutrient links
        self.link1 = IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.protein,
            amount_per_100_units=25.0
        )
        self.link2 = IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.calories,
            amount_per_100_units=165.0
        )
        self.link3 = IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.vitamin_c,
            amount_per_100_units=89.0
        )
        
        self.client = APIClient()
    
    def test_list_ingredient_nutrient_links(self):
        """Test retrieving a list of ingredient-nutrient links."""
        url = reverse('ingredientnutrientlink-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('results' in response.data, "Response should be paginated and contain 'results' key")
        self.assertEqual(response.data['count'], 3)
        
        results = response.data['results']
        self.assertEqual(len(results), 3)
        
        # Check that the links match what we expect
        ingredients = [link['ingredient'] for link in results]
        nutrients = [link['nutrient'] for link in results]
        
        self.assertIn(self.chicken.id, ingredients)
        self.assertIn(self.broccoli.id, ingredients)
        self.assertIn(self.protein.id, nutrients)
        self.assertIn(self.vitamin_c.id, nutrients)
        self.assertIn(self.calories.id, nutrients)
    
    def test_retrieve_ingredient_nutrient_link(self):
        """Test retrieving a specific ingredient-nutrient link by its ID."""
        url = reverse('ingredientnutrientlink-detail', kwargs={'pk': self.link1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['ingredient'], self.chicken.id)
        self.assertEqual(response.data['nutrient'], self.protein.id)
        self.assertEqual(response.data['amount_per_100_units'], 25.0)
    
    def test_create_ingredient_nutrient_link(self):
        """Test creating a new ingredient-nutrient link."""
        url = reverse('ingredientnutrientlink-list')
        data = {
            'ingredient': self.broccoli.id,
            'nutrient': self.protein.id,
            'amount_per_100_units': 2.8
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IngredientNutrientLink.objects.count(), 4)
        
        # Check that our new link exists in the database
        new_link = IngredientNutrientLink.objects.get(
            ingredient=self.broccoli, 
            nutrient=self.protein
        )
        self.assertEqual(new_link.amount_per_100_units, 2.8)
    
    def test_update_ingredient_nutrient_link(self):
        """Test updating an existing ingredient-nutrient link."""
        url = reverse('ingredientnutrientlink-detail', kwargs={'pk': self.link2.pk})
        data = {
            'ingredient': self.chicken.id,
            'nutrient': self.calories.id,
            'amount_per_100_units': 180.0  # Changed from 165.0
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the link from the database
        self.link2.refresh_from_db()
        self.assertEqual(self.link2.amount_per_100_units, 180.0)
    
    def test_partial_update_ingredient_nutrient_link(self):
        """Test partially updating an ingredient-nutrient link."""
        url = reverse('ingredientnutrientlink-detail', kwargs={'pk': self.link3.pk})
        data = {
            'amount_per_100_units': 95.0  # Changed from 89.0
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the link from the database
        self.link3.refresh_from_db()
        self.assertEqual(self.link3.amount_per_100_units, 95.0)
    
    def test_delete_ingredient_nutrient_link(self):
        """Test deleting an existing ingredient-nutrient link."""
        url = reverse('ingredientnutrientlink-detail', kwargs={'pk': self.link3.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(IngredientNutrientLink.objects.count(), 2)
        
        # Check that the deleted link does not exist
        with self.assertRaises(IngredientNutrientLink.DoesNotExist):
            IngredientNutrientLink.objects.get(pk=self.link3.pk)
