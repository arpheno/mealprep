from django.contrib import admin
from .models import (
    Nutrient, 
    Ingredient, 
    IngredientNutrientLink, 
    PersonProfile, 
    MealComponent, 
    IngredientUsage, 
    MealPlan,
    DietaryReferenceValue,
    FoodPortion
)

# Basic registration for now, can be customized later with ModelAdmin classes

@admin.register(Nutrient)
class NutrientAdmin(admin.ModelAdmin):
    list_display = ('name', 'unit', 'category', 'is_essential')
    list_filter = ('category', 'is_essential')
    search_fields = ('name', 'description')

class IngredientNutrientLinkInline(admin.TabularInline):
    model = IngredientNutrientLink
    extra = 1 # Number of empty forms to display
    autocomplete_fields = ['nutrient']

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'base_unit_for_nutrition', 'common_purchase_unit')
    list_filter = ('category',)
    search_fields = ('name', 'notes')
    inlines = [IngredientNutrientLinkInline]

# No need to register IngredientNutrientLink separately if it's only used as an inline

class IngredientUsageInline(admin.TabularInline):
    model = IngredientUsage
    extra = 1
    autocomplete_fields = ['ingredient']

@admin.register(MealComponent)
class MealComponentAdmin(admin.ModelAdmin):
    list_display = ('name', 'category_tag')
    list_filter = ('category_tag',)
    search_fields = ('name', 'description_recipe')
    inlines = [IngredientUsageInline]
    # filter_horizontal = ('ingredients',)

# No need to register IngredientUsage separately if it's only used as an inline

@admin.register(PersonProfile)
class PersonProfileAdmin(admin.ModelAdmin):
    list_display = ('name', )
    search_fields = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name',)
        }),
        ('Dietary Targets', {
            'fields': ('custom_nutrient_targets',)
        }),
    )
    # To make JSONField more readable if it gets complex, consider a custom widget
    # or just rely on the default JSON string editing for now.

@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'duration_days', 'servings_per_day_per_person', 'creation_date', 'last_modified_date')
    list_filter = ('duration_days', 'creation_date')
    search_fields = ('name', 'description', 'notes')
    filter_horizontal = ('target_people_profiles',)
    readonly_fields = ('creation_date', 'last_modified_date')

# If you want to see the through models directly in admin (optional):
# admin.site.register(IngredientNutrientLink)
# admin.site.register(IngredientUsage)

@admin.register(DietaryReferenceValue)
class DietaryReferenceValueAdmin(admin.ModelAdmin):
    list_display = (
        'nutrient',
        'target_population',
        'age_range_text',
        'gender',
        'pri', 
        'ai', 
        'ar',
        'ul', 
        'value_unit'
    )
    list_filter = (
        'target_population',
        'gender',
        'nutrient__category',
        'nutrient__name',
        'value_unit'
    )
    search_fields = (
        'nutrient__name',
        'target_population',
        'age_range_text',
        'source_data_category'
    )
    autocomplete_fields = ['nutrient']

@admin.register(FoodPortion)
class FoodPortionAdmin(admin.ModelAdmin):
    list_display = (
        'ingredient',
        'portion_description',
        'gram_weight',
        'amount',
        'measure_unit_name',
        'modifier',
        'sequence_number'
    )
    list_filter = (
        'ingredient__category',
        'ingredient__name',
        'measure_unit_name',
    )
    search_fields = (
        'ingredient__name',
        'portion_description',
        'modifier',
        'measure_unit_name'
    )
    autocomplete_fields = ['ingredient']
    # For better performance with many ingredients, consider raw_id_fields = ['ingredient']
    # or ensure your IngredientAdmin has search_fields configured for autocomplete.
    ordering = ('ingredient__name', 'sequence_number', 'gram_weight')
