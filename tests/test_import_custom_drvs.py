"""
Tests for the import_custom_drvs management command.
"""
import os
import csv
from io import StringIO
from tempfile import NamedTemporaryFile
import pytest
from django.core.management import call_command
from django.test import TestCase, override_settings
from api.models import Nutrient, DietaryReferenceValue, Gender, NutrientCategory


@pytest.mark.django_db
class TestImportCustomDrvs:
    """Test the import_custom_drvs management command."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Create some nutrients for testing
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

        self.vitamin_k = Nutrient.objects.create(
            name="Vitamin K",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )

        self.test_csv_content = """Category,Nutrient,Target population,Age,Gender,frequency,unit,AI,AR,PRI,RI,UL
Carbohydrates,Dietary fibre,Adults,≥ 18 years,Male,daily,g,25,,,,
Vitamins,Vitamin C,Adults,≥ 18 years,Female,daily,mg,75,60,80,,2000
Vitamins,Vitamin K,Adults,≥ 18 years,both genders,daily,µg,70,,,100,
Macronutrients,Protein,Adults,≥ 18 years,Male,daily,g,,0.83,,,
Energy,Energy,Adults,≥ 18 years,Female,daily,kcal,,,2000,,
"""

    def test_import_new_drvs(self, tmp_path):
        """Test importing new DRV entries from a CSV file."""
        # Create a temporary CSV file
        csv_file = tmp_path / "test_drv.csv"
        csv_file.write_text(self.test_csv_content)
        
        # Override the CSV file path in the command
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            # Call the command
            output = StringIO()
            call_command('import_custom_drvs', stdout=output)
            command_output = output.getvalue()
            
            # Check the output
            assert "Successfully created entries: " in command_output
            
            # Check that relevant DRVs were created
            # Energy for female adults
            energy_drv = DietaryReferenceValue.objects.filter(
                nutrient=self.energy,
                gender=Gender.FEMALE,
                age_range_text="≥ 18 years"
            ).first()
            
            assert energy_drv is not None
            assert energy_drv.pri == 2000.0
            assert energy_drv.frequency == "daily"
            
            # Vitamin C for female adults
            vitamin_c_drv = DietaryReferenceValue.objects.filter(
                nutrient=self.vitamin_c,
                gender=Gender.FEMALE,
                age_range_text="≥ 18 years"
            ).first()
            
            assert vitamin_c_drv is not None
            assert vitamin_c_drv.ai == 75.0
            assert vitamin_c_drv.ar == 60.0
            assert vitamin_c_drv.pri == 80.0
            assert vitamin_c_drv.ul == 2000.0
            
            # Vitamin K for both genders
            vitamin_k_drv = DietaryReferenceValue.objects.filter(
                nutrient=self.vitamin_k,
                gender=None,  # None represents both genders
                age_range_text="≥ 18 years"
            ).first()
            
            assert vitamin_k_drv is not None
            assert vitamin_k_drv.ai == 70.0
            assert vitamin_k_drv.ri == 100.0
            
            # Should not find an entry for Dietary Fibre (not in our test nutrients)
            dietary_fibre_count = DietaryReferenceValue.objects.filter(
                nutrient__name="Dietary fibre"
            ).count()
            assert dietary_fibre_count == 0

    def test_update_existing_drvs(self, tmp_path):
        """Test updating existing DRV entries from a CSV file."""
        # Create an existing DRV
        existing_drv = DietaryReferenceValue.objects.create(
            source_data_category="Vitamins",
            nutrient=self.vitamin_c,
            target_population="Adults",
            age_range_text="≥ 18 years",
            gender=Gender.FEMALE,
            frequency="daily",
            value_unit="mg",
            ai=60.0,  # Will be updated to 75.0
            ar=50.0,  # Will be updated to 60.0
            pri=70.0  # Will be updated to 80.0
        )
        
        # Create a temporary CSV file
        csv_file = tmp_path / "test_drv.csv"
        csv_file.write_text(self.test_csv_content)
        
        # Call the command with --update-existing
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', update_existing=True, stdout=output)
            command_output = output.getvalue()
            
            # Check the output
            assert "Successfully updated entries: " in command_output
            
            # Refresh the DRV from the database
            existing_drv.refresh_from_db()
            
            # Check that values were updated
            assert existing_drv.ai == 75.0
            assert existing_drv.ar == 60.0
            assert existing_drv.pri == 80.0
            assert existing_drv.ul == 2000.0

    def test_dry_run_mode(self, tmp_path):
        """Test the dry run mode."""
        # Create a temporary CSV file
        csv_file = tmp_path / "test_drv.csv"
        csv_file.write_text(self.test_csv_content)
        
        # Get initial count of DRVs
        initial_count = DietaryReferenceValue.objects.count()
        
        # Call the command with --dry-run
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', dry_run=True, stdout=output)
            command_output = output.getvalue()
            
            # Check the output
            assert "Dry run complete." in command_output
            assert "Would create DRV for" in command_output
            
            # Check that no DRVs were actually created
            assert DietaryReferenceValue.objects.count() == initial_count

    def test_nutrient_name_variants(self):
        """Test the nutrient name variant generation and matching."""
        # Import the function directly from the module
        from api.management.commands.import_custom_drvs import get_nutrient_name_variants, find_nutrient
        
        # Test get_nutrient_name_variants
        variants = get_nutrient_name_variants("Vitamin B-12 (Cobalamin)")
        
        # Check that various expected variants are present
        assert "Vitamin B-12 (Cobalamin)" in variants
        assert "vitamin b-12 (cobalamin)" in variants
        assert "Vitamin B12 (Cobalamin)" in variants
        assert "vitamin b12 (cobalamin)" in variants
        assert "Cobalamin" in variants
        assert "cobalamin" in variants
        
        # Test with a simpler name
        variants = get_nutrient_name_variants("Vitamin C")
        assert "Vitamin C" in variants
        assert "vitamin c" in variants
        
        # Test vitamins with B numbering conversion
        variants = get_nutrient_name_variants("Vitamin B6")
        assert "Vitamin B-6" in variants
        assert "vitamin b-6" in variants
        
        # Create a mock nutrient cache for testing find_nutrient
        mock_cache = [
            {
                'id': 1,
                'original_name': 'Vitamin C',
                'name_variants': get_nutrient_name_variants('Vitamin C'),
                'obj': self.vitamin_c
            },
            {
                'id': 2,
                'original_name': 'Protein',
                'name_variants': get_nutrient_name_variants('Protein'),
                'obj': self.protein
            }
        ]
        
        # Test find_nutrient with exact match
        result = find_nutrient("Vitamin C", mock_cache)
        assert result['id'] == 1
        assert result['obj'] == self.vitamin_c
        
        # Test find_nutrient with case insensitivity
        result = find_nutrient("vitamin c", mock_cache)
        assert result['id'] == 1
        
        # Test find_nutrient with no match
        result = find_nutrient("Zinc", mock_cache)
        assert result is None
