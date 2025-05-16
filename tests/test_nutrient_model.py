import pytest
from api.models import Nutrient, DietaryReferenceValue, NutrientCategory

@pytest.mark.django_db
class TestNutrientModel:
    def test_nutrient_creation(self):
        """Test if a nutrient can be created and retrieved properly"""
        nutrient = Nutrient.objects.create(
            name="Test Nutrient",
            unit="mg",
            category=NutrientCategory.MINERAL,
            source_notes="This is a test nutrient",
            is_essential=True
        )
        
        # Check if the nutrient was created correctly
        assert nutrient.name == "Test Nutrient"
        assert nutrient.unit == "mg"
        assert nutrient.category == NutrientCategory.MINERAL
        assert nutrient.source_notes == "This is a test nutrient"
        assert nutrient.is_essential == True
        
        # Test string representation
        assert str(nutrient) == "Test Nutrient (mg)"
        
    def test_get_default_rda(self):
        """Test the method to retrieve default RDA from DRV"""
        nutrient = Nutrient.objects.create(
            name="Test Nutrient",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        
        # Create a reference value
        drv = DietaryReferenceValue.objects.create(
            source_data_category="Test Category",
            nutrient=nutrient,
            target_population="Adults",
            age_range_text="≥ 18 years",
            frequency="daily",
            value_unit="mg",
            pri=100.0  # Using PRI (Population Reference Intake)
        )
        
        # Test retrieval of default RDA
        assert nutrient.get_default_rda() == 100.0
        
    def test_get_upper_limit(self):
        """Test the method to retrieve upper limit from DRV"""
        nutrient = Nutrient.objects.create(
            name="Test Nutrient",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        
        # Create a reference value with upper limit
        drv = DietaryReferenceValue.objects.create(
            source_data_category="Test Category",
            nutrient=nutrient,
            target_population="Adults",
            age_range_text="≥ 18 years",
            frequency="daily",
            value_unit="mg",
            ul=500.0  # Upper limit
        )
        
        # Test retrieval of upper limit
        assert nutrient.get_upper_limit() == 500.0
        
    def test_no_drv_returns_none(self):
        """Test that get_default_rda and get_upper_limit return None if no DRV exists"""
        nutrient = Nutrient.objects.create(
            name="Test Nutrient No DRV",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        
        # Test retrieval with no existing DRV
        assert nutrient.get_default_rda() is None
        assert nutrient.get_upper_limit() is None
