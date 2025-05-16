"""
Tests for edge cases in the import_custom_drvs management command.
"""
import pytest
from io import StringIO
from django.core.management import call_command
from django.test import override_settings
from api.models import Nutrient, DietaryReferenceValue, Gender, NutrientCategory


@pytest.mark.django_db
class TestImportCustomDrvsEdgeCases:
    """Test edge cases for the import_custom_drvs management command."""

    def setup_method(self):
        """Set up test data for each test method."""
        # Create some nutrients for testing
        self.vitamin_c = Nutrient.objects.create(
            name="Vitamin C",
            unit="mg",
            category=NutrientCategory.VITAMIN
        )

    def test_missing_csv_file(self):
        """Test handling of a missing CSV file."""
        # Use a non-existent file path
        with override_settings(CSV_FILE_PATH="non_existent_file.csv"):
            output = StringIO()
            call_command('import_custom_drvs', stdout=output, stderr=output)
            
            # Check the error message in the output
            output_text = output.getvalue()
            assert "Error: CSV file not found" in output_text

    def test_empty_csv_file(self, tmp_path):
        """Test handling of an empty CSV file."""
        # Create an empty CSV file
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("")
        
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', stdout=output, stderr=output)
            
            # Check the error message in the output
            output_text = output.getvalue()
            assert "empty or has no header" in output_text

    def test_invalid_csv_headers(self, tmp_path):
        """Test handling of a CSV file with invalid headers."""
        # Create a CSV with invalid headers
        invalid_csv_content = "Wrong,Headers,Here\n1,2,3\n"
        csv_file = tmp_path / "invalid_headers.csv"
        csv_file.write_text(invalid_csv_content)
        
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', stdout=output, stderr=output)
            
            # Check the error message in the output
            output_text = output.getvalue()
            assert "missing expected headers" in output_text

    def test_invalid_gender_value(self, tmp_path):
        """Test handling of a CSV file with an invalid gender value."""
        # Create a CSV with an invalid gender value
        invalid_gender_csv = """Category,Nutrient,Target population,Age,Gender,frequency,unit,AI,AR,PRI,RI,UL
Vitamins,Vitamin C,Adults,≥ 18 years,INVALID_GENDER,daily,mg,75,60,80,,2000
"""
        csv_file = tmp_path / "invalid_gender.csv"
        csv_file.write_text(invalid_gender_csv)
        
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', stdout=output)
            
            # Check that the command warns about invalid gender
            output_text = output.getvalue()
            assert "Unknown gender 'INVALID_GENDER'" in output_text
            
            # Check that no DRVs were created for the invalid gender entry
            drv_count = DietaryReferenceValue.objects.count()
            assert drv_count == 0

    def test_invalid_nutrient_values(self, tmp_path):
        """Test handling of a CSV file with invalid nutrient values."""
        # Create a CSV with invalid nutrient values
        invalid_value_csv = """Category,Nutrient,Target population,Age,Gender,frequency,unit,AI,AR,PRI,RI,UL
Vitamins,Vitamin C,Adults,≥ 18 years,Female,daily,mg,not_a_number,sixty,80.0,,2000
"""
        csv_file = tmp_path / "invalid_values.csv"
        csv_file.write_text(invalid_value_csv)
        
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', stdout=output)
            
            # The command should continue but parse these as None
            vitamin_c_drv = DietaryReferenceValue.objects.filter(
                nutrient=self.vitamin_c,
                gender=Gender.FEMALE
            ).first()
            
            assert vitamin_c_drv is not None
            assert vitamin_c_drv.ai is None  # "not_a_number" should be parsed as None
            # Both numeric and non-numeric values should be handled
            assert vitamin_c_drv.pri == 80.0  # This was a valid float
            assert vitamin_c_drv.ul == 2000.0  # This was a valid float

    def test_nutrient_name_partial_match(self, tmp_path):
        """Test matching of nutrients with partial name matches."""
        # Create nutrients with similar names
        vitamin_b12 = Nutrient.objects.create(
            name="Vitamin B-12",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )
        
        vitamin_b12_cyano = Nutrient.objects.create(
            name="Vitamin B-12 (Cyanocobalamin)",
            unit="µg",
            category=NutrientCategory.VITAMIN
        )
        
        # Create a CSV with different variants of B12
        b12_csv = """Category,Nutrient,Target population,Age,Gender,frequency,unit,AI,AR,PRI,RI,UL
Vitamins,Vitamin B12,Adults,≥ 18 years,Female,daily,µg,2.4,,,,
Vitamins,Cyanocobalamin,Adults,≥ 18 years,Male,daily,µg,2.8,,,,
"""
        csv_file = tmp_path / "b12_variants.csv"
        csv_file.write_text(b12_csv)
        
        with override_settings(CSV_FILE_PATH=str(csv_file)):
            output = StringIO()
            call_command('import_custom_drvs', stdout=output)
            
            # Check that both nutrient variants were matched correctly
            b12_female_drv = DietaryReferenceValue.objects.filter(
                nutrient=vitamin_b12,
                gender=Gender.FEMALE
            ).first()
            
            b12_cyano_drv = DietaryReferenceValue.objects.filter(
                nutrient=vitamin_b12_cyano,
                gender=Gender.MALE
            ).first()
            
            # Check that at least one of the DRVs exists
            assert b12_female_drv is not None
            # Test that the created DRV has the correct AI value (approximate)
            if b12_female_drv:
                assert abs(b12_female_drv.ai - 2.4) < 0.1
            
            assert b12_cyano_drv is not None
            if b12_cyano_drv:
                assert abs(b12_cyano_drv.ai - 2.8) < 0.1
