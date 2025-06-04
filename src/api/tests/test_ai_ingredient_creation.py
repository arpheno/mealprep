import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from api.models import Ingredient, Nutrient, IngredientNutrientLink, FoodPortion, IngredientFoodCategory
from api.services import AIFoodGenerationService
from api.domain_services import IngredientCreationDomainService


class TestAIFoodGenerationService(TestCase):
    """Test cases for the AI food generation service."""
    
    def setUp(self):
        """Set up test data."""
        # Create test nutrients
        self.energy_nutrient = Nutrient.objects.create(
            name='Energy',
            unit='kcal',
            fdc_nutrient_id=1008,
            category='ENERGY'
        )
        self.protein_nutrient = Nutrient.objects.create(
            name='Protein',
            unit='g',
            fdc_nutrient_id=1003,
            category='MACRO'
        )

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_service_initialization_with_api_key(self):
        """Test that service initializes correctly with API key."""
        service = AIFoodGenerationService()
        self.assertIsNotNone(service.client)
        self.assertIn('1008', service.nutrient_mapping)
        self.assertEqual(service.nutrient_mapping['1008'], 'Energy')

    def test_service_initialization_without_api_key(self):
        """Test that service raises error without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError) as cm:
                AIFoodGenerationService()
            self.assertIn('OPENAI_API_KEY', str(cm.exception))

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_get_nutrient_mapping_for_database(self):
        """Test nutrient mapping between FDC IDs and database IDs."""
        service = AIFoodGenerationService()
        mapping = service.get_nutrient_mapping_for_database()
        
        self.assertIn('1008', mapping)
        self.assertIn('1003', mapping)
        self.assertEqual(mapping['1008'], self.energy_nutrient.id)
        self.assertEqual(mapping['1003'], self.protein_nutrient.id)

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('api.services.OpenAI')
    def test_generate_food_data_success(self, mock_openai):
        """Test successful food data generation."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "fdcId": -12345,
            "description": "Test Food",
            "foodClass": "ChatGPT",
            "foodCategory": {"description": "Test Category", "code": "9999", "id": -1},
            "foodNutrients": [
                {"nutrient": {"id": 1008, "unitName": "kcal"}, "amount": 100.0}
            ],
            "foodPortions": [
                {
                    "id": -1901,
                    "amount": 1.0,
                    "gramWeight": 100.0,
                    "modifier": "test",
                    "portionDescription": "100 g",
                    "sequenceNumber": 1,
                    "measureUnit": {"id": -190101, "name": "g", "abbreviation": "g"}
                }
            ]
        })
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        service = AIFoodGenerationService()
        result = service.generate_food_data("test food description")
        
        self.assertEqual(result['description'], "Test Food")
        self.assertEqual(result['foodClass'], "ChatGPT")
        self.assertEqual(len(result['foodNutrients']), 1)
        self.assertEqual(len(result['foodPortions']), 1)

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_validate_food_data_success(self):
        """Test successful food data validation."""
        service = AIFoodGenerationService()
        
        valid_data = {
            "fdcId": -12345,
            "description": "Test Food",
            "foodClass": "ChatGPT",
            "foodCategory": {"description": "Test", "code": "9999", "id": -1},
            "foodNutrients": [{"nutrient": {"id": 1008}, "amount": 100.0}],
            "foodPortions": [{"id": -1, "amount": 1.0, "gramWeight": 100.0}]
        }
        
        # Should not raise any exception
        service._validate_food_data(valid_data)

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_validate_food_data_invalid_class(self):
        """Test validation failure for wrong food class."""
        service = AIFoodGenerationService()
        
        invalid_data = {
            "fdcId": -12345,
            "description": "Test Food",
            "foodClass": "NotChatGPT",  # Wrong class
            "foodCategory": {"description": "Test"},
            "foodNutrients": [{"nutrient": {"id": 1008}, "amount": 100.0}],
            "foodPortions": [{"id": -1, "amount": 1.0}]
        }
        
        with self.assertRaises(ValueError) as cm:
            service._validate_food_data(invalid_data)
        self.assertIn('foodClass must be', str(cm.exception))


