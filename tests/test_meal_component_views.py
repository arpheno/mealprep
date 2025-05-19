import json
from django.urls import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient, APITestCase
from api.models import (
    Nutrient, Ingredient, MealComponent, IngredientUsage, 
    IngredientNutrientLink, MealComponentFrequency, NutrientCategory
)


class MealComponentViewSetTests(APITestCase):
    """Tests for the MealComponentViewSet API endpoints."""

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
        self.calories = Nutrient.objects.create(
            name="Energy",
            unit="kcal",
            category=NutrientCategory.GENERAL
        )
        
        # Create ingredients
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
        
        # Add nutrient links to ingredients
        # Chicken: 25g protein, 0mg vitamin C, 165 kcal per 100g
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
        
        # Rice: 7g protein, 0mg vitamin C, 130 kcal per 100g
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
        
        # Broccoli: 2.8g protein, 89mg vitamin C, 34 kcal per 100g
        IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.protein,
            amount_per_100_units=2.8
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.vitamin_c,
            amount_per_100_units=89.0
        )
        IngredientNutrientLink.objects.create(
            ingredient=self.broccoli,
            nutrient=self.calories,
            amount_per_100_units=34.0
        )
        
        # Create meal components
        self.meal1 = MealComponent.objects.create(
            name="Chicken and Rice Bowl",
            category_tag="Lunch",
            description_recipe="A simple lunch bowl with chicken and rice",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Add ingredient usages to meal components
        # 150g chicken, 200g rice
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
            name="Broccoli Side",
            category_tag="Side",
            description_recipe="Steamed broccoli side dish",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        # Add ingredient usages to meal components
        # 100g broccoli
        IngredientUsage.objects.create(
            meal_component=self.meal2,
            ingredient=self.broccoli,
            quantity=100.0  # 100g
        )
        
        self.client = APIClient()

    def test_list_meal_components(self):
        """Test retrieving a list of meal components."""
        url = reverse('mealcomponent-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is turned off as per user's manual change
        self.assertFalse('results' in response.data, "Response should not be paginated")
        self.assertEqual(len(response.data), 2)
        
        # Check that the meal component names match what we expect
        component_names = [component['name'] for component in response.data]
        self.assertIn("Chicken and Rice Bowl", component_names)
        self.assertIn("Broccoli Side", component_names)
        
        # Check that the first component has the expected category
        for component in response.data:
            if component['name'] == "Chicken and Rice Bowl":
                self.assertEqual(component['category_tag'], "Lunch")
            elif component['name'] == "Broccoli Side":
                self.assertEqual(component['category_tag'], "Side")

    def test_retrieve_meal_component(self):
        """Test retrieving a specific meal component by its ID."""
        url = reverse('mealcomponent-detail', kwargs={'pk': self.meal1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], "Chicken and Rice Bowl")
        self.assertEqual(response.data['category_tag'], "Lunch")
        self.assertEqual(response.data['frequency'], MealComponentFrequency.PER_MEAL_BOX)
        
        # Check that it has the correct number of ingredient usages
        self.assertEqual(len(response.data['ingredientusage_set']), 2)

    def test_retrieve_meal_component_with_nutritional_totals(self):
        """Test retrieving a meal component and checking its nutritional totals."""
        url = reverse('mealcomponent-detail', kwargs={'pk': self.meal1.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify nutritional totals are included in response
        self.assertIn('nutritional_totals', response.data)
        
        # Calculate expected totals
        # 150g chicken: 37.5g protein, 0mg vitamin C, 247.5 kcal
        # 200g rice: 14g protein, 0mg vitamin C, 260 kcal
        # Total: 51.5g protein, 0mg vitamin C, 507.5 kcal
        
        nutritional_totals = response.data['nutritional_totals']
        
        self.assertIn('Protein', nutritional_totals)
        self.assertIn('Energy', nutritional_totals)
        self.assertEqual(nutritional_totals['Protein']['amount'], 51.5)
        self.assertEqual(nutritional_totals['Protein']['unit'], 'g')
        self.assertEqual(nutritional_totals['Energy']['amount'], 507.5)
        self.assertEqual(nutritional_totals['Energy']['unit'], 'kcal')
        
        # Vitamin C shouldn't be in the totals since it's 0 for both ingredients
        # but we should check both ways to be sure (api might return 0 values or exclude them)
        if 'Vitamin C' in nutritional_totals:
            self.assertEqual(nutritional_totals['Vitamin C']['amount'], 0)
            self.assertEqual(nutritional_totals['Vitamin C']['unit'], 'mg')

    def test_create_meal_component(self):
        """Test creating a new meal component."""
        url = reverse('mealcomponent-list')
        data = {
            'name': 'Chicken Broccoli Mix',
            'category_tag': 'Dinner',
            'description_recipe': 'A healthy mix of chicken and broccoli',
            'frequency': MealComponentFrequency.PER_MEAL_BOX,
            'ingredients_usage_write': [
                {
                    'ingredient': self.chicken.id,
                    'quantity': 120.0
                },
                {
                    'ingredient': self.broccoli.id,
                    'quantity': 150.0
                }
            ]
        }
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(MealComponent.objects.count(), 3)
        
        # Check that our new meal component exists in the database
        new_component = MealComponent.objects.get(name='Chicken Broccoli Mix')
        self.assertEqual(new_component.category_tag, 'Dinner')
        
        # Check that ingredient usages were created
        usages = new_component.ingredientusage_set.all()
        self.assertEqual(usages.count(), 2)
        
        # Verify ingredient quantities
        for usage in usages:
            if usage.ingredient.id == self.chicken.id:
                self.assertEqual(usage.quantity, 120.0)
            elif usage.ingredient.id == self.broccoli.id:
                self.assertEqual(usage.quantity, 150.0)

    def test_update_meal_component(self):
        """Test updating an existing meal component."""
        url = reverse('mealcomponent-detail', kwargs={'pk': self.meal1.pk})
        data = {
            'name': 'Chicken and Rice Bowl',  # Same name
            'category_tag': 'Dinner',  # Changed from Lunch to Dinner
            'description_recipe': 'A simple dinner bowl with chicken and rice',  # Changed description
            'frequency': MealComponentFrequency.PER_MEAL_BOX,
            'ingredients_usage_write': [
                {
                    'ingredient': self.chicken.id,
                    'quantity': 180.0  # Changed from 150g to 180g
                },
                {
                    'ingredient': self.rice.id,
                    'quantity': 150.0  # Changed from 200g to 150g
                }
            ]
        }
        response = self.client.put(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the meal component from the database
        self.meal1.refresh_from_db()
        self.assertEqual(self.meal1.category_tag, 'Dinner')
        self.assertEqual(self.meal1.description_recipe, 'A simple dinner bowl with chicken and rice')
        
        # Check that ingredient usages were updated
        usages = self.meal1.ingredientusage_set.all()
        self.assertEqual(usages.count(), 2)
        
        # Verify updated ingredient quantities
        for usage in usages:
            if usage.ingredient.id == self.chicken.id:
                self.assertEqual(usage.quantity, 180.0)
            elif usage.ingredient.id == self.rice.id:
                self.assertEqual(usage.quantity, 150.0)

    def test_partial_update_meal_component(self):
        """Test partially updating a meal component."""
        url = reverse('mealcomponent-detail', kwargs={'pk': self.meal1.pk})
        data = {
            'category_tag': 'Dinner'  # Only update the category tag
        }
        response = self.client.patch(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh the meal component from the database
        self.meal1.refresh_from_db()
        self.assertEqual(self.meal1.category_tag, 'Dinner')
        self.assertEqual(self.meal1.name, 'Chicken and Rice Bowl')  # Name should remain unchanged
        
        # Ingredient usages should remain unchanged
        usages = self.meal1.ingredientusage_set.all()
        self.assertEqual(usages.count(), 2)
        
        chicken_usage = usages.filter(ingredient=self.chicken).first()
        rice_usage = usages.filter(ingredient=self.rice).first()
        self.assertEqual(chicken_usage.quantity, 150.0)  # Original value
        self.assertEqual(rice_usage.quantity, 200.0)  # Original value

    def test_delete_meal_component(self):
        """Test deleting an existing meal component."""
        url = reverse('mealcomponent-detail', kwargs={'pk': self.meal2.pk})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(MealComponent.objects.count(), 1)
        
        # Check that the deleted meal component does not exist
        with self.assertRaises(MealComponent.DoesNotExist):
            MealComponent.objects.get(pk=self.meal2.pk)
        
        # Check that associated ingredient usages were also deleted
        self.assertEqual(IngredientUsage.objects.filter(meal_component=self.meal2).count(), 0)

    def test_search_by_name(self):
        """Test searching meal components by name."""
        url = reverse('mealcomponent-list') + '?search=chicken'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is turned off
        self.assertFalse('results' in response.data, "Response should not be paginated")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Chicken and Rice Bowl')

    def test_search_by_category_tag(self):
        """Test searching meal components by category tag."""
        url = reverse('mealcomponent-list') + '?search=side'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is turned off
        self.assertFalse('results' in response.data, "Response should not be paginated")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Broccoli Side')

    def test_ordering_by_name(self):
        """Test ordering meal components by name."""
        # Create another meal component to test ordering
        MealComponent.objects.create(
            name="Avocado Toast",
            category_tag="Breakfast",
            description_recipe="Simple avocado toast",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        url = reverse('mealcomponent-list') + '?ordering=name'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is turned off
        self.assertFalse('results' in response.data, "Response should not be paginated")
        self.assertEqual(len(response.data), 3)
        
        # Check the order of meal components
        self.assertEqual(response.data[0]['name'], 'Avocado Toast')
        self.assertEqual(response.data[1]['name'], 'Broccoli Side')
        self.assertEqual(response.data[2]['name'], 'Chicken and Rice Bowl')
        
        # Test reverse ordering
        url = reverse('mealcomponent-list') + '?ordering=-name'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is turned off
        self.assertFalse('results' in response.data, "Response should not be paginated")
        self.assertEqual(len(response.data), 3)
        self.assertEqual(response.data[0]['name'], 'Chicken and Rice Bowl')
        self.assertEqual(response.data[1]['name'], 'Broccoli Side')
        self.assertEqual(response.data[2]['name'], 'Avocado Toast')

    def test_ordering_by_category_tag(self):
        """Test ordering meal components by category tag."""
        # Create another meal component to test ordering
        MealComponent.objects.create(
            name="Avocado Toast",
            category_tag="Breakfast",
            description_recipe="Simple avocado toast",
            frequency=MealComponentFrequency.PER_MEAL_BOX
        )
        
        url = reverse('mealcomponent-list') + '?ordering=category_tag'
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Assuming pagination is turned off
        self.assertFalse('results' in response.data, "Response should not be paginated")
        self.assertEqual(len(response.data), 3)
        
        # Check the order of meal components (alphabetical by category_tag)
        categories = [component['category_tag'] for component in response.data]
        self.assertEqual(categories, ['Breakfast', 'Lunch', 'Side'])
