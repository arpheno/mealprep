"""Tests for the DietaryReferenceValueViewSet API endpoints."""
import json
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    Nutrient, DietaryReferenceValue, NutrientCategory, Gender
)


class DietaryReferenceValueViewSetTests(APITestCase):
    """Tests for the DietaryReferenceValueViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some nutrients
        self.vitamin_c = Nutrient.objects.create(
            name="Vitamin C",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        self.protein = Nutrient.objects.create(
            name="Protein",
            unit="g",
            category=NutrientCategory.MACRONUTRIENT
        )
        self.calcium = Nutrient.objects.create(
            name="Calcium",
            unit="mg",
            category=NutrientCategory.MINERAL
        )
        
        # Create some dietary reference values
        self.drv1 = DietaryReferenceValue.objects.create(
            source_data_category="Vitamins",
            nutrient=self.vitamin_c,
            target_population="Adults",
            age_range_text="19-30 years",
            gender=Gender.MALE,
            frequency="daily",
            value_unit="mg",
            pri=90.0,
            ul=2000.0
        )
        self.drv2 = DietaryReferenceValue.objects.create(
            source_data_category="Vitamins",
            nutrient=self.vitamin_c,
            target_population="Adults",
            age_range_text="19-30 years",
            gender=Gender.FEMALE,
            frequency="daily",
            value_unit="mg",
            pri=75.0,
            ul=2000.0
        )
        self.drv3 = DietaryReferenceValue.objects.create(
            source_data_category="Macronutrients",
            nutrient=self.protein,
            target_population="Adults",
            age_range_text="19-30 years",
            gender=Gender.MALE,
            frequency="daily",
            value_unit="g",
            pri=56.0
        )
        
        self.client = APIClient()
    
    def test_list_dietary_reference_values(self):
        """Test retrieving a list of dietary reference values."""
        url = reverse('dietaryreferencevalue-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)
        
        # Check that the DRVs match what we expect
        nutrients = [drv['nutrient'] for drv in response.data]
        genders = [drv['gender'] for drv in response.data]
        
        self.assertIn(self.vitamin_c.id, nutrients)
        self.assertIn(self.protein.id, nutrients)
        self.assertIn(Gender.MALE, genders)
        self.assertIn(Gender.FEMALE, genders)
    
    def test_retrieve_dietary_reference_value(self):
        """Test retrieving a specific dietary reference value by its ID."""
        url = reverse('dietaryreferencevalue-detail', kwargs={'pk': self.drv1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['nutrient'], self.vitamin_c.id)
        self.assertEqual(response.data['target_population'], "Adults")
        self.assertEqual(response.data['age_range_text'], "19-30 years")
        self.assertEqual(response.data['gender'], Gender.MALE)
        self.assertEqual(response.data['pri'], 90.0)
        self.assertEqual(response.data['ul'], 2000.0)
    
    def test_create_dietary_reference_value(self):
        """Test creating a new dietary reference value."""
        url = reverse('dietaryreferencevalue-list')
        data = {
            'source_data_category': "Minerals",
            'nutrient': self.calcium.id,
            'target_population': "Adults",
            'age_range_text': "19-30 years",
            'gender': Gender.MALE,
            'frequency': "daily",
            'value_unit': "mg",
            'pri': 1000.0,
            'ul': 2500.0
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DietaryReferenceValue.objects.count(), 4)
        
        # Check that our new DRV exists in the database
        new_drv = DietaryReferenceValue.objects.get(
            nutrient=self.calcium, 
            gender=Gender.MALE
        )
        self.assertEqual(new_drv.pri, 1000.0)
        self.assertEqual(new_drv.ul, 2500.0)
    
    def test_update_dietary_reference_value(self):
        """Test updating an existing dietary reference value."""
        url = reverse('dietaryreferencevalue-detail', kwargs={'pk': self.drv3.pk})
        data = {
            'source_data_category': "Macronutrients",
            'nutrient': self.protein.id,
            'target_population': "Adults",
            'age_range_text': "19-30 years",
            'gender': Gender.MALE,
            'frequency': "daily",
            'value_unit': "g",
            'pri': 60.0,  # Changed from 56.0
            'ul': 170.0   # Added UL
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the DRV from the database
        self.drv3.refresh_from_db()
        self.assertEqual(self.drv3.pri, 60.0)
        self.assertEqual(self.drv3.ul, 170.0)
    
    def test_partial_update_dietary_reference_value(self):
        """Test partially updating a dietary reference value."""
        url = reverse('dietaryreferencevalue-detail', kwargs={'pk': self.drv2.pk})
        data = {
            'pri': 80.0,  # Changed from 75.0
            'ul': 1800.0  # Changed from 2000.0
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the DRV from the database
        self.drv2.refresh_from_db()
        self.assertEqual(self.drv2.pri, 80.0)
        self.assertEqual(self.drv2.ul, 1800.0)
    
    def test_delete_dietary_reference_value(self):
        """Test deleting an existing dietary reference value."""
        url = reverse('dietaryreferencevalue-detail', kwargs={'pk': self.drv3.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DietaryReferenceValue.objects.count(), 2)
        
        # Check that the deleted DRV does not exist
        with self.assertRaises(DietaryReferenceValue.DoesNotExist):
            DietaryReferenceValue.objects.get(pk=self.drv3.pk)
