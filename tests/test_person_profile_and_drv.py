import pytest
from api.models import (
    Nutrient, PersonProfile, DietaryReferenceValue, 
    Gender, ActivityLevel, NutrientCategory
)

@pytest.mark.django_db
class TestPersonProfileModel:
    def setup_method(self):
        """Set up test data for each test method"""
        # Create sample nutrients
        self.energy = Nutrient.objects.create(
            name="Energy",
            unit="kcal",
            category=NutrientCategory.GENERAL
        )
        
        self.protein = Nutrient.objects.create(
            name="Protein",
            unit="g",
            category=NutrientCategory.MACRONUTRIENT
        )
        
        self.vitamin_c = Nutrient.objects.create(
            name="Vitamin C",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        
        # Create DRVs for the nutrients
        DietaryReferenceValue.objects.create(
            source_data_category="General",
            nutrient=self.energy,
            target_population="Adults",
            age_range_text="≥ 18 years",
            frequency="daily",
            value_unit="kcal",
            pri=2000.0,  # PRI (Population Reference Intake)
            ul=4000.0    # Upper Limit
        )
        
        DietaryReferenceValue.objects.create(
            source_data_category="Macronutrients",
            nutrient=self.protein,
            target_population="Adults",
            age_range_text="≥ 18 years",
            frequency="daily",
            value_unit="g",
            pri=56.0,  # PRI for males
            ul=None    # No established UL for protein
        )
        
        DietaryReferenceValue.objects.create(
            source_data_category="Vitamins",
            nutrient=self.vitamin_c,
            target_population="Adults",
            age_range_text="≥ 18 years",
            frequency="daily",
            value_unit="mg",
            pri=90.0,  # PRI
            ul=2000.0  # UL
        )
        # Create a person profile
        self.person = PersonProfile.objects.create(
            name="Test Person",
            age=30, # Changed from age_years, removed weight_kg, height_cm, activity_level
            gender=Gender.MALE.value, # Ensure .value is used for CharField choices
            custom_nutrient_targets={
                "Protein": {"target": 120, "unit": "g", "is_override": True},
                "Custom Nutrient": {"target": 50, "unit": "µg", "is_override": True}
            }
        )
    
    def test_person_profile_creation(self):
        """Test basic person profile creation and properties"""
        assert self.person.name == "Test Person"
        assert self.person.age == 30 # Changed from age_years
        assert self.person.gender == Gender.MALE.value # Ensure .value is used for CharField choices
        # Removed assertions for weight_kg, height_cm, activity_level
        
        # Test custom nutrient targets
        assert "Protein" in self.person.custom_nutrient_targets
        assert self.person.custom_nutrient_targets["Protein"]["target"] == 120
        assert "Custom Nutrient" in self.person.custom_nutrient_targets
    
    def test_get_personalized_drvs(self):
        """Test retrieval of personalized dietary reference values"""
        drvs = self.person.get_complete_drvs() # Changed to get_complete_drvs
        
        # Check if system nutrients with system DRVs are present
        # Keys in get_complete_drvs include unit, so adjust assertions
        assert f"Energy ({self.energy.unit})" in drvs
        assert f"Protein ({self.protein.unit})" in drvs
        assert f"Vitamin C ({self.vitamin_c.unit})" in drvs
        
        # Check if custom targets override system values
        assert drvs[f"Energy ({self.energy.unit})"]["rda"] == 2000.0  # System value
        assert drvs[f"Protein ({self.protein.unit})"]["rda"] == 120.0  # Custom override
        assert drvs[f"Vitamin C ({self.vitamin_c.unit})"]["rda"] == 90.0  # System value
        
        # Check upper limits
        assert drvs[f"Energy ({self.energy.unit})"]["ul"] == 4000.0
        # Protein UL is None in DRV, so it should be None here unless overridden
        assert drvs[f"Protein ({self.protein.unit})"]["ul"] is None 
        assert drvs[f"Vitamin C ({self.vitamin_c.unit})"]["ul"] == 2000.0
        
        # Check for custom nutrients not in the system
        # Custom Nutrient key will be "Custom Nutrient (µg)" due to unit in custom_nutrient_targets
        assert "Custom Nutrient (µg)" in drvs 
        assert drvs["Custom Nutrient (µg)"]["rda"] == 50
        assert drvs["Custom Nutrient (µg)"]["unit"] == "µg"
        
    def test_default_nutrient_targets(self):
        """Test the default nutrient targets when creating a new profile"""
        # Create a new profile without specifying custom targets
        new_person = PersonProfile.objects.create(
            name="Default Target Person"
        )
        
        # The default function should have created Energy and Protein targets
        assert "Energy" in new_person.custom_nutrient_targets
        assert "Protein" in new_person.custom_nutrient_targets
        
        # Default values should be set
        assert new_person.custom_nutrient_targets["Energy"]["target"] == 2000
        assert new_person.custom_nutrient_targets["Energy"]["unit"] == "kcal"
        
        assert new_person.custom_nutrient_targets["Protein"]["target"] == 75
        assert new_person.custom_nutrient_targets["Protein"]["unit"] == "g"


@pytest.mark.django_db
class TestDietaryReferenceValueModel:
    def test_drv_creation(self):
        """Test creation of Dietary Reference Values"""
        # Create a nutrient
        vitamin_d = Nutrient.objects.create(
            name="Vitamin D",
            unit="μg",
            category=NutrientCategory.VITAMIN
        )
        
        # Create DRVs for different population groups
        drv_adults = DietaryReferenceValue.objects.create(
            source_data_category="Vitamins",
            nutrient=vitamin_d,
            target_population="Adults",
            age_range_text="18-70 years",
            frequency="daily",
            value_unit="μg",
            ai=15.0,    # Adequate Intake
            ul=100.0    # Upper Limit
        )
        
        drv_elderly = DietaryReferenceValue.objects.create(
            source_data_category="Vitamins",
            nutrient=vitamin_d,
            target_population="Elderly",
            age_range_text=">70 years",
            gender=Gender.MALE,
            frequency="daily",
            value_unit="μg",
            ai=20.0,    # Adequate Intake for elderly
            ul=100.0    # Upper Limit
        )
        
        # Basic assertions
        assert drv_adults.nutrient.name == "Vitamin D"
        assert drv_adults.target_population == "Adults"
        assert drv_adults.ai == 15.0
        assert drv_adults.ul == 100.0
        
        assert drv_elderly.target_population == "Elderly"
        assert drv_elderly.gender == Gender.MALE
        assert drv_elderly.ai == 20.0
        
        # Test string representation
        assert str(drv_adults) == "DRV for Vitamin D: Pop: Adults, Age: 18-70 years, Gender: Both genders"
        assert str(drv_elderly) == "DRV for Vitamin D: Pop: Elderly, Age: >70 years, Gender: Male"
        
    def test_nutrient_drv_relationship(self):
        """Test the relationship between Nutrient and DietaryReferenceValue"""
        # Create a nutrient
        calcium = Nutrient.objects.create(
            name="Calcium",
            unit="mg",
            category=NutrientCategory.MINERAL
        )
        
        # Create multiple DRVs for the nutrient
        drv1 = DietaryReferenceValue.objects.create(
            source_data_category="Minerals",
            nutrient=calcium,
            target_population="Adults",
            age_range_text="19-50 years",
            frequency="daily",
            value_unit="mg",
            pri=1000.0,
            ul=2500.0
        )
        
        drv2 = DietaryReferenceValue.objects.create(
            source_data_category="Minerals",
            nutrient=calcium,
            target_population="Adults",
            age_range_text="51+ years",
            frequency="daily",
            value_unit="mg",
            pri=1200.0,
            ul=2000.0
        )
        
        drv3 = DietaryReferenceValue.objects.create(
            source_data_category="Minerals",
            nutrient=calcium,
            target_population="Children",
            age_range_text="9-18 years",
            frequency="daily",
            value_unit="mg",
            pri=1300.0,
            ul=3000.0
        )
        
        # Test accessing DRVs from the nutrient
        assert calcium.drvs.count() == 3
        
        # Test filtering DRVs
        adult_drvs = calcium.drvs.filter(target_population="Adults")
        assert adult_drvs.count() == 2
        
        children_drvs = calcium.drvs.filter(target_population="Children")
        assert children_drvs.count() == 1
        assert children_drvs.first().pri == 1300.0
