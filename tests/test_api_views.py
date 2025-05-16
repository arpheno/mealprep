import json
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    Nutrient, Ingredient, PersonProfile, MealComponent, MealPlan, 
    FoodPortion, IngredientNutrientLink, DietaryReferenceValue, Gender, NutrientCategory, IngredientUsage, MealComponentFrequency, MealPlanItem
)


class NutrientViewSetTests(APITestCase):
    """Tests for the NutrientViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some nutrients for testing
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
        self.client = APIClient()

    def test_list_nutrients(self):
        """Test retrieving a list of nutrients."""
        url = reverse('nutrient-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the nutrient names match what we expect
        nutrient_names = [nutrient['name'] for nutrient in response.data]
        self.assertIn("Vitamin C", nutrient_names)
        self.assertIn("Protein", nutrient_names)

    def test_retrieve_nutrient(self):
        """Test retrieving a specific nutrient by its ID."""
        url = reverse('nutrient-detail', kwargs={'pk': self.vitamin_c.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Vitamin C")
        self.assertEqual(response.data['unit'], "mg")
        self.assertEqual(response.data['category'], NutrientCategory.VITAMIN)

    def test_create_nutrient(self):
        """Test creating a new nutrient."""
        url = reverse('nutrient-list')
        data = {
            'name': 'Vitamin D',
            'unit': 'µg',
            'category': NutrientCategory.VITAMIN
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Nutrient.objects.count(), 3)
        
        # Check that our new nutrient exists in the database
        new_nutrient = Nutrient.objects.get(name='Vitamin D')
        self.assertEqual(new_nutrient.unit, 'µg')
        self.assertEqual(new_nutrient.category, NutrientCategory.VITAMIN)

    def test_update_nutrient(self):
        """Test updating an existing nutrient."""
        url = reverse('nutrient-detail', kwargs={'pk': self.protein.pk})
        data = {
            'name': 'Protein',
            'unit': 'g',
            'category': NutrientCategory.MACRONUTRIENT
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the nutrient from the database
        self.protein.refresh_from_db()
        self.assertEqual(self.protein.name, 'Protein')  # Name should remain the same
        self.assertEqual(self.protein.unit, 'g')  # Unit should remain the same
        self.assertEqual(self.protein.category, NutrientCategory.MACRONUTRIENT)  # Category should remain the same

    def test_delete_nutrient(self):
        """Test deleting an existing nutrient."""
        url = reverse('nutrient-detail', kwargs={'pk': self.vitamin_c.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Nutrient.objects.count(), 1)  # One nutrient left
        
        # Check that the deleted nutrient does not exist
        with self.assertRaises(Nutrient.DoesNotExist):
            Nutrient.objects.get(pk=self.vitamin_c.pk)


class IngredientSearchAPIViewTests(APITestCase):
    """Tests for the IngredientSearchAPIView."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some ingredients for testing
        self.chicken = Ingredient.objects.create(name="Chicken Breast", notes="Fresh chicken breast")
        self.chicken_thigh = Ingredient.objects.create(name="Chicken Thigh", notes="Fresh chicken thigh")
        self.beef = Ingredient.objects.create(name="Beef Steak", notes="Fresh beef steak")
        self.rice = Ingredient.objects.create(name="White Rice", notes="Long grain white rice")
        self.client = APIClient()

    def test_search_ingredient_by_name(self):
        """Test searching ingredients by name."""
        url = reverse('ingredient-search') + '?name=chicken'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Should return both chicken ingredients
        
        # Check that the ingredient names match what we expect
        ingredient_names = [ingredient['name'] for ingredient in response.data]
        self.assertIn("Chicken Breast", ingredient_names)
        self.assertIn("Chicken Thigh", ingredient_names)
        self.assertNotIn("Beef Steak", ingredient_names)
        self.assertNotIn("White Rice", ingredient_names)

    def test_search_ingredient_exact_match_first(self):
        """Test that exact matches appear first in the search results."""
        # Add an ingredient with a name that starts exactly with the search term
        exact_match = Ingredient.objects.create(name="Chicken", notes="Generic chicken")
        
        url = reverse('ingredient-search') + '?name=chicken'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # Should return all 3 chicken ingredients
        
        # The exact match "Chicken" should be first
        self.assertEqual(response.data[0]['name'], "Chicken")

    def test_search_ingredient_no_results(self):
        """Test searching for ingredients with no matching results."""
        url = reverse('ingredient-search') + '?name=nonexistent'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 0)  # Should return empty list

    def test_search_ingredient_no_query(self):
        """Test searching ingredients without providing a search query."""
        url = reverse('ingredient-search')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLessEqual(len(response.data), 20)  # Should return at most 20 results
        
        # Results should include our test ingredients
        ingredient_ids = [ingredient['id'] for ingredient in response.data]
        self.assertIn(self.chicken.id, ingredient_ids)
        self.assertIn(self.beef.id, ingredient_ids)


