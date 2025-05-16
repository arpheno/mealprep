"""
Tests for utility functions in the import_custom_drvs management command.
"""
import pytest
from api.management.commands.import_custom_drvs import (
    parse_float_or_none, 
    extract_parentheses_content,
    get_nutrient_name_variants,
    find_nutrient
)
from api.models import Nutrient, NutrientCategory


class TestParseFloatOrNone:
    """Test the parse_float_or_none function."""
    
    def test_valid_float(self):
        """Test parsing valid float values."""
        assert parse_float_or_none("123.45") == 123.45
        assert parse_float_or_none("0") == 0.0
        assert parse_float_or_none("-10.5") == -10.5
        assert parse_float_or_none("1e3") == 1000.0
    
    def test_invalid_float(self):
        """Test parsing invalid float values."""
        assert parse_float_or_none("not a number") is None
        assert parse_float_or_none("123abc") is None
        assert parse_float_or_none("12,345") is None  # Comma as thousand separator
    
    def test_empty_and_none_values(self):
        """Test parsing empty and None values."""
        assert parse_float_or_none("") is None
        assert parse_float_or_none(None) is None
        assert parse_float_or_none("   ") is None  # Whitespace only
    
    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        assert parse_float_or_none(" 123.45 ") == 123.45
        assert parse_float_or_none("\t42\n") == 42.0


class TestExtractParenthesesContent:
    """Test the extract_parentheses_content function."""
    
    def test_basic_extraction(self):
        """Test basic extraction of content within parentheses."""
        assert extract_parentheses_content("Vitamin A (Retinol)") == "Retinol"
        assert extract_parentheses_content("Thiamin (Vitamin B-1)") == "Vitamin B-1"
    
    def test_no_parentheses(self):
        """Test extraction when there are no parentheses."""
        assert extract_parentheses_content("Vitamin C") is None
        assert extract_parentheses_content("") is None
        assert extract_parentheses_content(None) is None
    
    def test_multiple_parentheses(self):
        """Test extraction with multiple parentheses - should return first match."""
        assert extract_parentheses_content("EPA (20:5 n-3) (Omega-3)") == "20:5 n-3"
    
    def test_nested_parentheses(self):
        """Test extraction with nested parentheses."""
        # Current implementation doesn't handle nested parentheses specially
        assert extract_parentheses_content("Outer (Inner (Nested))") == "Inner (Nested"


class TestGetNutrientNameVariants:
    """Test the get_nutrient_name_variants function."""
    
    def test_simple_name(self):
        """Test variants for a simple name."""
        variants = get_nutrient_name_variants("Vitamin C")
        assert "Vitamin C" in variants
        assert "vitamin c" in variants
        assert len(variants) >= 2
    
    def test_hyphenated_name(self):
        """Test variants for a name with hyphens."""
        variants = get_nutrient_name_variants("Vitamin B-6")
        assert "Vitamin B-6" in variants
        assert "vitamin b-6" in variants
        assert "Vitamin B6" in variants
        assert "vitamin b6" in variants
        assert len(variants) >= 4
    
    def test_name_with_parentheses(self):
        """Test variants for a name with parentheses."""
        variants = get_nutrient_name_variants("Folate (Vitamin B-9)")
        assert "Folate (Vitamin B-9)" in variants
        assert "folate (vitamin b-9)" in variants
        # Check that base name (before parenthesis) is included
        assert "Folate" in variants or "folate" in variants
        # Check parenthetical content
        assert "Vitamin B-9" in variants
        assert "vitamin b-9" in variants
        assert "Vitamin B9" in variants
        assert "vitamin b9" in variants
        assert len(variants) >= 8
    
    def test_vitamin_b_numbering(self):
        """Test special handling of vitamin B numbering."""
        variants = get_nutrient_name_variants("Vitamin B1")
        assert "Vitamin B1" in variants
        assert "Vitamin B-1" in variants
        assert "vitamin b-1" in variants
        
        variants = get_nutrient_name_variants("Vitamin B12")
        assert "Vitamin B12" in variants
        assert "Vitamin B-12" in variants


@pytest.mark.django_db
class TestFindNutrient:
    """Test the find_nutrient function."""
    
    def setup_method(self):
        """Set up test data."""
        # Create test nutrients
        self.vitamin_c = Nutrient.objects.create(
            name="Vitamin C",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )
        
        self.vitamin_b12 = Nutrient.objects.create(
            name="Vitamin B-12 (Cobalamin)",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )
        
        self.omega3 = Nutrient.objects.create(
            name="Omega-3 fatty acids",
            unit="g",
            category=NutrientCategory.MACRONUTRIENT
        )
        
        # Prepare the nutrient cache format
        self.nutrient_cache = [
            {
                'id': self.vitamin_c.id,
                'original_name': self.vitamin_c.name,
                'obj': self.vitamin_c,
                'name_variants': get_nutrient_name_variants(self.vitamin_c.name)
            },
            {
                'id': self.vitamin_b12.id,
                'original_name': self.vitamin_b12.name,
                'obj': self.vitamin_b12,
                'name_variants': get_nutrient_name_variants(self.vitamin_b12.name)
            },
            {
                'id': self.omega3.id,
                'original_name': self.omega3.name,
                'obj': self.omega3,
                'name_variants': get_nutrient_name_variants(self.omega3.name)
            }
        ]
    
    def test_exact_match(self):
        """Test finding a nutrient with exact match."""
        result = find_nutrient("Vitamin C", self.nutrient_cache)
        assert result['id'] == self.vitamin_c.id
        assert result['obj'] == self.vitamin_c
    
    def test_case_insensitive_match(self):
        """Test finding a nutrient with case-insensitive match."""
        result = find_nutrient("vitamin c", self.nutrient_cache)
        assert result['id'] == self.vitamin_c.id
    
    def test_variant_match(self):
        """Test finding a nutrient using variant names."""
        # Match on no hyphen variant
        result = find_nutrient("Vitamin B12", self.nutrient_cache)
        assert result['id'] == self.vitamin_b12.id
        
        # Match on content in parentheses
        result = find_nutrient("Cobalamin", self.nutrient_cache)
        assert result['id'] == self.vitamin_b12.id
        
        # Match on variant without hyphen
        result = find_nutrient("Omega 3 fatty acids", self.nutrient_cache)
        assert result['id'] == self.omega3.id
    
    def test_no_match(self):
        """Test when no nutrient matches."""
        result = find_nutrient("Zinc", self.nutrient_cache)
        assert result is None
        
        result = find_nutrient("", self.nutrient_cache)
        assert result is None
