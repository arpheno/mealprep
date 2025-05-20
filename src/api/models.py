from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.contrib.auth.models import User
from collections import defaultdict


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

    def get_generic_drv(self, drv_type='rda'):
        """
        Helper to get a generic DRV value (RDA or UL) for this nutrient.
        You'll need to define what constitutes a "generic" or "default" DRV.
        This is a placeholder for that logic.
        It attempts to find a DRV for adults.
        """
        from django.db.models import Q  # Ensure Q is imported

        # Attempt to find a DRV for a general adult population.
        # This query is an example and might need adjustment based on your DRV data specifics
        # (e.g., exact strings for target_population, age_range_text, or how gender is handled for defaults).
        # It also doesn't currently differentiate by gender for this generic lookup.
        generic_adult_drvs = self.drvs.filter(
            Q(target_population__icontains='Adult') | Q(target_population__icontains='Adults') |
            Q(age_range_text__icontains='18-') | Q(age_range_text__icontains='19-') | 
            Q(age_range_text__icontains='≥18') | Q(age_range_text__icontains='≥19')
        )

        if not generic_adult_drvs.exists():
            # Fallback: if no specific adult DRV, take any DRV available, preferring those with PRI/AI or UL
            generic_adult_drvs = self.drvs.all()


        value = None
        if drv_type == 'rda':
            # Prioritize PRI, then AI for RDA
            drv = generic_adult_drvs.filter(pri__isnull=False).order_by('pri').first() # Order by pri to get a value, not necessarily lowest/highest specific one
            if drv:
                value = drv.pri
            else:
                drv = generic_adult_drvs.filter(ai__isnull=False).order_by('ai').first()
                if drv:
                    value = drv.ai
        elif drv_type == 'ul':
            # For UL, typically any UL found for adults might be relevant, often the lowest is safest if multiple exist.
            drv = generic_adult_drvs.filter(ul__isnull=False).order_by('ul').first() # Get the lowest UL among adults
            if drv:
                value = drv.ul
        
        # print(f"Nutrient: {self.name}, DRV Type: {drv_type}, Found Value: {value}") # For debugging
        return value

    def get_default_rda(self):
        # This method should return the default RDA value for the nutrient.
        # Placeholder: return a fixed value or look up from a default DRV.
        # For now, let's try to get it from DietaryReferenceValue for a general adult.
        return self.get_generic_drv(drv_type='rda')

    def get_upper_limit(self):
        # This method should return the default UL value for the nutrient.
        # Placeholder: return a fixed value or look up from a default DRV.
        return self.get_generic_drv(drv_type='ul')

    def __str__(self):
        return f'{self.name} ({self.unit})'

    class Meta:
        ordering = ['name']

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
        help_text='Custom nutrient targets for this person, overriding default DRVs. Format: {"Nutrient Name": {"target": value, "unit": "unit", "is_override": true}}'
    )
    notes = models.TextField(blank=True, null=True)
    gender = models.CharField(
        max_length=10,
        choices=Gender.choices,
        null=True,
        blank=True,
        help_text="Gender of the person"
    )
    age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Age of the person in years. Used for DRV calculations."
    )

    def _parse_age_range(self, age_range_text, person_age_years):
        """
        Parses DRV age_range_text and checks if person_age_years falls within it.
        Handles formats like: "X-Y years", "≥X years", "<X years", "X-Y months".
        Returns True if age matches, False otherwise.
        """
        if not person_age_years: # Cannot determine if age is unknown
            return False
            
        age_range_text = age_range_text.lower().strip()

        # Months handling (simplistic: assumes age < 1 year is 0, DRVs handle months)
        if "months" in age_range_text or "month" in age_range_text:
            if person_age_years == 0: # Check for <1 year old
                try:
                    parts = age_range_text.replace("months", "").replace("month", "").strip().split('-')
                    min_months = int(parts[0].strip())
                    # For ranges like "7-11 months"
                    if len(parts) == 2:
                        max_months = int(parts[1].strip())
                        # This logic is tricky as person_age is in years.
                        # A person with age 0 could be 0-11 months.
                        # This requires DRVs to be very specific for <1 year or PersonProfile to store months for <1 year.
                        # For now, if DRV is for months and person_age is 0, we assume it could match.
                        # This is a simplification and might need refinement.
                        return True # Simplified: if person is <1yr and DRV is in months, assume potential match
                    # For single month values e.g. "6 months" (less common for ranges)
                    # This simplistic approach assumes if a DRV is specified in months, and the person is 0 years old, it *could* apply.
                    # A more robust solution would require storing age in months for infants or more detailed DRV age fields.
                    return True
                except ValueError:
                    return False # Cannot parse month range
            else:
                return False # Person is >= 1 year, but DRV is in months

        # Years handling
        try:
            if "≥" in age_range_text or ">=" in age_range_text:
                min_age = int(age_range_text.replace("≥", "").replace(">=", "").replace("years", "").strip())
                return person_age_years >= min_age
            elif "≤" in age_range_text or "<=" in age_range_text:
                max_age = int(age_range_text.replace("≤", "").replace("<=", "").replace("years", "").strip())
                return person_age_years <= max_age
            elif "<" in age_range_text:
                max_age = int(age_range_text.replace("<", "").replace("years", "").strip())
                return person_age_years < max_age
            elif ">" in age_range_text:
                min_age = int(age_range_text.replace(">", "").replace("years", "").strip())
                return person_age_years > min_age
            elif "-" in age_range_text:
                parts = age_range_text.replace("years", "").strip().split('-')
                if len(parts) == 2:
                    min_age = int(parts[0].strip())
                    max_age = int(parts[1].strip())
                    return min_age <= person_age_years <= max_age
            else: # Try to parse as a single age year, e.g. "18 years" (less common for ranges)
                single_age = int(age_range_text.replace("years", "").strip())
                return person_age_years == single_age
        except ValueError:
            return False # Cannot parse year range
        return False

    def get_complete_drvs(self):
        """
        Retrieves all applicable DRVs for the person based on their age and gender,
        then applies any custom overrides.
        DRV types are prioritized: PRI (as RDA), then AI (as RDA if PRI not present), then UL.
        """
        if self.age is None or self.gender is None:
            # If age or gender is not set, we can't reliably determine DRVs.
            # Return custom targets only, or empty if none.
            # Or, could try to fetch "generic" DRVs not specific to age/gender.
            # For now, returning custom targets or empty.
            # Frontend expects nutrientKey: {rda, ul, unit, fdc_nutrient_number}
            
            # Process custom_nutrient_targets to fit the expected structure
            processed_custom_targets = {}
            if isinstance(self.custom_nutrient_targets, dict):
                for name, data in self.custom_nutrient_targets.items():
                    # Attempt to find the nutrient to get its canonical unit and FDC number
                    nutrient_obj = Nutrient.objects.filter_by_name_or_alias(name).first()
                    unit = data.get("unit", nutrient_obj.unit if nutrient_obj else None)
                    fdc_num = nutrient_obj.fdc_nutrient_number if nutrient_obj else None
                    nutrient_key = f"{name} ({unit})" if unit else name

                    processed_custom_targets[nutrient_key] = {
                        "rda": data.get("target"), # Assuming "target" is RDA
                        "ul": None, # Custom targets usually specify RDA/target, not UL
                        "ai": None, # And not AI
                        "unit": unit,
                        "fdc_nutrient_number": fdc_num,
                        "source": "custom_override"
                    }
            return processed_custom_targets

        complete_drvs = {}
        
        # Filter DRVs:
        # 1. Match gender: either person's gender or DRV gender is null/blank (applies to all)
        #    Gender.OTHER and Gender.PREFER_NOT_TO_SAY on PersonProfile might match DRVs with gender=null.
        gender_q = Q(gender=self.gender) | Q(gender__isnull=True) | Q(gender='')
        if self.gender in [Gender.OTHER, Gender.PREFER_NOT_TO_SAY]:
            # For OTHER/NO_SAY, primarily rely on DRVs with null gender (meant for all)
            # or DRVs specifically marked for OTHER if such data exists.
            # This simplifies to effectively matching non-gender-specific DRVs primarily.
            gender_q = Q(gender__isnull=True) | Q(gender='') | Q(gender=self.gender)


        applicable_drvs = DietaryReferenceValue.objects.filter(gender_q)
        
        # Further filter by age text parsing
        # This is done in Python as it's complex for direct ORM query
        matched_by_age_drvs = []
        for drv_instance in applicable_drvs:
            if self._parse_age_range(drv_instance.age_range_text, self.age):
                matched_by_age_drvs.append(drv_instance)

        for drv in matched_by_age_drvs:
            nutrient = drv.nutrient
            nutrient_key = f"{nutrient.name} ({nutrient.unit})" # Standardized key

            if nutrient_key not in complete_drvs:
                complete_drvs[nutrient_key] = {
                    "rda": None, "ul": None, "ai": None, # Initialize
                    "unit": nutrient.unit,
                    "fdc_nutrient_number": nutrient.fdc_nutrient_number,
                    "source": "base_drv"
                }

            # Prioritize PRI as RDA, then AI as RDA
            if drv.pri is not None:
                if complete_drvs[nutrient_key]["rda"] is None: # Only set if not already set by a higher priority PRI
                    complete_drvs[nutrient_key]["rda"] = drv.pri
            if drv.ai is not None:
                if complete_drvs[nutrient_key]["rda"] is None: # AI is used if PRI (primary RDA) is not available
                     complete_drvs[nutrient_key]["ai"] = drv.ai # Store AI separately or merge based on strategy
                     # For now, let's assume frontend wants one "rda" value, so if rda is still None, use AI
                     complete_drvs[nutrient_key]["rda"] = drv.ai


            if drv.ul is not None:
                # If multiple ULs match (e.g. from different source_data_category for same nutrient but should be rare for same age/sex)
                # take the lowest (most restrictive) UL.
                if complete_drvs[nutrient_key]["ul"] is None or drv.ul < complete_drvs[nutrient_key]["ul"]:
                    complete_drvs[nutrient_key]["ul"] = drv.ul
        
        # Apply custom overrides
        if isinstance(self.custom_nutrient_targets, dict):
            for name, data in self.custom_nutrient_targets.items():
                # Attempt to find the nutrient to get its canonical unit and FDC number for key construction
                nutrient_obj = Nutrient.objects.filter_by_name_or_alias(name).first()
                unit_from_data = data.get("unit")
                
                # Determine unit: 1. From data, 2. From nutrient_obj, 3. Fallback to None
                final_unit = unit_from_data if unit_from_data else (nutrient_obj.unit if nutrient_obj else None)
                
                # If unit is still None, we can't form the key correctly, or it might lead to issues.
                # Log this or handle as an error. For now, we'll use the name as key if unit is None.
                nutrient_key = f"{name} ({final_unit})" if final_unit else name
                
                fdc_num = nutrient_obj.fdc_nutrient_number if nutrient_obj else None

                if nutrient_key not in complete_drvs:
                    complete_drvs[nutrient_key] = {
                        "rda": None, "ul": None, "ai": None, 
                        "unit": final_unit, 
                        "fdc_nutrient_number": fdc_num,
                        "source": "custom_override"
                    }
                
                # Override RDA with "target" from custom_nutrient_targets
                if "target" in data and data["target"] is not None:
                    complete_drvs[nutrient_key]["rda"] = data["target"]
                    complete_drvs[nutrient_key]["unit"] = final_unit # Ensure unit from override is used
                    complete_drvs[nutrient_key]["source"] = "custom_override"
                    if nutrient_obj and not complete_drvs[nutrient_key]["fdc_nutrient_number"]:
                        complete_drvs[nutrient_key]["fdc_nutrient_number"] = nutrient_obj.fdc_nutrient_number
                
                # Custom targets might also specify UL or AI, though less common for "target" field
                # if "ul" in data: complete_drvs[nutrient_key]["ul"] = data["ul"]
                # if "ai" in data: complete_drvs[nutrient_key]["ai"] = data["ai"]
        
        # Clean up: remove ai if rda (from pri) was found, or decide if frontend wants both
        # For now, if rda is populated (from PRI or AI), we don't need separate ai field in the final output,
        # unless frontend is specifically designed to use AI when RDA is an estimate.
        # The current logic sets rda = ai if pri is not found. So `ai` field itself is redundant in final output.
        for key in list(complete_drvs.keys()):
            if "ai" in complete_drvs[key]: # And rda is already set
                 del complete_drvs[key]["ai"] # Remove intermediate 'ai' field
            # If RDA is still None after all processing (e.g. only UL was found, no PRI/AI)
            # and no custom override, it remains None.
            if complete_drvs[key]["rda"] is None and \
               complete_drvs[key]["ul"] is None and \
               complete_drvs[key].get("source") != "custom_override": # Don't remove if it's a custom entry even if empty
                del complete_drvs[key] # Remove nutrients for which no values could be found

        return complete_drvs

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
        
    def __str__(self):
        return f"{self.portion_description} ({self.gram_weight}g) for {self.ingredient.name}"
