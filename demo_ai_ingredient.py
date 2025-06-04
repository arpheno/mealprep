#!/usr/bin/env python
"""
Demo script for AI Ingredient Creation functionality.

This script demonstrates how to use the new AI ingredient creation feature
to create custom ingredients from simple descriptions.

Usage:
    python demo_ai_ingredient.py

Requirements:
    - OpenAI API key set in environment variable OPENAI_API_KEY
    - Django project properly set up with nutrients imported
"""

import os
import sys
import django

# Add the src directory to Python path
sys.path.insert(0, 'src')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mealprep_project.settings')
django.setup()

from api.domain_services import IngredientCreationDomainService
from api.models import Ingredient, Nutrient


def demo_ai_ingredient_creation():
    """Demonstrate AI ingredient creation with a real example."""
    
    print("🤖 AI Ingredient Creation Demo")
    print("=" * 50)
    
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("Please set your OpenAI API key before running this demo.")
        return
    
    # Check if we have nutrients in the database
    nutrient_count = Nutrient.objects.count()
    print(f"📊 Found {nutrient_count} nutrients in database")
    
    if nutrient_count == 0:
        print("❌ Error: No nutrients found in database")
        print("Please import nutrients first using: make import-nutrients")
        return
    
    # Initialize the domain service
    print("\n🚀 Initializing AI ingredient creation service...")
    try:
        domain_service = IngredientCreationDomainService()
        print("✅ Service initialized successfully")
    except Exception as e:
        print(f"❌ Error initializing service: {e}")
        return
    
    # Test description
    test_description = "kidneybohnen, dose"
    print(f"\n🥫 Creating ingredient for: '{test_description}'")
    
    # Check uniqueness first
    print("🔍 Checking for duplicate ingredients...")
    is_unique, message = domain_service.validate_ingredient_uniqueness(test_description)
    print(f"Uniqueness check: {message}")
    
    if not is_unique:
        print("⚠️  Warning: This ingredient already exists!")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Demo cancelled.")
            return
    
    # Create the ingredient
    print("\n🎯 Calling OpenAI API to generate nutritional data...")
    try:
        ingredient = domain_service.create_ingredient_from_description(test_description)
        print("✅ Ingredient created successfully!")
        
        # Display results
        print(f"\n📋 Created Ingredient Details:")
        print(f"   ID: {ingredient.id}")
        print(f"   Name: {ingredient.name}")
        print(f"   FDC ID: {ingredient.fdc_id}")
        print(f"   Food Class: {ingredient.food_class}")
        print(f"   Category: {ingredient.get_category_display()}")
        print(f"   Notes: {ingredient.notes}")
        
        # Show nutrient information
        nutrient_links = ingredient.ingredientnutrientlink_set.all()
        print(f"\n🥗 Nutritional Information ({len(nutrient_links)} nutrients):")
        for link in nutrient_links[:10]:  # Show first 10 nutrients
            print(f"   {link.nutrient.name}: {link.amount_per_100_units:.2f} {link.nutrient.unit}")
        
        if len(nutrient_links) > 10:
            print(f"   ... and {len(nutrient_links) - 10} more nutrients")
        
        # Show food portions
        food_portions = ingredient.food_portions.all()
        print(f"\n📏 Food Portions ({len(food_portions)} portions):")
        for portion in food_portions:
            print(f"   {portion.portion_description}: {portion.gram_weight}g")
        
        print(f"\n🎉 Demo completed successfully!")
        print(f"Ingredient '{ingredient.name}' is now available in your database.")
        
    except Exception as e:
        print(f"❌ Error creating ingredient: {e}")
        print("This could be due to:")
        print("- Missing or invalid OpenAI API key")
        print("- OpenAI API quota exceeded")
        print("- Network connectivity issues")
        print("- Missing nutrients in database")


def show_existing_chatgpt_ingredients():
    """Show existing ChatGPT-generated ingredients."""
    chatgpt_ingredients = Ingredient.objects.filter(food_class='ChatGPT')
    
    if chatgpt_ingredients.exists():
        print(f"\n🤖 Existing ChatGPT Ingredients ({len(chatgpt_ingredients)}):")
        for ingredient in chatgpt_ingredients:
            print(f"   - {ingredient.name} (ID: {ingredient.id})")
    else:
        print("\n📝 No ChatGPT ingredients found in database.")


def main():
    """Main demo function."""
    try:
        show_existing_chatgpt_ingredients()
        demo_ai_ingredient_creation()
        
        print("\n" + "=" * 50)
        print("💡 Next steps:")
        print("   - Test the API endpoints using curl or Postman")
        print("   - Integrate with your frontend application")
        print("   - Export your custom ingredients: make export-chatgpt-foods")
        print("   - Run tests: make tests")
        
    except KeyboardInterrupt:
        print("\n\n👋 Demo cancelled by user.")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 