class IngredientViewSetTests(APITestCase):
    """Tests for the IngredientViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some ingredients for testing
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        self.rice = Ingredient.objects.create(
            name="White Rice",
            notes="Long grain white rice"
        )
        self.client = APIClient()

    def test_list_ingredients(self):
        """Test retrieving a list of ingredients."""
        url = reverse('ingredient-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the ingredient names match what we expect
        ingredient_names = [ingredient['name'] for ingredient in response.data]
        self.assertIn("Chicken Breast", ingredient_names)
        self.assertIn("White Rice", ingredient_names)

    def test_retrieve_ingredient(self):
        """Test retrieving a specific ingredient by its ID."""
        url = reverse('ingredient-detail', kwargs={'pk': self.chicken.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Chicken Breast")
        self.assertEqual(response.data["notes"], "Fresh chicken breast")

    def test_create_ingredient(self):
        """Test creating a new ingredient."""
        url = reverse('ingredient-list')
        data = {
            'name': 'Broccoli',
            'notes': 'Fresh green broccoli'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Ingredient.objects.count(), 3)
        
        # Check that our new ingredient exists in the database
        new_ingredient = Ingredient.objects.get(name='Broccoli')
        self.assertEqual(new_ingredient.description, 'Fresh green broccoli')

    def test_update_ingredient(self):
        """Test updating an existing ingredient."""
        url = reverse('ingredient-detail', kwargs={'pk': self.chicken.pk})
        data = {
            'name': 'Chicken Breast',
            'notes': 'Organic chicken breast'
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the ingredient from the database
        self.chicken.refresh_from_db()
        self.assertEqual(self.chicken.name, 'Chicken Breast')
        self.assertEqual(self.chicken.description, 'Organic chicken breast')

    def test_delete_ingredient(self):
        """Test deleting an existing ingredient."""
        url = reverse('ingredient-detail', kwargs={'pk': self.rice.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Ingredient.objects.count(), 1)
        
        # Check that the deleted ingredient does not exist
        with self.assertRaises(Ingredient.DoesNotExist):
            Ingredient.objects.get(pk=self.rice.pk)


class CalculateNutritionalTargetsViewTests(APITestCase):
    """Tests for the CalculateNutritionalTargetsView."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create nutrients
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
        
        # Create DRVs
        self.drv_vitamin_c_male = DietaryReferenceValue.objects.create(
            nutrient=self.vitamin_c,
            gender=Gender.MALE,
            target_population="Adults",
            age_range_text="19-30 years",
            pri=90.0,
            ul=2000.0,
            value_unit="mg"
        )
        
        self.drv_vitamin_c_female = DietaryReferenceValue.objects.create(
            nutrient=self.vitamin_c,
            gender=Gender.FEMALE,
            target_population="Adults",
            age_range_text="19-30 years",
            pri=75.0,
            ul=2000.0,
            value_unit="mg"
        )
        
        self.drv_protein_male = DietaryReferenceValue.objects.create(
            nutrient=self.protein,
            gender=Gender.MALE,
            target_population="Adults",
            age_range_text="19-30 years",
            pri=56.0,
            value_unit="g"
        )
        
        self.drv_protein_female = DietaryReferenceValue.objects.create(
            nutrient=self.protein,
            gender=Gender.FEMALE,
            target_population="Adults",
            age_range_text="19-30 years",
            pri=46.0,
            value_unit="g"
        )
        
        # Create person profiles
        self.profile_male = PersonProfile.objects.create(
            name="John",
            gender=Gender.MALE,
            age_years=25,
            weight_kg=70,
            height_cm=180,
            activity_level=1.5
        )
        
        self.profile_female = PersonProfile.objects.create(
            name="Jane",
            gender=Gender.FEMALE,
            age_years=25,
            weight_kg=60,
            height_cm=165,
            activity_level=1.5
        )
        
        self.client = APIClient()

    def test_calculate_nutritional_targets_single_profile(self):
        """Test calculating nutritional targets for a single person profile."""
        url = reverse('calculate-nutritional-targets')
        data = {
            "person_profile_ids": [self.profile_male.id]
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the response contains the expected nutrients
        self.assertIn("Vitamin C", response.data)
        self.assertIn("Protein", response.data)
        
        # Check the values for each nutrient
        self.assertEqual(response.data["Vitamin C"]["rda"], 90.0)  # Using PRI as RDA for male
        self.assertEqual(response.data["Vitamin C"]["ul"], 2000.0)
        self.assertEqual(response.data["Vitamin C"]["unit"], "mg")
        
        self.assertEqual(response.data["Protein"]["rda"], 56.0)  # Using PRI as RDA for male
        self.assertIsNone(response.data["Protein"]["ul"])  # No UL set for protein
        self.assertEqual(response.data["Protein"]["unit"], "g")

    def test_calculate_nutritional_targets_multiple_profiles(self):
        """Test calculating combined nutritional targets for multiple person profiles."""
        url = reverse('calculate-nutritional-targets')
        data = {
            "person_profile_ids": [self.profile_male.id, self.profile_female.id]
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the response contains the expected nutrients
        self.assertIn("Vitamin C", response.data)
        self.assertIn("Protein", response.data)
        
        # Check the values for each nutrient - should be sum of male and female values
        self.assertEqual(response.data["Vitamin C"]["rda"], 90.0 + 75.0)  # Sum of male and female PRIs
        self.assertEqual(response.data["Vitamin C"]["ul"], 2000.0 + 2000.0)  # Sum of male and female ULs
        self.assertEqual(response.data["Vitamin C"]["unit"], "mg")
        
        self.assertEqual(response.data["Protein"]["rda"], 56.0 + 46.0)  # Sum of male and female PRIs
        self.assertIsNone(response.data["Protein"]["ul"])  # No UL set for protein
        self.assertEqual(response.data["Protein"]["unit"], "g")

    def test_calculate_nutritional_targets_invalid_ids(self):
        """Test calculating nutritional targets with invalid profile IDs."""
        url = reverse('calculate-nutritional-targets')
        data = {
            "person_profile_ids": [999, 1000]  # Non-existent IDs
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should return empty dict since no valid profiles were found
        self.assertEqual(response.data, {})

    def test_calculate_nutritional_targets_mixed_valid_invalid_ids(self):
        """Test calculating nutritional targets with a mix of valid and invalid profile IDs."""
        url = reverse('calculate-nutritional-targets')
        data = {
            "person_profile_ids": [self.profile_male.id, 999]  # One valid, one invalid ID
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that the response contains data for the valid profile only
        self.assertIn("Vitamin C", response.data)
        self.assertEqual(response.data["Vitamin C"]["rda"], 90.0)  # Only male PRI


class PersonProfileViewSetTests(APITestCase):
    """Tests for the PersonProfileViewSet API endpoints."""

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
        self.client = APIClient()

    def test_list_profiles(self):
        """Test retrieving a list of person profiles."""
        url = reverse('personprofile-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the profile names match what we expect
        profile_names = [profile['name'] for profile in response.data]
        self.assertIn("John", profile_names)
        self.assertIn("Jane", profile_names)

    def test_retrieve_profile(self):
        """Test retrieving a specific person profile by its ID."""
        url = reverse('personprofile-detail', kwargs={'pk': self.profile1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "John")
        self.assertEqual(response.data['gender'], Gender.MALE)
        self.assertEqual(response.data['age_years'], 25)
        self.assertEqual(response.data['weight_kg'], 70)
        self.assertEqual(response.data['height_cm'], 180)
        self.assertEqual(response.data['activity_level'], 1.5)

    def test_create_profile(self):
        """Test creating a new person profile."""
        url = reverse('personprofile-list')
        data = {
            'name': 'Alex',
            'gender': Gender.MALE,
            'age_years': 35,
            'weight_kg': 80,
            'height_cm': 175,
            'activity_level': 1.8
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PersonProfile.objects.count(), 3)
        
        # Check that our new profile exists in the database
        new_profile = PersonProfile.objects.get(name='Alex')
        self.assertEqual(new_profile.gender, Gender.MALE)
        self.assertEqual(new_profile.age, 35)

    def test_update_profile(self):
        """Test updating an existing person profile."""
        url = reverse('personprofile-detail', kwargs={'pk': self.profile2.pk})
        data = {
            'name': 'Jane',
            'gender': Gender.FEMALE,
            'age_years': 31,  # Changed age
            'weight_kg': 62,  # Changed weight
            'height_cm': 165,
            'activity_level': 1.3
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the profile from the database
        self.profile2.refresh_from_db()
        self.assertEqual(self.profile2.age, 31)
        self.assertEqual(self.profile2.weight_kg, 62)

    def test_delete_profile(self):
        """Test deleting an existing person profile."""
        url = reverse('personprofile-detail', kwargs={'pk': self.profile1.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(PersonProfile.objects.count(), 1)
        
        # Check that the deleted profile does not exist
        with self.assertRaises(PersonProfile.DoesNotExist):
            PersonProfile.objects.get(pk=self.profile1.pk)


class FoodPortionViewSetTests(APITestCase):
    """Tests for the FoodPortionViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create an ingredient
        self.ingredient = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        
        # Create food portions for the ingredient
        self.portion1 = FoodPortion.objects.create(
            ingredient=self.ingredient,
            amount=1.0,
            portion_description="1 cup, diced",
            gram_weight=140.0,
            measure_unit_name="cup",
            sequence_number=1
        )
        
        self.portion2 = FoodPortion.objects.create(
            ingredient=self.ingredient,
            amount=3.0,
            portion_description="3 oz",
            gram_weight=85.0,
            measure_unit_name="oz",
            sequence_number=2
        )
        
        self.client = APIClient()

    def test_list_food_portions(self):
        """Test retrieving a list of food portions."""
        url = reverse('foodportion-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the food portion descriptions match what we expect
        portion_descriptions = [portion['portion_description'] for portion in response.data]
        self.assertIn("1 cup, diced", portion_descriptions)
        self.assertIn("3 oz", portion_descriptions)

    def test_retrieve_food_portion(self):
        """Test retrieving a specific food portion by its ID."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['portion_description'], "1 cup, diced")
        self.assertEqual(response.data['gram_weight'], 140.0)
        self.assertEqual(response.data['measure_unit_name'], "cup")

    def test_create_food_portion(self):
        """Test creating a new food portion."""
        url = reverse('foodportion-list')
        data = {
            'ingredient': self.ingredient.id,
            'amount': 1.0,
            'portion_description': '1 slice',
            'gram_weight': 30.0,
            'measure_unit_name': 'slice',
            'sequence_number': 3
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FoodPortion.objects.count(), 3)
        
        # Check that our new food portion exists in the database
        new_portion = FoodPortion.objects.get(portion_description='1 slice')
        self.assertEqual(new_portion.gram_weight, 30.0)
        self.assertEqual(new_portion.measure_unit_name, 'slice')

    def test_update_food_portion(self):
        """Test updating an existing food portion."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion2.pk})
        data = {
            'ingredient': self.ingredient.id,
            'amount': 3.0,
            'portion_description': '3 oz, cooked',  # Changed description
            'gram_weight': 90.0,  # Changed weight
            'measure_unit_name': 'oz',
            'sequence_number': 2
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the food portion from the database
        self.portion2.refresh_from_db()
        self.assertEqual(self.portion2.portion_description, '3 oz, cooked')
        self.assertEqual(self.portion2.gram_weight, 90.0)

    def test_delete_food_portion(self):
        """Test deleting an existing food portion."""
        url = reverse('foodportion-detail', kwargs={'pk': self.portion1.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(FoodPortion.objects.count(), 1)
        
        # Check that the deleted food portion does not exist
        with self.assertRaises(FoodPortion.DoesNotExist):
            FoodPortion.objects.get(pk=self.portion1.pk)


class IngredientNutrientLinkViewSetTests(APITestCase):
    """Tests for the IngredientNutrientLinkViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create nutrients
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
        
        # Create ingredients
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        
        # Create ingredient-nutrient links
        self.link1 = IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.protein,
            amount_per_100_units=25.0
        )
        
        self.link2 = IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=self.vitamin_c,
            amount_per_100_units=0.0
        )
        
        self.client = APIClient()

    def test_list_ingredient_nutrient_links(self):
        """Test retrieving a list of ingredient-nutrient links."""
        url = reverse('ingredientnutrientlink-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the links match what we expect
        for link in response.data:
            if link['nutrient'] == self.protein.id:
                self.assertEqual(link['amount_per_100_units'], 25.0)
            elif link['nutrient'] == self.vitamin_c.id:
                self.assertEqual(link['amount_per_100_units'], 0.0)

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
        # Create a new ingredient and nutrient
        broccoli = Ingredient.objects.create(
            name="Broccoli",
            notes="Fresh broccoli"
        )
        
        url = reverse('ingredientnutrientlink-list')
        data = {
            'ingredient': broccoli.id,
            'nutrient': self.protein.id,
            'amount_per_100_units': 2.8
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IngredientNutrientLink.objects.count(), 3)
        
        # Check that our new link exists in the database
        new_link = IngredientNutrientLink.objects.get(ingredient=broccoli, nutrient=self.protein)
        self.assertEqual(new_link.amount_per_100_units, 2.8)

    def test_update_ingredient_nutrient_link(self):
        """Test updating an existing ingredient-nutrient link."""
        url = reverse('ingredientnutrientlink-detail', kwargs={'pk': self.link1.pk})
        data = {
            'ingredient': self.chicken.id,
            'nutrient': self.protein.id,
            'amount_per_100_units': 26.5  # Changed amount
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the link from the database
        self.link1.refresh_from_db()
        self.assertEqual(self.link1.amount_per_100_units, 26.5)

    def test_delete_ingredient_nutrient_link(self):
        """Test deleting an existing ingredient-nutrient link."""
        url = reverse('ingredientnutrientlink-detail', kwargs={'pk': self.link2.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(IngredientNutrientLink.objects.count(), 1)
        
        # Check that the deleted link does not exist
        with self.assertRaises(IngredientNutrientLink.DoesNotExist):
            IngredientNutrientLink.objects.get(pk=self.link2.pk)


class IngredientUsageViewSetTests(APITestCase):
    """Tests for the IngredientUsageViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create ingredients
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        self.rice = Ingredient.objects.create(
            name="White Rice",
            notes="Long grain white rice"
        )
        
        # Create a meal component
        self.meal = MealComponent.objects.create(
            name="Chicken and Rice Bowl",
            category_tag="Lunch",
            description_recipe="A simple lunch bowl with chicken and rice",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Create ingredient usages
        self.usage1 = IngredientUsage.objects.create(
            meal_component=self.meal,
            ingredient=self.chicken,
            quantity=150.0  # 150g
        )
        self.usage2 = IngredientUsage.objects.create(
            meal_component=self.meal,
            ingredient=self.rice,
            quantity=200.0  # 200g
        )
        
        self.client = APIClient()

    def test_list_ingredient_usages(self):
        """Test retrieving a list of ingredient usages."""
        url = reverse('ingredientusage-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the usages match what we expect
        for usage in response.data:
            if usage['ingredient'] == self.chicken.id:
                self.assertEqual(usage['quantity'], 150.0)
            elif usage['ingredient'] == self.rice.id:
                self.assertEqual(usage['quantity'], 200.0)

    def test_retrieve_ingredient_usage(self):
        """Test retrieving a specific ingredient usage by its ID."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['meal_component'], self.meal.id)
        self.assertEqual(response.data['ingredient'], self.chicken.id)
        self.assertEqual(response.data['quantity'], 150.0)

    def test_create_ingredient_usage(self):
        """Test creating a new ingredient usage."""
        # Create a new ingredient
        broccoli = Ingredient.objects.create(
            name="Broccoli",
            notes="Fresh broccoli"
        )
        
        url = reverse('ingredientusage-list')
        data = {
            'meal_component': self.meal.id,
            'ingredient': broccoli.id,
            'quantity': 100.0
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(IngredientUsage.objects.count(), 3)
        
        # Check that our new usage exists in the database
        new_usage = IngredientUsage.objects.get(meal_component=self.meal, ingredient=broccoli)
        self.assertEqual(new_usage.quantity, 100.0)

    def test_update_ingredient_usage(self):
        """Test updating an existing ingredient usage."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage2.pk})
        data = {
            'meal_component': self.meal.id,
            'ingredient': self.rice.id,
            'quantity': 150.0  # Changed from 200g to 150g
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the usage from the database
        self.usage2.refresh_from_db()
        self.assertEqual(self.usage2.quantity, 150.0)

    def test_delete_ingredient_usage(self):
        """Test deleting an existing ingredient usage."""
        url = reverse('ingredientusage-detail', kwargs={'pk': self.usage1.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(IngredientUsage.objects.count(), 1)
        
        # Check that the deleted usage does not exist
        with self.assertRaises(IngredientUsage.DoesNotExist):
            IngredientUsage.objects.get(pk=self.usage1.pk)


class DietaryReferenceValueViewSetTests(APITestCase):
    """Tests for the DietaryReferenceValueViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create nutrients
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
        
        # Create DRVs
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

    def test_list_drvs(self):
        """Test retrieving a list of dietary reference values."""
        url = reverse('dietaryreferencevalue-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that the DRVs match what we expect
        for drv in response.data:
            if drv['nutrient'] == self.vitamin_c.id:
                self.assertEqual(drv['pri'], 90.0)
                self.assertEqual(drv['ul'], 2000.0)
            elif drv['nutrient'] == self.protein.id:
                self.assertEqual(drv['pri'], 56.0)
                self.assertIsNone(drv['ul'])

    def test_retrieve_drv(self):
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

    def test_create_drv(self):
        """Test creating a new dietary reference value."""
        url = reverse('dietaryreferencevalue-list')
        data = {
            'source_data_category': 'Vitamins',
            'nutrient': self.vitamin_c.id,
            'target_population': 'Adults',
            'age_range_text': '31-50 years',
            'gender': Gender.FEMALE,
            'frequency': 'daily',
            'value_unit': 'mg',
            'pri': 75.0,
            'ul': 2000.0
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(DietaryReferenceValue.objects.count(), 3)
        
        # Check that our new DRV exists in the database
        new_drv = DietaryReferenceValue.objects.get(
            nutrient=self.vitamin_c,
            target_population='Adults',
            age_range_text='31-50 years',
            gender=Gender.FEMALE
        )
        self.assertEqual(new_drv.pri, 75.0)
        self.assertEqual(new_drv.ul, 2000.0)

    def test_update_drv(self):
        """Test updating an existing dietary reference value."""
        url = reverse('dietaryreferencevalue-detail', kwargs={'pk': self.drv2.pk})
        data = {
            'source_data_category': 'Macronutrients',
            'nutrient': self.protein.id,
            'target_population': 'Adults',
            'age_range_text': '19-30 years',
            'gender': Gender.MALE,
            'frequency': 'daily',
            'value_unit': 'g',
            'pri': 58.0,  # Changed from 56.0 to 58.0
            'ul': 200.0   # Added UL value
        }
        response = self.client.put(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the DRV from the database
        self.drv2.refresh_from_db()
        self.assertEqual(self.drv2.pri, 58.0)
        self.assertEqual(self.drv2.ul, 200.0)

    def test_delete_drv(self):
        """Test deleting an existing dietary reference value."""
        url = reverse('dietaryreferencevalue-detail', kwargs={'pk': self.drv1.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(DietaryReferenceValue.objects.count(), 1)
        
        # Check that the deleted DRV does not exist
        with self.assertRaises(DietaryReferenceValue.DoesNotExist):
            DietaryReferenceValue.objects.get(pk=self.drv1.pk)


class MealPlanViewSetTests(APITestCase):
    """Tests for the MealPlanViewSet API endpoints."""

    def setUp(self):
        """Set up test data for each test method."""
        # Create some person profiles
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
        
        # Create some ingredients
        self.chicken = Ingredient.objects.create(
            name="Chicken Breast",
            notes="Fresh chicken breast"
        )
        self.rice = Ingredient.objects.create(
            name="White Rice",
            notes="Long grain white rice"
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
    
    def test_delete_meal_plan(self):
        """Test deleting an existing meal plan."""
        url = reverse('mealplan-detail', kwargs={'pk': self.plan2.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MealPlan.objects.count(), 1)
        
        # Check that the deleted meal plan does not exist
        with self.assertRaises(MealPlan.DoesNotExist):
            MealPlan.objects.get(pk=self.plan2.pk)
            
    def test_meal_plan_nutritional_totals(self):
        """Test that a meal plan correctly calculates its nutritional totals."""
        # First, add nutrients to ingredients
        protein = Nutrient.objects.create(
            name="Protein",
            unit="g",
            category=NutrientCategory.MACRONUTRIENT
        )
        calories = Nutrient.objects.create(
            name="Energy",
            unit="kcal",
            category=NutrientCategory.GENERAL
        )
        
        # Add nutrient links to ingredients
        # Chicken: 25g protein, 165 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=protein,
            amount_per_100_units=25.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.chicken,
            nutrient=calories,
            amount_per_100_units=165.0
        )
        
        # Rice: 7g protein, 130 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=protein,
            amount_per_100_units=7.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.rice,
            nutrient=calories,
            amount_per_100_units=130.0
        )
        
        # Get the plan nutritional totals
        plan_totals = self.plan1.get_plan_nutritional_totals()
        
        # Calculate expected totals for the meal plan
        # Plan 1: 1 person, 7 days, 3 servings per day
        # Meal 1: 150g chicken (37.5g protein, 247.5 kcal) + 200g rice (14g protein, 260 kcal)
        # Total per meal: 51.5g protein, 507.5 kcal
        # Total for plan: 51.5g * 1 person * 7 days * 3 servings = 1081.5g protein
        #                 507.5 kcal * 1 person * 7 days * 3 servings = 10657.5 kcal
        
        self.assertIn('Protein', plan_totals)
        self.assertIn('Energy', plan_totals)
        self.assertEqual(plan_totals['Protein']['amount'], 1081.5)
        self.assertEqual(plan_totals['Protein']['unit'], 'g')
        self.assertEqual(plan_totals['Energy']['amount'], 10657.5)
        self.assertEqual(plan_totals['Energy']['unit'], 'kcal')
