from rest_framework import serializers
from .models import Nutrient, Ingredient, IngredientNutrientLink, PersonProfile, MealComponent, IngredientUsage, MealPlan, FoodPortion, DietaryReferenceValue

class NutrientSerializer(serializers.ModelSerializer):
    default_rda = serializers.SerializerMethodField()
    upper_limit = serializers.SerializerMethodField()

    class Meta:
        model = Nutrient
        fields = ['id', 'name', 'unit', 'category', 'fdc_nutrient_id', 'fdc_nutrient_number', 
                  'description', 'is_essential', 'source_notes', 
                  'default_rda', 'upper_limit'] # Added new RDA fields

    def get_default_rda(self, obj):
        return obj.get_default_rda()

    def get_upper_limit(self, obj):
        return obj.get_upper_limit()

class IngredientNutrientLinkSerializer(serializers.ModelSerializer):
    # To show nutrient name instead of ID in Ingredient detail
    nutrient_name = serializers.CharField(source='nutrient.name', read_only=True)
    nutrient_unit = serializers.CharField(source='nutrient.unit', read_only=True)
    fdc_nutrient_number = serializers.CharField(source='nutrient.fdc_nutrient_number', read_only=True)
    # Add back default RDA and UL, sourced from the Nutrient model's methods
    default_rda = serializers.SerializerMethodField()
    upper_limit = serializers.SerializerMethodField()

    class Meta:
        model = IngredientNutrientLink
        fields = [
            'nutrient', 'nutrient_name', 'nutrient_unit', 'fdc_nutrient_number', 
            'amount_per_100_units',
            'default_rda', 'upper_limit' # Added back generic RDA fields
        ]

    def get_default_rda(self, obj):
        # obj is an IngredientNutrientLink instance
        return obj.nutrient.get_default_rda()

    def get_upper_limit(self, obj):
        # obj is an IngredientNutrientLink instance
        return obj.nutrient.get_upper_limit()

class IngredientSerializer(serializers.ModelSerializer):
    # Use the IngredientNutrientLinkSerializer for the nested representation
    # 'source' should match the related_name or field name on the IngredientNutrientLink model if it points back to Ingredient explicitly
    # Or, if IngredientNutrientLink is primarily accessed from Ingredient, this would be the 'through' model details.
    # Let's assume we want to list the nutrient links when viewing an ingredient.
    # The 'through' model IngredientNutrientLink has a ForeignKey to Ingredient called 'ingredient'.
    # So on Ingredient, the reverse relation is ingredientnutrientlink_set.
    nutrient_links = IngredientNutrientLinkSerializer(source='ingredientnutrientlink_set', many=True, read_only=True)

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'category', 'base_unit_for_nutrition',
                  'common_purchase_unit', 'purchase_unit_to_base_unit_conversion',
                  'notes', 'nutrient_links']
        # We can add a writeable nested field for nutrients later if needed, e.g. using custom create/update or a different serializer.

# Basic serializers for other models (can be expanded later)
class PersonProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonProfile
        fields = '__all__'

class IngredientUsageSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)

    class Meta:
        model = IngredientUsage
        fields = ['ingredient', 'ingredient_name', 'quantity']

class MealComponentSerializer(serializers.ModelSerializer):
    # For reading existing usages - matches the related_name from IngredientUsage to MealComponent
    ingredientusage_set = IngredientUsageSerializer(many=True, read_only=True)

    # For writing new/updated usages - this is the key the frontend should send for POST/PUT
    ingredients_usage_write = IngredientUsageSerializer(many=True, write_only=True, required=False)

    nutritional_totals = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = MealComponent
        fields = [
            'id', 'name', 'category_tag', 'description_recipe', 'frequency',
            'ingredientusage_set',      # For output (GET response)
            'ingredients_usage_write',  # For input (POST/PUT request payload)
            'nutritional_totals'
        ]

    def get_nutritional_totals(self, obj):
        if hasattr(obj, 'get_nutritional_totals'):
            return obj.get_nutritional_totals()
        return {}

    def create(self, validated_data):
        usages_data = validated_data.pop('ingredients_usage_write', []) # Use the new write-only field
        # The rest of validated_data should only contain direct fields for MealComponent
        meal_component = MealComponent.objects.create(**validated_data)
        for usage_data in usages_data:
            # usage_data comes from IngredientUsageSerializer, so 'ingredient' key should hold the ID
            IngredientUsage.objects.create(meal_component=meal_component, **usage_data)
        return meal_component

    def update(self, instance, validated_data):
        usages_data = validated_data.pop('ingredients_usage_write', None) # Use the new write-only field
        
        # Update MealComponent direct fields
        instance.name = validated_data.get('name', instance.name)
        instance.category_tag = validated_data.get('category_tag', instance.category_tag)
        instance.description_recipe = validated_data.get('description_recipe', instance.description_recipe)
        instance.frequency = validated_data.get('frequency', instance.frequency)
        instance.save()

        # Handle IngredientUsage updates
        if usages_data is not None:
            instance.ingredientusage_set.all().delete() # Use actual related_name for operations
            for usage_data in usages_data:
                IngredientUsage.objects.create(meal_component=instance, **usage_data)
        
        return instance

class MealPlanSerializer(serializers.ModelSerializer):
    plan_nutritional_totals = serializers.SerializerMethodField()
    plan_nutritional_targets_detail = serializers.SerializerMethodField(read_only=True)
    # For M2M fields like target_people_profiles and meal_components,
    # DRF handles them by default with PrimaryKeyRelatedField for write operations.
    # For read operations, you might want to use a nested serializer or StringRelatedField.
    # For now, default handling is fine, frontend will likely send IDs.

    # To allow writing people and components by ID when creating/updating a MealPlan:
    target_people_ids = serializers.PrimaryKeyRelatedField(
        queryset=PersonProfile.objects.all(),
        source='target_people_profiles',
        many=True,
        write_only=True, # Only for writing, reading uses target_people_profiles (default or custom depth)
        required=False # Depending on if it's mandatory
    )
    meal_component_ids = serializers.PrimaryKeyRelatedField(
        queryset=MealComponent.objects.all(),
        source='meal_components',
        many=True,
        write_only=True,
        required=False
    )

    # If you want to see the full profile objects on read, not just IDs:
    target_people_profiles_detail = PersonProfileSerializer(source='target_people_profiles', many=True, read_only=True)
    # If you want to see the full component objects on read:
    meal_components_detail = MealComponentSerializer(source='meal_components', many=True, read_only=True)

    class Meta:
        model = MealPlan
        fields = [
            'id', 'name', 'description', 'duration_days', 
            'target_people_profiles', 'target_people_profiles_detail', 'target_people_ids', # For read (detail) and write (ids)
            'meal_components', 'meal_components_detail', 'meal_component_ids', # For read (detail) and write (ids)
            'servings_per_day_per_person', 'notes',
            'creation_date', 'last_modified_date',
            'plan_nutritional_totals', 'plan_nutritional_targets_detail'
        ]
        # read_only_fields = ['plan_nutritional_totals'] # This is fetched by get_plan_nutritional_totals method

    def get_plan_nutritional_totals(self, obj):
        return obj.get_plan_nutritional_totals()
    
    def get_plan_nutritional_targets_detail(self, obj):
        return obj.get_plan_nutritional_targets()

class FoodPortionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FoodPortion
        fields = '__all__' # Or list specific fields

class DietaryReferenceValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = DietaryReferenceValue
        fields = '__all__'

class IngredientSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'fdc_id'] 