"""Tests for the FoodPortionViewSet API endpoints."""
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    Ingredient, FoodPortion
)


class FoodPortionViewSetTests(APITestCase):
    """Tests for the FoodPortionViewSet API endpoints."""

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
        
        # Create some food portions
        self.portion1 = FoodPortion.objects.create(
            ingredient=self.chicken,
            amount=1.0,
            portion_description="1 medium breast, boneless, skinless",
            gram_weight=120.0,
            measure_unit_name="piece",
            measure_unit_abbreviation="pc",
            sequence_number=1
        )
        self.portion2 = FoodPortion.objects.create(
            ingredient=self.chicken,
            amount=0.5,
            portion_description="1/2 breast",
            gram_weight=60.0,
            measure_unit_name="piece",
            measure_unit_abbreviation="pc",
            sequence_number=2
        )
        self.portion3 = FoodPortion.objects.create(
            ingredient=self.rice,
            amount=1.0,
            portion_description="1 cup, cooked",
            gram_weight=158.0,
            measure_unit_name="cup",
            measure_unit_abbreviation="cup",
            sequence_number=1
        )
        
        self.client = APIClient()
    
    def test_list_food_portions(self):
        """Test retrieving a list of food portions."""
        url = reverse('foodportion-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('results' in response.data, "Response should be paginated and contain 'results' key")
        self.assertEqual(response.data['count'], 3)
        
        results = response.data['results']
        self.assertEqual(len(results), 3)
        
        # Check that the food portion descriptions match what we expect
        portion_descriptions = [portion['portion_description'] for portion in results]
        self.assertIn("1 medium breast, boneless, skinless", portion_descriptions)
        self.assertIn("1/2 breast", portion_descriptions)
        self.assertIn("1 cup, cooked", portion_descriptions)
    
    def test_retrieve_food_portion(self):
        """Test retrieving a specific food portion by its ID."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['portion_description'], "1 medium breast, boneless, skinless")
        self.assertEqual(response.data['gram_weight'], 120.0)
        self.assertEqual(response.data['measure_unit_name'], "piece")
        self.assertEqual(response.data['measure_unit_abbreviation'], "pc")
    
    def test_create_food_portion(self):
        """Test creating a new food portion."""
        url = reverse('foodportion-list')
        data = {
            'ingredient': self.rice.pk,
            'amount': 0.5,
            'portion_description': '1/2 cup, cooked',
            'gram_weight': 79.0,
            'measure_unit_name': 'cup',
            'measure_unit_abbreviation': 'cup',
            'sequence_number': 2
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FoodPortion.objects.count(), 4)
        
        # Check that our new food portion exists in the database
        new_portion = FoodPortion.objects.get(portion_description='1/2 cup, cooked')
        self.assertEqual(new_portion.ingredient_id, self.rice.id)
        self.assertEqual(new_portion.gram_weight, 79.0)
        self.assertEqual(new_portion.measure_unit_name, 'cup')
    
    def test_update_food_portion(self):
        """Test updating an existing food portion."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion2.pk})
        data = {
            'ingredient': self.chicken.pk,
            'amount': 0.5,
            'portion_description': '1/2 breast, boneless, skinless',  # Changed
            'gram_weight': 65.0,  # Changed
            'measure_unit_name': 'piece',
            'measure_unit_abbreviation': 'pc',
            'sequence_number': 2
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the food portion from the database
        self.portion2.refresh_from_db()
        self.assertEqual(self.portion2.portion_description, '1/2 breast, boneless, skinless')
        self.assertEqual(self.portion2.gram_weight, 65.0)
    
    def test_partial_update_food_portion(self):
        """Test partially updating a food portion."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion3.pk})
        data = {
            'gram_weight': 160.0  # Changed from 158.0
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the food portion from the database
        self.portion3.refresh_from_db()
        self.assertEqual(self.portion3.portion_description, '1 cup, cooked')  # Unchanged
        self.assertEqual(self.portion3.gram_weight, 160.0)  # Changed
    
    def test_delete_food_portion(self):
        """Test deleting an existing food portion."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion2.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FoodPortion.objects.count(), 2)
        
        # Check that the deleted food portion does not exist
        with self.assertRaises(FoodPortion.DoesNotExist):
            FoodPortion.objects.get(pk=self.portion2.pk)
