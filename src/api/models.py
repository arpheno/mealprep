from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from collections import defaultdict

# --- Helper function for PersonProfile default nutrient targets ---
def get_default_nutrient_targets():
    # This function is called when a new PersonProfile is created.
    # It attempts to find common nutrients (Energy, Protein) and set default targets.
    defaults = {}
    try:
        # Use the new manager method to find Energy, trying "Energy" then "Calories"
        # Assumes "Energy" is the canonical name if both exist.
        energy_nutrient = Nutrient.objects.filter_by_name_or_alias('Energy').first()
        if not energy_nutrient:
            energy_nutrient = Nutrient.objects.filter_by_name_or_alias('Calories').first()
        
        energy_unit = energy_nutrient.unit if energy_nutrient else 'kcal'
        # Store with canonical name "Energy" if possible, or the key used for lookup.
        # It's best if custom_nutrient_targets in PersonProfile uses canonical keys.
        # For this default, we'll use "Energy" as the key.
        defaults["Energy"] = {"target": 2000, "unit": energy_unit, "is_override": True}
    except Exception: # Catch broader errors if Nutrient table isn't populated yet
        defaults["Energy"] = {"target": 2000, "unit": "kcal", "is_override": True} # Fallback

    try:
        protein_nutrient = Nutrient.objects.filter_by_name_or_alias('Protein').first()
        protein_unit = protein_nutrient.unit if protein_nutrient else 'g'
        defaults["Protein"] = {"target": 75, "unit": protein_unit, "is_override": True}
    except Exception:
        defaults["Protein"] = {"target": 75, "unit": "g", "is_override": True} # Fallback
    return defaults

# --- Enums as Django Choices --- 

class NutrientCategory(models.TextChoices):
    MACRONUTRIENT = 'MACRO', 'Macronutrient'
    VITAMIN = 'VITAMIN', 'Vitamin'
    MINERAL = 'MINERAL', 'Mineral'
    GENERAL = 'GENERAL', 'General' # For things like Calories, Water

class IngredientFoodCategory(models.TextChoices):
    PROTEIN_ANIMAL = 'PRO_ANIMAL', 'Animal Protein'
    PROTEIN_PLANT = 'PRO_PLANT', 'Plant Protein'
    GRAIN_CEREAL = 'GRAIN', 'Grain/Cereal'
    LEGUME = 'LEGUME', 'Legume'
    VEGETABLE_LEAFY = 'VEG_LEAFY', 'Leafy Vegetable'
    VEGETABLE_ROOT = 'VEG_ROOT', 'Root Vegetable'
    VEGETABLE_FRUITING = 'VEG_FRUIT', 'Fruiting Vegetable'
    FRUIT = 'FRUIT', 'Fruit'
    NUT_SEED = 'NUT_SEED', 'Nut/Seed'
    OIL_FAT = 'OIL_FAT', 'Oil/Fat'
    DAIRY = 'DAIRY', 'Dairy'
    DAIRY_ALTERNATIVE = 'DAIRY_ALT', 'Dairy Alternative'
    SPICE_HERB = 'SPICE_HERB', 'Spice/Herb'
    CONDIMENT_SAUCE = 'CONDIMENT', 'Condiment/Sauce'
    BEVERAGE = 'BEVERAGE', 'Beverage'
    OTHER = 'OTHER', 'Other'

