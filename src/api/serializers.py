from rest_framework import serializers
from .models import Nutrient, Ingredient, IngredientNutrientLink, PersonProfile, MealComponent, IngredientUsage, MealPlan, FoodPortion, DietaryReferenceValue, MealPlanItem

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
    # Make ingredient writable for direct creation/update via IngredientNutrientLinkViewSet
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    # Nutrient is already a writable FK by default if included in fields
    nutrient = serializers.PrimaryKeyRelatedField(queryset=Nutrient.objects.all()) # Ensure nutrient is also explicitly writable

    class Meta:
        model = IngredientNutrientLink
        fields = [
            'id', 'ingredient', 'nutrient', 'nutrient_name', 'nutrient_unit', 'fdc_nutrient_number', 
            'amount_per_100_units', 
            'default_rda', 'upper_limit' 
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
    personalized_drvs = serializers.SerializerMethodField()

    class Meta:
        model = PersonProfile
        fields = '__all__' # This will now include 'personalized_drvs' due to the method field

    def get_personalized_drvs(self, obj):
        if hasattr(obj, 'get_personalized_drvs'):
            return obj.get_personalized_drvs()
        return {}

class IngredientUsageSerializer(serializers.ModelSerializer):
    ingredient_name = serializers.CharField(source='ingredient.name', read_only=True)
    # Make meal_component writable for direct creation/update via IngredientUsageViewSet
    meal_component = serializers.PrimaryKeyRelatedField(queryset=MealComponent.objects.all(), required=False)
    # Ingredient is already a writable FK by default if included in fields
    ingredient = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all()) # Ensure ingredient is also explicitly writable

    class Meta:
        model = IngredientUsage
        fields = ['id', 'meal_component', 'ingredient', 'ingredient_name', 'quantity']

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

class MealPlanItemSerializer(serializers.ModelSerializer):
    # For Read operations - nested representation
    meal_component_detail = MealComponentSerializer(source='meal_component', read_only=True)
    assigned_people_detail = PersonProfileSerializer(source='assigned_people', many=True, read_only=True)

    # For Write operations - IDs
    meal_component_id = serializers.PrimaryKeyRelatedField(
        queryset=MealComponent.objects.all(), 
        source='meal_component', 
        write_only=True
    )
    assigned_people_ids = serializers.PrimaryKeyRelatedField(
        queryset=PersonProfile.objects.all(), 
        source='assigned_people', 
        many=True, 
        write_only=True,
        required=False # Allow empty list for "shared" items if that convention is used, or if explicitly assigning all.
    )

    class Meta:
        model = MealPlanItem
        fields = [
            'id', 
            'meal_component_id', 'meal_component_detail', # Write ID, Read Detail
            'assigned_people_ids', 'assigned_people_detail', # Write IDs, Read Detail
            # Add other MealPlanItem specific fields here if any (e.g., quantity_multiplier, notes)
            'meal_plan' # meal_plan is often set implicitly by the parent serializer or view
        ]
        read_only_fields = ['meal_plan'] # meal_plan will be set by the MealPlanSerializer

class MealPlanSerializer(serializers.ModelSerializer):
    plan_nutritional_totals = serializers.SerializerMethodField(read_only=True)
    plan_nutritional_targets_detail = serializers.SerializerMethodField(read_only=True)
    
    # For M2M field target_people_profiles - use 'target_people_profiles' as key for both read and write source
    target_people_profiles = serializers.PrimaryKeyRelatedField(
        queryset=PersonProfile.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    # For reading, use a nested serializer with the same key 'target_people_profiles'
    target_people_profiles_detail = PersonProfileSerializer(source='target_people_profiles', many=True, read_only=True)

    # New handling for MealPlanItems
    plan_items = MealPlanItemSerializer(many=True, read_only=True) # source defaults to 'plan_items'
    plan_items_write = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False,
        source='plan_items' # Ensure this maps to the correct field for processing if needed, or handle in create/update
    )

    class Meta:
        model = MealPlan
        fields = [
            'id', 'name', 'notes', 'duration_days', # Standardized to 'notes', removed 'description'
            'target_people_profiles', 'target_people_profiles_detail', # target_people_profiles for write, _detail for read
            'plan_items', 'plan_items_write',
            'servings_per_day_per_person', 
            'creation_date', 'last_modified_date',
            'plan_nutritional_totals', 'plan_nutritional_targets_detail'
        ]
        read_only_fields = ['creation_date', 'last_modified_date']

    def get_plan_nutritional_totals(self, obj):
        if hasattr(obj, 'get_plan_nutritional_totals'):
            return obj.get_plan_nutritional_totals()
        return {}
    
    def get_plan_nutritional_targets_detail(self, obj):
        if hasattr(obj, 'get_plan_nutritional_targets'):
            return obj.get_plan_nutritional_targets()
        return {}

    def _create_or_update_plan_items(self, meal_plan_instance, plan_items_data):
        MealPlanItem.objects.filter(meal_plan=meal_plan_instance).delete()
        
        for item_data in plan_items_data:
            component_id = item_data.get('meal_component_id')
            people_ids = item_data.get('assigned_people_ids', [])
            
            if not component_id:
                print(f"Skipping item, missing meal_component_id: {item_data}") 
                continue

            try:
                meal_component = MealComponent.objects.get(id=component_id)
            except MealComponent.DoesNotExist:
                print(f"Skipping item, MealComponent not found: {component_id}")
                continue
            
            plan_item = MealPlanItem.objects.create(
                meal_plan=meal_plan_instance,
                meal_component=meal_component
            )
            if people_ids:
                try:
                    assigned_person_profiles = PersonProfile.objects.filter(id__in=people_ids)
                    plan_item.assigned_people.set(assigned_person_profiles)
                except Exception as e:
                    print(f"Error assigning people to item {plan_item.id}: {e}")

    def create(self, validated_data):
        target_people_data = validated_data.pop('target_people_profiles', [])
        plan_items_data = validated_data.pop('plan_items', []) # Changed from plan_items_write to plan_items based on source
        
        # Remove 'description' if it's still in validated_data and model doesn't have it
        validated_data.pop('description', None)

        meal_plan = MealPlan.objects.create(**validated_data)
        
        if target_people_data:
            meal_plan.target_people_profiles.set(target_people_data)
            
        self._create_or_update_plan_items(meal_plan, plan_items_data)
        
        return meal_plan

    def update(self, instance, validated_data):
        target_people_data = validated_data.pop('target_people_profiles', None)
        plan_items_data = validated_data.pop('plan_items', None) # Changed from plan_items_write to plan_items

        # Remove 'description' if it's still in validated_data and model doesn't have it
        validated_data.pop('description', None)

        instance.name = validated_data.get('name', instance.name)
        # instance.description = validated_data.get('description', instance.description) # Removed description
        instance.notes = validated_data.get('notes', instance.notes)
        instance.duration_days = validated_data.get('duration_days', instance.duration_days)
        instance.servings_per_day_per_person = validated_data.get('servings_per_day_per_person', instance.servings_per_day_per_person)
        instance.save()

        if target_people_data is not None:
            instance.target_people_profiles.set(target_people_data)
            
        if plan_items_data is not None:
            self._create_or_update_plan_items(instance, plan_items_data)
            
        return instance

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