"""
Tests for edge cases in the nutrient matching functions in import_custom_drvs.py
"""
import pytest
from api.models import Nutrient, NutrientCategory
from api.management.commands.import_custom_drvs import get_nutrient_name_variants, find_nutrient


@pytest.mark.django_db
class TestFindNutrientEdgeCases:
    """Test edge cases for the find_nutrient function."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Create nutrients with names that might be tricky to match
        self.vitamin_b12 = Nutrient.objects.create(
            name="Vitamin B-12 (Cobalamin)",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )
        
        self.vitamin_b6 = Nutrient.objects.create(
            name="Vitamin B6",  # Note no hyphen
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        
        self.vitamin_k = Nutrient.objects.create(
            name="Vitamin K",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )
        
        self.vitamin_k2 = Nutrient.objects.create(
            name="Vitamin K2 (Menaquinone)",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )
        
        # EPA and DHA separately
        self.epa = Nutrient.objects.create(
            name="Eicosapentaenoic acid (EPA)",
            unit="mg",
            category=NutrientCategory.MACRONUTRIENT
        )
        
        self.dha = Nutrient.objects.create(
            name="Docosahexaenoic acid (DHA)",
            unit="mg",
            category=NutrientCategory.MACRONUTRIENT
        )

    def test_variant_generation_with_different_formats(self):
        """Test the variant generation with different formatted names."""
        # Hyphenated name variant generation
        variants = get_nutrient_name_variants("Vitamin B-12")
        assert "Vitamin B12" in variants
        assert "Vitamin B-12" in variants
        assert "vitamin b12" in variants
        assert "vitamin b-12" in variants
        
        # Parentheses handling
        variants = get_nutrient_name_variants("Vitamin D (Calciferol)")
        assert "Vitamin D" in variants
        assert "Calciferol" in variants
        assert "calciferol" in variants
        
        # Spaces and special characters
        variants = get_nutrient_name_variants("  Vitamin   E  ")
        assert "Vitamin E" in variants
        
        # Empty string edge case
        variants = get_nutrient_name_variants("")
        assert len(variants) == 0

    def test_find_nutrient_with_variant_formats(self):
        """Test finding nutrients with various format variations."""
        from api.management.commands.import_custom_drvs import get_nutrient_name_variants, find_nutrient
        
        # Create processed cache for testing
        db_nutrients_cache = []
        for n_obj in [self.vitamin_b12, self.vitamin_b6, self.vitamin_k, self.vitamin_k2, self.epa, self.dha]:
            db_nutrients_cache.append({
                'id': n_obj.id,
                'original_name': n_obj.name,
                'obj': n_obj,
                'name_variants': get_nutrient_name_variants(n_obj.name)
            })
        
        # Test with B12 variants
        result = find_nutrient("Vitamin B12", db_nutrients_cache)
        assert result['id'] == self.vitamin_b12.id
        
        result = find_nutrient("Cobalamin", db_nutrients_cache)
        assert result['id'] == self.vitamin_b12.id
        
        # Test with B6 variants
        result = find_nutrient("Vitamin B-6", db_nutrients_cache)
        assert result['id'] == self.vitamin_b6.id
        
        # Test with K variants
        result = find_nutrient("Vitamin K", db_nutrients_cache)
        assert result['id'] == self.vitamin_k.id
        
        result = find_nutrient("Vitamin K2", db_nutrients_cache)
        assert result['id'] == self.vitamin_k2.id
        
        result = find_nutrient("Menaquinone", db_nutrients_cache)
        assert result['id'] == self.vitamin_k2.id
        
    def test_find_nutrient_with_epa_dha_special_handling(self):
        """Test the special handling for EPA/DHA combinations."""
        from api.management.commands.import_custom_drvs import get_nutrient_name_variants, find_nutrient
        
        # Create processed cache for testing
        db_nutrients_cache = []
        for n_obj in [self.vitamin_b12, self.vitamin_b6, self.vitamin_k, self.vitamin_k2, self.epa, self.dha]:
            db_nutrients_cache.append({
                'id': n_obj.id,
                'original_name': n_obj.name,
                'obj': n_obj,
                'name_variants': get_nutrient_name_variants(n_obj.name)
            })
        
        # Test EPA by itself
        result = find_nutrient("EPA", db_nutrients_cache)
        assert result['id'] == self.epa.id
        
        # Test DHA by itself
        result = find_nutrient("DHA", db_nutrients_cache)
        assert result['id'] == self.dha.id
        
        # Test combined EPA+DHA - this should return the first one found based on current implementation
        # You might want to enhance the implementation to handle this special case better
        result = find_nutrient("EPA and DHA", db_nutrients_cache)
        assert result is not None  # For now, just check that something is returned
        
        # More specific combined format often seen in DRV sources
        result = find_nutrient("Eicosapentaenoic acid (EPA) + Docosahexaenoic acid (DHA)", db_nutrients_cache)
        assert result is not None  # Should match one of them
        
    def test_no_match_handling(self):
        """Test that non-existent nutrients return None."""
        from api.management.commands.import_custom_drvs import get_nutrient_name_variants, find_nutrient
        
        # Create processed cache for testing
        db_nutrients_cache = []
        for n_obj in [self.vitamin_b12, self.vitamin_b6, self.vitamin_k, self.vitamin_k2, self.epa, self.dha]:
            db_nutrients_cache.append({
                'id': n_obj.id,
                'original_name': n_obj.name,
                'obj': n_obj, 
                'name_variants': get_nutrient_name_variants(n_obj.name)
            })
        
        # Test with a non-existent nutrient
        result = find_nutrient("Vibranium", db_nutrients_cache)
        assert result is None
        
        # Test with empty string
        result = find_nutrient("", db_nutrients_cache)
        assert result is None
        
        # Test with None
        result = find_nutrient(None, db_nutrients_cache)
        assert result is None