class Gender(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    PREFER_NOT_TO_SAY = 'NO_SAY', 'Prefer not to say'
    OTHER = 'OTHER', 'Other'


class MealComponentFrequency(models.TextChoices):
    PER_MEAL_BOX = 'PER_BOX', 'Per Meal Box'
    WEEKLY_TOTAL = 'WEEKLY', 'Weekly Total'
    DAILY_TOTAL = 'DAILY', 'Daily Total'

# --- Django Models --- 

class NutrientManager(models.Manager):
    def get_by_name_or_alias(self, name_query):
        """
        Retrieves a single Nutrient instance by its canonical name or any of its aliases.
        Raises Nutrient.DoesNotExist if not found.
        Raises Nutrient.MultipleObjectsReturned if multiple distinct nutrients match (should not happen with unique names/aliases).
        """
        try:
            # Check direct canonical name match (case-insensitive)
            return self.get(name__iexact=name_query)
        except self.model.DoesNotExist:
            # If not found, check aliases (case-insensitive)
            try:
                return self.get(aliases__name__iexact=name_query)
            except self.model.DoesNotExist:
                raise self.model.DoesNotExist(
                    f"{self.model.__name__} matching query '{name_query}' does not exist in canonical names or aliases."
                )
            except self.model.MultipleObjectsReturned:
                # This could happen if the same alias string somehow got linked to multiple nutrients,
                # which should be prevented by NutrientAlias.name being unique.
                # Or if the query matches multiple aliases that point to different nutrients.
                # For a .get() operation, this is an issue.
                raise self.model.MultipleObjectsReturned(
                    f"Query '{name_query}' matched multiple distinct nutrients through aliases."
                )
        except self.model.MultipleObjectsReturned:
            # Should not happen if Nutrient.name is unique
            raise

    def filter_by_name_or_alias(self, name_query):
        """
        Filters Nutrient instances by canonical name or any of their aliases (case-insensitive).
        Returns a QuerySet.
        """
        return self.filter(
            Q(name__iexact=name_query) | Q(aliases__name__iexact=name_query)
        ).distinct()

class Nutrient(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text='e.g., Vitamin C, Protein. This is the canonical name.') # Made unique
    unit = models.CharField(max_length=20, help_text='e.g., kcal, g, mg, mcg, IU')
    fdc_nutrient_id = models.IntegerField(unique=True, null=True, blank=True, db_index=True, help_text="FoodData Central Nutrient ID (nutrient.id from FDC data)")
    fdc_nutrient_number = models.CharField(max_length=10, null=True, blank=True, db_index=True, help_text="FoodData Central Nutrient Number (nutrient.number from FDC data)")
    category = models.CharField(
        max_length=20,
        choices=NutrientCategory.choices,
        default=NutrientCategory.GENERAL
    )
    description = models.TextField(blank=True, null=True)
    # RDA fields default_rda_female, default_rda_male, upper_limit have been removed.
    # Their data will be managed by the new DietaryReferenceValue model.
    is_essential = models.BooleanField(default=False)
    source_notes = models.TextField(blank=True, null=True, help_text='e.g., Source of RDA data, general notes about the nutrient')

    objects = NutrientManager() # Add the custom manager

    def __str__(self):
        return f'{self.name} ({self.unit})'

    class Meta:
        ordering = ['name']

    def get_default_rda(self):
        """
        Attempts to find a default Recommended Dietary Allowance (RDA) value
        from its related DietaryReferenceValue objects.
        Placeholder: Fetches PRI for 'Adults' if available.
        """
        # Prioritize PRI for a general adult population
        drv = self.drvs.filter(target_population__icontains='Adults', pri__isnull=False).first()
        if drv:
            return drv.pri
        # Fallback to AI if PRI not found
        drv = self.drvs.filter(target_population__icontains='Adults', ai__isnull=False).first()
        if drv:
            return drv.ai
        return None

    def get_upper_limit(self):
        """
        Attempts to find an Upper Limit (UL) value
        from its related DietaryReferenceValue objects.
        Placeholder: Fetches UL for 'Adults' if available.
        """
        drv = self.drvs.filter(target_population__icontains='Adults', ul__isnull=False).first()
        if drv:
            return drv.ul
        return None

class NutrientAlias(models.Model):
    name = models.CharField(max_length=255, unique=True, help_text="An alternative name or symbol for a nutrient (e.g., 'Vitamin B2', 'Thiamin'). Must be unique.")
    nutrient = models.ForeignKey(Nutrient, related_name='aliases', on_delete=models.CASCADE, help_text="The canonical nutrient this alias refers to.")

    def __str__(self):
        return f"{self.name} (Alias for {self.nutrient.name})"

    class Meta:
        ordering = ['name']
        verbose_name_plural = "Nutrient Aliases"

class Ingredient(models.Model):
    name = models.CharField(max_length=255, help_text='e.g., Chicken Breast, boneless, skinless, raw. Will be populated from FDC description.')
    fdc_id = models.IntegerField(unique=True, null=True, blank=True, db_index=True, help_text="FoodData Central Food ID for this ingredient")
    food_class = models.CharField(max_length=50, blank=True, null=True, help_text="From FDC foodClass e.g., FinalFood")
    category = models.CharField(
        max_length=20,
        choices=IngredientFoodCategory.choices,
        blank=True, null=True
    )
    base_unit_for_nutrition = models.CharField(max_length=10, default='g', help_text='Nutritional info is per 100 of this unit (e.g., g, ml)')
    nutrients = models.ManyToManyField(
        Nutrient,
        through='IngredientNutrientLink',
        related_name='ingredients'
    )
    common_purchase_unit = models.CharField(max_length=50, blank=True, null=True, help_text='e.g., piece, can, bunch')
    # Factor to convert one common_purchase_unit to base_unit_for_nutrition (e.g., if 1 piece = 150g, factor is 150)
    purchase_unit_to_base_unit_conversion = models.FloatField(blank=True, null=True, validators=[MinValueValidator(0)])
    notes = models.TextField(blank=True, null=True, help_text='e.g., Cooked yield is ~70% of raw weight')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class IngredientNutrientLink(models.Model):
    """ Intermediary model for Ingredient to Nutrient M2M relationship. """
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    nutrient = models.ForeignKey(Nutrient, on_delete=models.CASCADE)
    # Amount of the nutrient per 100 units of the ingredient's base_unit_for_nutrition
    amount_per_100_units = models.FloatField(validators=[MinValueValidator(0)], help_text='Amount of nutrient per 100 units of ingredient base unit')

    def __str__(self):
        return f'{self.ingredient.name} - {self.nutrient.name}: {self.amount_per_100_units} per 100 {self.ingredient.base_unit_for_nutrition}'

    class Meta:
        unique_together = ('ingredient', 'nutrient') # Each nutrient listed once per ingredient
        ordering = ['ingredient__name', 'nutrient__name']

class PersonProfile(models.Model):
    # user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, help_text="Link to Django User model")
    name = models.CharField(max_length=100, help_text='Display name for the profile')
    custom_nutrient_targets = models.JSONField(
        blank=True, # Blank is okay as default will fill it
        null=False, # Should always have a dict, even if empty, due to default
        default=get_default_nutrient_targets, 
        help_text='Store custom nutrient targets, e.g., {"NutrientName": {"target": 100, "unit": "mg", "is_override": true}}'
    )
    notes = models.TextField(blank=True, null=True)

    def get_personalized_drvs(self):
        """
        Calculates personalized Daily Recommended Values for this person, 
        considering general DRVs and specific overrides from their profile.
        Returns a dictionary: {nutrient_name: {'rda': float/None, 'ul': float/None, 'unit': str}}
        All RDA/UL values are returned in the nutrient's canonical unit if it's a system nutrient,
        or the unit specified in custom_targets if it's a purely custom nutrient.
        """
        personalized_values = {}
        all_system_nutrients = Nutrient.objects.all()
        system_nutrient_names = {n.name for n in all_system_nutrients}

        # Step 1: Process all system nutrients (from Nutrient table)
        for nutrient in all_system_nutrients:
            base_rda = nutrient.get_default_rda() # Fetches from DRV model, e.g., PRI for Adults
            base_ul = nutrient.get_upper_limit()   # Fetches from DRV model, e.g., UL for Adults
            canonical_unit = nutrient.unit

            current_rda = base_rda
            current_ul = base_ul
            # The unit for this nutrient will be its canonical unit.
            # If custom_targets specify a different unit, it's for user input convenience;
            # the value should ideally be pre-converted or understood to be in the canonical unit.

            if self.custom_nutrient_targets and nutrient.name in self.custom_nutrient_targets:
                custom_spec = self.custom_nutrient_targets[nutrient.name]
                
                # RDA override logic:
                # 'target' in custom_spec is considered the RDA.
                # It overrides if 'is_override' is true, or if no base_rda exists.
                if custom_spec.get('is_override', False) or base_rda is None:
                    if 'target' in custom_spec:
                        current_rda = custom_spec['target']
                elif 'target' in custom_spec and current_rda is None: # Not an override, but base was None, so use custom.
                    current_rda = custom_spec['target']

                # UL override logic:
                # Custom 'ul' always overrides the base_ul if present.
                if 'ul' in custom_spec:
                    current_ul = custom_spec['ul']
                
                # Check for unit mismatch in custom_targets, but do not change canonical_unit for system nutrients.
                # The values in custom_spec ('target', 'ul') are assumed to be interpretable in the canonical_unit.
                if 'unit' in custom_spec and custom_spec['unit'] != canonical_unit:
                    # This is a good place for logging in a real application.
                    print(f"INFO: PersonProfile '{self.name}' has custom target for '{nutrient.name}' with unit '{custom_spec['unit']}', "
                          f"but canonical unit is '{canonical_unit}'. Values are assumed to be in canonical unit or pre-converted.")
            
            # Include the nutrient if it has an RDA, a UL, or was mentioned in custom_targets (even if values are null)
            # This ensures that if a user customizes a nutrient (e.g., sets RDA to 0 or UL to null), it's still part of their profile.
            if current_rda is not None or current_ul is not None or (self.custom_nutrient_targets and nutrient.name in self.custom_nutrient_targets):
                personalized_values[nutrient.name] = {
                    'rda': current_rda,
                    'ul': current_ul,
                    'unit': canonical_unit
                }

        # Step 2: Add purely custom nutrients (defined in custom_nutrient_targets but not in Nutrient table)
        if self.custom_nutrient_targets:
            for nutrient_name, targets_spec in self.custom_nutrient_targets.items():
                if nutrient_name not in system_nutrient_names:
                    # This nutrient is not a system nutrient, so it wasn't processed above.
                    # We take its definition (rda, ul, unit) directly from custom_nutrient_targets.
                    personalized_values[nutrient_name] = {
                        'rda': targets_spec.get('target'), # 'target' field is used for RDA
                        'ul': targets_spec.get('ul'),
                        'unit': targets_spec.get('unit', '') # Default to empty string if no unit specified
                    }
        
        return personalized_values

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

# NEW MODEL DEFINITION for DietaryReferenceValue
class DietaryReferenceValue(models.Model):
    """
    Stores Dietary Reference Values (DRVs) for various nutrients, 
    considering target population, age, gender, and specific DRV types (AI, AR, PRI, UL).
    """
    source_data_category = models.CharField(
        max_length=100, 
        help_text="Category from the source DRV data, e.g., 'Carbohydrates', 'Vitamins'"
    )
    
    nutrient = models.ForeignKey(
        Nutrient, 
        on_delete=models.CASCADE, 
        related_name='drvs',
        help_text="The specific nutrient these values refer to."
    )
    
    target_population = models.CharField(
        max_length=100, 
        help_text="e.g., 'Adults', 'Infants 7-11 months'"
    )
    
    age_range_text = models.CharField(
        max_length=50, 
        help_text="Age range as text from the source, e.g., '≥ 18 years', '7-11 months'"
    )
    
    gender = models.CharField(
        max_length=10, 
        choices=Gender.choices, 
        null=True, 
        blank=True, 
        help_text="Gender specificity of the DRV (Male, Female, or applies to both if null/blank)"
    ) 
    
    frequency = models.CharField(
        max_length=50, 
        help_text="Frequency of intake, e.g., 'daily'"
    )
    
    value_unit = models.CharField(
        max_length=20, 
        help_text="Unit for AI, AR, PRI, RI, UL values, e.g., 'g', 'mg', 'E%'"
    )
    
    ai = models.FloatField(null=True, blank=True, verbose_name="Adequate Intake (AI)")
    ar = models.FloatField(null=True, blank=True, verbose_name="Average Requirement (AR)")
    pri = models.FloatField(null=True, blank=True, verbose_name="Population Reference Intake (PRI)")
    ri = models.FloatField(null=True, blank=True, verbose_name="Reference Intake (RI)")
    ul = models.FloatField(null=True, blank=True, verbose_name="Tolerable Upper Intake Level (UL)")

    class Meta:
        verbose_name = "Dietary Reference Value"
        verbose_name_plural = "Dietary Reference Values"
        unique_together = [['nutrient', 'target_population', 'age_range_text', 'gender', 'source_data_category', 'value_unit']]
        ordering = ['nutrient__name', 'target_population', 'age_range_text', 'gender']

    def __str__(self):
        gender_display = self.get_gender_display() if self.gender else "Both genders"
        return f"DRV for {self.nutrient.name}: Pop: {self.target_population}, Age: {self.age_range_text}, Gender: {gender_display}"

class MealComponent(models.Model):
    name = models.CharField(max_length=200)
    category_tag = models.CharField(max_length=50, blank=True, null=True, help_text='e.g., Protein, Carb, Snack')
    description_recipe = models.TextField(blank=True, null=True)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientUsage',
        related_name='meal_components'
    )
    frequency = models.CharField(
        max_length=10,
        choices=MealComponentFrequency.choices,
        default=MealComponentFrequency.PER_MEAL_BOX,
        help_text='Defines how the component quantity/nutrition is accounted for (e.g., per meal box, weekly total).'
    )
    # owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, help_text="User who created this component")

    def get_nutritional_totals(self):
        """
        Calculates the sum of each nutrient for this meal component based on its ingredients and their quantities.
        Returns a dictionary like: {'Nutrient Name': {'amount': X, 'unit': 'Y'}, ...}
        """
        totals = defaultdict(lambda: {'amount': 0, 'unit': ''})
        
        # Prefetch related data for efficiency if this method is called multiple times or for multiple components
        # For a single call, direct access is fine. For lists, consider prefetching in the view/queryset.
        for usage in self.ingredientusage_set.select_related('ingredient').all():
            ingredient_quantity_grams = usage.quantity # This is already in grams
            
            # Ensure ingredient.base_unit_for_nutrition is 'g' for correct calculation,
            # or adjust if other base units were to be allowed for an ingredient's nutrition facts.
            # Our current FDC import and model setup assumes 'g'.
            
            for link in usage.ingredient.ingredientnutrientlink_set.select_related('nutrient').all():
                nutrient = link.nutrient
                amount_per_100g = link.amount_per_100_units
                
                # Calculate amount of this nutrient from this ingredient usage
                nutrient_amount_from_usage = (ingredient_quantity_grams / 100.0) * amount_per_100g
                
                totals[nutrient.name]['amount'] += nutrient_amount_from_usage
                if not totals[nutrient.name]['unit']: # Set unit if not already set
                    totals[nutrient.name]['unit'] = nutrient.unit
        
        # Round amounts for cleaner display, e.g., to 2 decimal places
        for nutrient_name in totals:
            totals[nutrient_name]['amount'] = round(totals[nutrient_name]['amount'], 2)
            
        return dict(totals) # Convert defaultdict to dict for the final output

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class IngredientUsage(models.Model):
    """ Intermediary model for MealComponent to Ingredient M2M relationship. """
    meal_component = models.ForeignKey(MealComponent, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField(validators=[MinValueValidator(0)], help_text='Amount of the ingredient in grams (g)')
    # unit = models.CharField(max_length=50, help_text='Unit for the quantity (e.g., g, kg, ml, piece, cup)')

    def __str__(self):
        return f'{self.quantity}g of {self.ingredient.name} in {self.meal_component.name}'

    class Meta:
        # Might not need unique_together if an ingredient can be listed multiple times in different forms/units in the same component, but usually it implies total quantity.
        # unique_together = ('meal_component', 'ingredient')
        ordering = ['meal_component__name', 'ingredient__name']

# Define MealPlanItem before MealPlan if MealPlan refers to it,
# or use string references if preferred for ordering.
# For clarity, let's define it before MealPlan, though Django handles string references well.

class MealPlanItem(models.Model):
    """
    Intermediary model detailing how a specific MealComponent is used within a MealPlan,
    including assignments to specific people.
    """
    meal_plan = models.ForeignKey('MealPlan', on_delete=models.CASCADE, related_name='plan_items')
    meal_component = models.ForeignKey(MealComponent, on_delete=models.CASCADE, related_name='used_in_plans_as_item')
    
    assigned_people = models.ManyToManyField(
        PersonProfile, 
        related_name='meal_plan_items', 
        blank=True, # Allows an item to initially have no one, or for "shared" items if we adapt the convention
        help_text="Specific people this meal component instance is assigned to in this plan. If for all, all plan's people will be linked."
    )
    
    # Optional: Future enhancements
    # quantity_multiplier = models.FloatField(default=1.0, validators=[MinValueValidator(0)], help_text="Multiplier for the component's recipe for this specific assignment (e.g., 0.5 for half portion, 2 for double).")
    # notes = models.TextField(blank=True, null=True, help_text="Notes specific to this component's assignment in this plan.")

    def __str__(self):
        people_count = self.assigned_people.count()
        if people_count > 0:
            return f"{self.meal_component.name} in {self.meal_plan.name} (for {people_count} people)"
        return f"{self.meal_component.name} in {self.meal_plan.name} (unassigned or shared)"

    class Meta:
        ordering = ['meal_plan__name', 'meal_component__name']
        # A component could be added multiple times to a plan if, for example,
        # it's assigned to different groups of people.
        # unique_together = ('meal_plan', 'meal_component') # Reconsider if a component can appear multiple times with different assignments.

class MealPlan(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    duration_days = models.PositiveIntegerField(default=7, validators=[MinValueValidator(1)])
    target_people_profiles = models.ManyToManyField(PersonProfile, related_name='meal_plans', blank=True)
    # meal_components = models.ManyToManyField(MealComponent, related_name='meal_plans', blank=True) # Removed
    servings_per_day_per_person = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)], help_text='e.g., How many meal boxes/main servings per person per day this plan provides nutrition for.') # Defaulted to 1 for simplicity in initial calculation logic
    # owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, help_text="User who created this plan")
    notes = models.TextField(blank=True, null=True)
    creation_date = models.DateTimeField(auto_now_add=True)
    last_modified_date = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-creation_date', 'name']

