#!/bin/bash

# Test script for AI Ingredient Creation API endpoints
# 
# Usage: ./test_ai_api.sh
# 
# Prerequisites:
# - Django server running (e.g., via docker-compose up)
# - OpenAI API key configured
# - curl installed

set -e

# Configuration
API_BASE_URL="http://localhost:8000/api"
CONTENT_TYPE="Content-Type: application/json"

echo "🧪 Testing AI Ingredient Creation API"
echo "======================================"

# Test 1: Validate ingredient description
echo -e "\n1️⃣  Testing ingredient validation..."
echo "Validating description: 'kidneybohnen, dose'"

VALIDATION_RESPONSE=$(curl -s -X POST \
  "${API_BASE_URL}/ingredients/validate/" \
  -H "${CONTENT_TYPE}" \
  -d '{"description": "kidneybohnen, dose"}')

echo "Response:"
echo "${VALIDATION_RESPONSE}" | python3 -m json.tool

# Test 2: Create AI ingredient
echo -e "\n2️⃣  Testing AI ingredient creation..."
echo "Creating ingredient from description: 'kidneybohnen, dose'"

CREATION_RESPONSE=$(curl -s -X POST \
  "${API_BASE_URL}/ingredients/ai-create/" \
  -H "${CONTENT_TYPE}" \
  -d '{"description": "kidneybohnen, dose"}')

echo "Response:"
echo "${CREATION_RESPONSE}" | python3 -m json.tool

# Extract ingredient ID from response for further tests
INGREDIENT_ID=$(echo "${CREATION_RESPONSE}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('success') and 'ingredient' in data:
        print(data['ingredient']['id'])
    else:
        print('N/A')
except:
    print('N/A')
")

if [ "${INGREDIENT_ID}" != "N/A" ]; then
    echo -e "\n✅ Successfully created ingredient with ID: ${INGREDIENT_ID}"
    
    # Test 3: Retrieve the created ingredient
    echo -e "\n3️⃣  Testing ingredient retrieval..."
    echo "Fetching ingredient details..."
    
    INGREDIENT_DETAILS=$(curl -s "${API_BASE_URL}/ingredients/${INGREDIENT_ID}/")
    echo "Response:"
    echo "${INGREDIENT_DETAILS}" | python3 -m json.tool
    
else
    echo -e "\n❌ Failed to create ingredient or extract ID"
fi

# Test 4: Search for ChatGPT ingredients
echo -e "\n4️⃣  Testing ingredient search..."
echo "Searching for ChatGPT ingredients..."

SEARCH_RESPONSE=$(curl -s "${API_BASE_URL}/ingredients/search/?name=ChatGPT")
echo "Response:"
echo "${SEARCH_RESPONSE}" | python3 -m json.tool

# Test 5: List all ingredients (limited)
echo -e "\n5️⃣  Testing ingredient list..."
echo "Fetching first few ingredients..."

LIST_RESPONSE=$(curl -s "${API_BASE_URL}/ingredients/?limit=5")
echo "Response (first 5 ingredients):"
echo "${LIST_RESPONSE}" | python3 -m json.tool

echo -e "\n✅ API testing completed!"
echo -e "\n💡 Tips:"
echo "   - Check the Django logs for detailed information"
echo "   - Use the frontend to interact with these endpoints"
echo "   - Run 'make export-chatgpt-foods' to save your custom ingredients" 