class TestIngredientCreationDomainService(TestCase):
    """Test cases for the ingredient creation domain service."""
    
    def setUp(self):
        """Set up test data."""
        self.energy_nutrient = Nutrient.objects.create(
            name='Energy',
            unit='kcal',
            fdc_nutrient_id=1008,
            category='ENERGY'
        )
        self.protein_nutrient = Nutrient.objects.create(
            name='Protein',
            unit='g',
            fdc_nutrient_id=1003,
            category='MACRO'
        )

    def test_map_food_category(self):
        """Test food category mapping logic."""
        service = IngredientCreationDomainService()
        
        # Test known mappings
        self.assertEqual(
            service._map_food_category("Poultry Products"),
            IngredientFoodCategory.PROTEIN_ANIMAL
        )
        self.assertEqual(
            service._map_food_category("Legume Products"),
            IngredientFoodCategory.LEGUME
        )
        self.assertEqual(
            service._map_food_category("Unknown Category"),
            IngredientFoodCategory.OTHER
        )

    def test_validate_ingredient_uniqueness_exact_match(self):
        """Test uniqueness validation with exact match."""
        # Create existing ingredient
        Ingredient.objects.create(
            name="Test Ingredient",
            fdc_id=-123,
            food_class="ChatGPT"
        )
        
        service = IngredientCreationDomainService()
        is_unique, message = service.validate_ingredient_uniqueness("Test Ingredient")
        
        self.assertFalse(is_unique)
        self.assertIn("exact name", message)

    def test_validate_ingredient_uniqueness_similar_match(self):
        """Test uniqueness validation with similar match."""
        # Create existing ingredient
        Ingredient.objects.create(
            name="Test Food Item",
            fdc_id=-123,
            food_class="ChatGPT"
        )
        
        service = IngredientCreationDomainService()
        is_unique, message = service.validate_ingredient_uniqueness("Test Food")
        
        self.assertTrue(is_unique)
        self.assertIn("Similar ingredients found", message)

    def test_validate_ingredient_uniqueness_no_match(self):
        """Test uniqueness validation with no match."""
        service = IngredientCreationDomainService()
        is_unique, message = service.validate_ingredient_uniqueness("Completely Unique Food")
        
        self.assertTrue(is_unique)
        self.assertIn("No similar ingredients found", message)

    @patch('api.domain_services.AIFoodGenerationService')
    def test_create_ingredient_from_description_success(self, mock_ai_service):
        """Test successful ingredient creation from description."""
        # Mock AI service response
        mock_ai_data = {
            "fdcId": -12345,
            "description": "Test AI Food",
            "foodClass": "ChatGPT",
            "foodCategory": {"description": "Legume Products", "code": "LEGUME", "id": -1},
            "foodNutrients": [
                {"nutrient": {"id": 1008, "unitName": "kcal"}, "amount": 100.0},
                {"nutrient": {"id": 1003, "unitName": "g"}, "amount": 10.0}
            ],
            "foodPortions": [
                {
                    "id": -1901,
                    "amount": 1.0,
                    "gramWeight": 100.0,
                    "modifier": "test",
                    "portionDescription": "100 g",
                    "sequenceNumber": 1,
                    "measureUnit": {"id": -190101, "name": "g", "abbreviation": "g"}
                }
            ]
        }
        
        mock_service_instance = Mock()
        mock_service_instance.generate_food_data.return_value = mock_ai_data
        mock_service_instance.get_nutrient_mapping_for_database.return_value = {
            '1008': self.energy_nutrient.id,
            '1003': self.protein_nutrient.id
        }
        mock_ai_service.return_value = mock_service_instance
        
        service = IngredientCreationDomainService()
        ingredient = service.create_ingredient_from_description("test food")
        
        # Verify ingredient creation
        self.assertEqual(ingredient.name, "Test AI Food")
        self.assertEqual(ingredient.food_class, "ChatGPT")
        self.assertEqual(ingredient.category, IngredientFoodCategory.LEGUME)
        
        # Verify nutrient links
        nutrient_links = ingredient.ingredientnutrientlink_set.all()
        self.assertEqual(len(nutrient_links), 2)
        
        # Verify food portions
        food_portions = ingredient.food_portions.all()
        self.assertEqual(len(food_portions), 1)
        self.assertEqual(food_portions[0].gram_weight, 100.0)


