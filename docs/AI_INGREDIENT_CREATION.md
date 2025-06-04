# AI Ingredient Creation

This feature allows users to create custom ingredients for their meal prep by simply describing the food or taking a picture. The system uses OpenAI's GPT models to generate realistic nutritional information based on the description.

## Overview

The AI ingredient creation system follows clean architecture principles with clear separation of concerns:

- **API Layer**: REST endpoints for frontend integration
- **Domain Services**: Business logic for ingredient creation
- **Infrastructure Services**: OpenAI API integration
- **Data Layer**: Django models for persistence

## Features

- ✅ Create ingredients from text descriptions (e.g., "kidneybohnen, dose")
- 🔮 Future: Create ingredients from food label images
- ✅ Automatic nutritional data generation for 40+ nutrients
- ✅ Smart food category mapping
- ✅ Duplicate detection and warnings
- ✅ Export/import system for version control

## API Endpoints

### Create AI Ingredient

**POST** `/api/ingredients/ai-create/`

Create a new ingredient using AI generation.

**Request Body:**
```json
{
  "description": "kidneybohnen, dose",
  "image": "base64_encoded_image_data" // Optional, for future use
}
```

**Response (Success):**
```json
{
  "ingredient": {
    "id": 123,
    "name": "Kidney Beans, Canned (German)",
    "fdc_id": -54321,
    "food_class": "ChatGPT",
    "category": "LEGUME",
    "notes": "AI-generated ingredient. Original category: Legume Products"
  },
  "uniqueness_check": {
    "is_unique": true,
    "message": "Similar ingredients found: Kidney beans raw, Red kidney beans"
  },
  "success": true,
  "message": "Successfully created ingredient: Kidney Beans, Canned (German)"
}
```

### Validate Description

**POST** `/api/ingredients/validate/`

Check if a description would create a duplicate ingredient.

**Request Body:**
```json
{
  "description": "kidneybohnen, dose"
}
```

**Response:**
```json
{
  "is_unique": true,
  "message": "No similar ingredients found.",
  "description": "kidneybohnen, dose"
}
```

## Usage Examples

### Frontend Integration

```javascript
// Create ingredient from description
const createIngredient = async (description) => {
  try {
    const response = await fetch('/api/ingredients/ai-create/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ description })
    });
    
    const data = await response.json();
    
    if (data.success) {
      console.log('Created ingredient:', data.ingredient);
      
      // Show warning if similar ingredients exist
      if (!data.uniqueness_check.is_unique) {
        alert(`Warning: ${data.uniqueness_check.message}`);
      }
    } else {
      console.error('Error:', data.error);
    }
  } catch (error) {
    console.error('Network error:', error);
  }
};

// Validate before creating
const validateDescription = async (description) => {
  const response = await fetch('/api/ingredients/validate/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description })
  });
  
  return await response.json();
};
```

### Django Management Commands

```bash
# Export all ChatGPT foods to JSON for version control
make export-chatgpt-foods

# Import ChatGPT foods from JSON file
make import-chatgpt-foods

# With custom options
docker-compose exec web python manage.py export_chatgpt_foods \
  --output-file data/my_custom_foods.json \
  --pretty \
  --include-metadata

docker-compose exec web python manage.py import_chatgpt_foods \
  data/my_custom_foods.json \
  --update-existing \
  --dry-run
```

## Configuration

### Required Environment Variables

```bash
# OpenAI API key (required)
OPENAI_API_KEY=sk-your-openai-api-key-here
```

### Nutrient Mapping

The system tracks 40+ nutrients based on FDC nutrient IDs:

- **Macronutrients**: Energy, Protein, Fats, Carbohydrates
- **Vitamins**: A, B-complex, C, D, E, K
- **Minerals**: Calcium, Iron, Magnesium, Zinc, etc.
- **Fatty Acids**: Omega-3s (ALA, EPA, DHA), Saturated, etc.

## Architecture Details

### Services

**AIFoodGenerationService** (`src/api/services.py`)
- Handles OpenAI API communication
- Validates AI responses
- Maps FDC nutrient IDs to database nutrients

**IngredientCreationDomainService** (`src/api/domain_services.py`)
- Orchestrates ingredient creation process
- Handles business rules and validation
- Manages database transactions

### Data Flow

1. **User Input** → API endpoint receives description
2. **Validation** → Check for duplicates and validate input
3. **AI Generation** → OpenAI generates nutritional data
4. **Processing** → Map AI data to Django models
5. **Storage** → Save ingredient with nutrients and portions
6. **Response** → Return created ingredient data

### Food Categories

AI-generated foods are automatically categorized:

- `PROTEIN_ANIMAL` - Meat, fish, poultry
- `LEGUME` - Beans, lentils, peas
- `GRAIN_CEREAL` - Bread, rice, pasta
- `VEGETABLE_*` - Various vegetable types
- `FRUIT` - All fruits
- `DAIRY` - Milk products
- `NUT_SEED` - Nuts and seeds
- `OIL_FAT` - Oils and fats
- `OTHER` - Fallback category

## Quality and Testing

### Test Coverage

- Unit tests for all services and API endpoints
- Integration tests for complete workflows
- Mocked OpenAI responses for consistent testing
- Validation of data persistence and mapping

### Run Tests

```bash
# Run all tests
make tests

# Run specific test file
PYTHONPATH=src python -m pytest src/api/tests/test_ai_ingredient_creation.py -v

# Run with coverage
PYTHONPATH=src python -m pytest --cov=api src/api/tests/
```

## Version Control Integration

ChatGPT-generated foods can be exported to JSON and committed to version control:

```bash
# Export current state
make export-chatgpt-foods

# Commit the JSON file
git add data/chatgpt_foods.json
git commit -m "Add new AI-generated ingredients"

# Team members can import
make import-chatgpt-foods
```

**JSON Structure:**
```json
{
  "metadata": {
    "export_timestamp": "2024-01-15T10:30:00",
    "total_ingredients": 5,
    "export_version": "1.0"
  },
  "ingredients": [
    {
      "fdcId": -54321,
      "description": "Kidney Beans, Canned",
      "foodClass": "ChatGPT",
      "foodCategory": {
        "description": "Legume Products",
        "code": "LEGUME"
      },
      "foodNutrients": [...],
      "foodPortions": [...]
    }
  ]
}
```

## Troubleshooting

### Common Issues

1. **Missing OpenAI API Key**
   ```
   Error: OPENAI_API_KEY environment variable is required
   ```
   Solution: Set the environment variable in your `.env` file

2. **Nutrient Not Found Warnings**
   ```
   WARNING: Nutrient 'XYZ' not found in database
   ```
   Solution: Import authoritative nutrients first: `make import-nutrients`

3. **AI Generation Failures**
   - Check OpenAI API quota and billing
   - Verify description is clear and food-related
   - Check network connectivity

### Logging

The system logs all AI generation activities:

```bash
# View logs
docker-compose logs -f web | grep "AI"

# Common log messages:
# INFO: Generating AI food data for: kidneybohnen, dose
# INFO: Successfully created ingredient: Kidney Beans, Canned
# WARNING: Nutrient 'Unknown Nutrient' not found in database
```

## Future Enhancements

- 📸 **Image Recognition**: Upload food label photos for automatic data extraction
- 🌍 **Multi-language Support**: Support for additional European languages
- 🔍 **Fuzzy Matching**: Better duplicate detection using similarity algorithms
- 📊 **Confidence Scores**: AI confidence ratings for generated nutritional data
- 🔄 **Batch Processing**: Create multiple ingredients from a list
- 🏷️ **Custom Tags**: User-defined tags and categories 