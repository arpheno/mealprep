import os
import json
import logging
import random
from typing import Dict, Any, Optional
from openai import OpenAI
from django.conf import settings
from .models import Nutrient

logger = logging.getLogger(__name__)


class AIFoodGenerationService:
    """
    Service for generating food nutritional data using OpenAI API.
    Follows clean architecture principles by separating external API concerns.
    """
    
    def __init__(self):
        """
        Initialize the OpenAI client with API key from environment.
        
        Raises:
            ValueError: If OpenAI API key is not configured
        """
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        
        self.client = OpenAI(api_key=api_key)
        
        # Nutrient mapping from FDC IDs to our system
        self.nutrient_mapping = {
            "1008": "Energy",
            "1003": "Protein", 
            "1004": "Total lipid (fat)",
            "1258": "Fatty acids, total saturated",
            "1292": "Fatty acids, total monounsaturated", 
            "1293": "Fatty acids, total polyunsaturated",
            "1005": "Carbohydrate, by difference",
            "2000": "Sugars, total",
            "1093": "Sodium, Na",
            "1158": "PUFA 18:3 n-3 (ALA)",
            "1278": "PUFA 20:5 n-3 (EPA)", 
            "1279": "PUFA 22:6 n-3 (DHA)",
            "1087": "Calcium, Ca",
            "1089": "Iron, Fe",
            "1090": "Magnesium, Mg",
            "1091": "Phosphorus, P",
            "1092": "Potassium, K", 
            "1095": "Zinc, Zn",
            "1098": "Copper, Cu",
            "1101": "Manganese, Mn",
            "1103": "Selenium, Se",
            "1100": "Iodine, I",
            "1106": "Vitamin A, RAE",
            "1107": "Carotene, beta",
            "1109": "Vitamin E",
            "1190": "Folate, DFE",
            "1165": "Thiamin (B1)",
            "1166": "Riboflavin (B2)", 
            "1167": "Niacin (B3 equivalent)",
            "1170": "Pantothenic acid (B5)",
            "1175": "Vitamin B-6",
            "1176": "Biotin (B7)",
            "1178": "Vitamin B-12",
            "1185": "Vitamin K",
            "1114": "Vitamin D",
            "1102": "Molybdenum, Mo",
            "1253": "Cholesterol",
            "1180": "Choline"
        }

    def _get_prompt_template(self) -> str:
        """
        Returns the OpenAI prompt template for food generation.
        
        Returns:
            str: The formatted prompt template
        """
        nutrient_list = json.dumps(self.nutrient_mapping, indent=2)
        
        return f"""I'm building a meal prepping app and tracking the following nutrients (ID:NAME):
{nutrient_list}

The user will provide information and instructions to build a new entry in my food database. This is the desired structure:
{{
    "fdcId": -3919,
    "description": "Hähnchenbrustfilet, roh, ohne Haut (Deutschland)",
    "foodClass": "ChatGPT",
    "foodCategory": {{
        "description": "Poultry Products",
        "code": "9999",
        "id": -1
    }},
    "foodNutrients": [
        {{
            "nutrient": {{
                "id": 1008,
                "unitName": "kcal"
            }},
            "amount": 107.0
        }}
    ],
    "foodPortions": [
        {{
            "id": -1901,
            "amount": 1.0,
            "gramWeight": 100.0,
            "modifier": "raw, skinless",
            "portionDescription": "100 g",
            "sequenceNumber": 1,
            "measureUnit": {{
                "id": -190101,
                "name": "g",
                "abbreviation": "g"
            }}
        }}
    ]
}}

Do not include json comments, output a pojo. Choose a random negative 5 digit id for fdcId and related ids. Make sure to include all nutrients from the list above with realistic values based on the food description."""

    def generate_food_data(self, user_description: str, image_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate food nutritional data using OpenAI API.
        
        Args:
            user_description (str): User's description of the food
            image_data (Optional[str]): Base64 encoded image data (future enhancement)
            
        Returns:
            Dict[str, Any]: Generated food data in FDC format
            
        Raises:
            Exception: If OpenAI API call fails or response is invalid
        """
        try:
            prompt = self._get_prompt_template()
            user_message = f"Please create a food database entry for: {user_description}"
            
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message}
            ]
            
            # Add image support for future enhancement
            if image_data:
                messages[-1]["content"] = [
                    {"type": "text", "text": user_message},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}
                    }
                ]
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise Exception("OPENAI_API_KEY environment variable not set")
            response = self.client.chat.completions.create(
                model="gpt-4o" if image_data else "o4-mini",
                messages=messages,
                temperature=0.3,  # Lower temperature for more consistent nutritional data
                max_tokens=2000
            )
            
            content = response.choices[0].message.content.strip()
            
            # Parse JSON response
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            food_data = json.loads(content)
            
            # Validate required fields
            self._validate_food_data(food_data)
            
            logger.info(f"Successfully generated food data for: {user_description}")
            return food_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse OpenAI response as JSON: {e}")
            raise Exception(f"Invalid JSON response from AI: {e}")
        except Exception as e:
            logger.error(f"Failed to generate food data: {e}")
            raise Exception(f"AI food generation failed: {e}")

    def _validate_food_data(self, food_data: Dict[str, Any]) -> None:
        """
        Validate the generated food data structure.
        
        Args:
            food_data (Dict[str, Any]): Generated food data to validate
            
        Raises:
            ValueError: If food data structure is invalid
        """
        required_fields = ['fdcId', 'description', 'foodClass', 'foodCategory', 'foodNutrients', 'foodPortions']
        
        for field in required_fields:
            if field not in food_data:
                raise ValueError(f"Missing required field: {field}")
        
        if food_data['foodClass'] != 'ChatGPT':
            raise ValueError("foodClass must be 'ChatGPT' for AI-generated foods")
        
        if not isinstance(food_data['foodNutrients'], list) or len(food_data['foodNutrients']) == 0:
            raise ValueError("foodNutrients must be a non-empty list")
        
        if not isinstance(food_data['foodPortions'], list) or len(food_data['foodPortions']) == 0:
            raise ValueError("foodPortions must be a non-empty list")

    def get_nutrient_mapping_for_database(self) -> Dict[str, int]:
        """
        Get mapping from nutrient names to database IDs.
        
        Returns:
            Dict[str, int]: Mapping of nutrient names to database nutrient IDs
        """
        mapping = {}
        
        for fdc_id, nutrient_name in self.nutrient_mapping.items():
            try:
                # Try to find by canonical name first, then by alias
                nutrient = Nutrient.objects.filter_by_name_or_alias(nutrient_name).first()
                if nutrient:
                    mapping[fdc_id] = nutrient.id
                else:
                    logger.warning(f"Nutrient '{nutrient_name}' not found in database")
            except Exception as e:
                logger.error(f"Error mapping nutrient '{nutrient_name}': {e}")
        
        return mapping 