class TestAIIngredientCreationAPIView(TestCase):
    """Test cases for the AI ingredient creation API endpoint."""
    
    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        self.url = reverse('ai-ingredient-create')
        
        # Create test nutrients
        self.energy_nutrient = Nutrient.objects.create(
            name='Energy',
            unit='kcal',
            fdc_nutrient_id=1008,
            category='ENERGY'
        )

    def test_create_ingredient_missing_description(self):
        """Test API response for missing description."""
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Description is required', response.data['error'])

    def test_create_ingredient_short_description(self):
        """Test API response for too short description."""
        response = self.client.post(self.url, {'description': 'ab'})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('at least 3 characters', response.data['error'])

    @patch('api.views.IngredientCreationDomainService')
    def test_create_ingredient_success(self, mock_domain_service):
        """Test successful ingredient creation via API."""
        # Mock domain service
        mock_ingredient = Mock()
        mock_ingredient.id = 1
        mock_ingredient.name = "Test Food"
        mock_ingredient.fdc_id = -12345
        
        mock_service_instance = Mock()
        mock_service_instance.validate_ingredient_uniqueness.return_value = (True, "No similar ingredients found")
        mock_service_instance.create_ingredient_from_description.return_value = mock_ingredient
        mock_domain_service.return_value = mock_service_instance
        
        # Mock serializer response
        with patch('api.views.IngredientSerializer') as mock_serializer:
            mock_serializer.return_value.data = {
                'id': 1,
                'name': 'Test Food',
                'fdc_id': -12345
            }
            
            response = self.client.post(self.url, {'description': 'test food description'})
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('ingredient', response.data)
        self.assertIn('uniqueness_check', response.data)

    @patch('api.views.IngredientCreationDomainService')
    def test_create_ingredient_domain_service_error(self, mock_domain_service):
        """Test API response when domain service raises an error."""
        mock_service_instance = Mock()
        mock_service_instance.validate_ingredient_uniqueness.return_value = (True, "No similar ingredients found")
        mock_service_instance.create_ingredient_from_description.side_effect = Exception("AI service error")
        mock_domain_service.return_value = mock_service_instance
        
        response = self.client.post(self.url, {'description': 'test food description'})
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(response.data['success'])
        self.assertIn('Failed to create ingredient', response.data['error'])


class TestValidateIngredientDescriptionView(TestCase):
    """Test cases for the ingredient description validation endpoint."""
    
    def setUp(self):
        """Set up test client."""
        self.client = APIClient()
        self.url = reverse('validate-ingredient-description')

    def test_validate_description_missing(self):
        """Test validation with missing description."""
        response = self.client.post(self.url, {})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Description is required', response.data['error'])

    def test_validate_description_success(self):
        """Test successful description validation."""
        response = self.client.post(self.url, {'description': 'test food'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_unique', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['description'], 'test food')


@pytest.mark.integration
class TestAIIngredientCreationIntegration(TestCase):
    """Integration tests for the complete AI ingredient creation flow."""
    
    def setUp(self):
        """Set up test data."""
        # Create essential nutrients that the AI service expects
        essential_nutrients = [
            ('Energy', 'kcal', 1008),
            ('Protein', 'g', 1003),
            ('Total lipid (fat)', 'g', 1004),
            ('Carbohydrate, by difference', 'g', 1005),
        ]
        
        for name, unit, fdc_id in essential_nutrients:
            Nutrient.objects.create(
                name=name,
                unit=unit,
                fdc_nutrient_id=fdc_id,
                category='MACRO'
            )

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    @patch('api.services.OpenAI')
    def test_complete_ingredient_creation_flow(self, mock_openai):
        """Test the complete flow from API request to database storage."""
        # Mock realistic OpenAI response
        mock_response_data = {
            "fdcId": -54321,
            "description": "Kidney Beans, Canned",
            "foodClass": "ChatGPT",
            "foodCategory": {
                "description": "Legume Products",
                "code": "LEGUME",
                "id": -1
            },
            "foodNutrients": [
                {"nutrient": {"id": 1008, "unitName": "kcal"}, "amount": 127.0},
                {"nutrient": {"id": 1003, "unitName": "g"}, "amount": 8.7},
                {"nutrient": {"id": 1004, "unitName": "g"}, "amount": 0.5},
                {"nutrient": {"id": 1005, "unitName": "g"}, "amount": 23.0}
            ],
            "foodPortions": [
                {
                    "id": -1901,
                    "amount": 1.0,
                    "gramWeight": 100.0,
                    "modifier": "canned, drained",
                    "portionDescription": "100 g",
                    "sequenceNumber": 1,
                    "measureUnit": {"id": -190101, "name": "g", "abbreviation": "g"}
                }
            ]
        }
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(mock_response_data)
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        # Make API request
        client = APIClient()
        url = reverse('ai-ingredient-create')
        response = client.post(url, {'description': 'kidneybohnen, dose'})
        
        # Verify API response
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify database storage
        ingredient = Ingredient.objects.get(name="Kidney Beans, Canned")
        self.assertEqual(ingredient.food_class, "ChatGPT")
        self.assertEqual(ingredient.category, IngredientFoodCategory.LEGUME)
        
        # Verify nutrient links
        nutrient_links = ingredient.ingredientnutrientlink_set.count()
        self.assertEqual(nutrient_links, 4)
        
        # Verify food portions
        food_portions = ingredient.food_portions.count()
        self.assertEqual(food_portions, 1) 