class FoodPortion(models.Model):
    ingredient = models.ForeignKey(
        Ingredient, 
        on_delete=models.CASCADE, 
        related_name='food_portions',
        help_text="The ingredient this portion information belongs to."
    )
    fdc_portion_id = models.IntegerField(
        null=True, blank=True, db_index=True, 
        help_text="The FDC ID for this specific portion entry (foodPortion.id from FDC data, if available)."
    )
    amount = models.FloatField(
        help_text="The quantity of the measure unit (e.g., 1 for '1 cup', 0.5 for '0.5 piece')."
    )
    portion_description = models.CharField(
        max_length=100, 
        help_text="Full description of the portion (e.g., '1 cup', '1 slice (1 oz)', '100 g'). From FDC portionDescription or constructed."
    )
    gram_weight = models.FloatField(
        validators=[MinValueValidator(0)],
        help_text="The weight of this portion in grams."
    )
    modifier = models.CharField(
        max_length=100, 
        blank=True, null=True,
        help_text="Portion modifier (e.g., 'small', 'large', 'piece', or an FDC code like '10205'). From FDC modifier."
    )
    measure_unit_name = models.CharField(
        max_length=50, blank=True, null=True, 
        help_text="Name of the measure unit (e.g., 'cup', 'tbsp', 'piece'). From FDC measureUnit.name."
    )
    measure_unit_abbreviation = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Abbreviation of the measure unit (e.g., 'cup', 'tsp'). From FDC measureUnit.abbreviation."
    )
    sequence_number = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Order of this portion description for the food item."
    )
    data_points = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Number of samples used to determine portion weight."
    )

    class Meta:
        ordering = ['ingredient__name', 'sequence_number', 'gram_weight']
        # Consider unique_together if needed, e.g.:
        # unique_together = [['ingredient', 'portion_description', 'gram_weight']]
        # Or if fdc_portion_id is reliable and unique per ingredient:
        # unique_together = [['ingredient', 'fdc_portion_id']]
        
    def __str__(self):
        return f"{self.portion_description} ({self.gram_weight}g) for {self.ingredient.name}"
