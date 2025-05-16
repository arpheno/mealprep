import csv
import re
import os
import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings
from api.models import Nutrient, DietaryReferenceValue, Gender # Ensure Gender is imported

# Define the path to the CSV file, relative to the project root
# Default path that can be overridden via settings
def get_csv_path():
    return getattr(settings, 'CSV_FILE_PATH', "data/drv.csv")

# Column names from the CSV
# Category,Nutrient,Target population,Age,Gender,frequency,unit,AI,AR,PRI,RI,UL

def parse_float_or_none(value_str):
    """
    Attempts to convert a string to a float.
    Returns None if the string is empty, None, or cannot be converted.
    """
    if value_str is None:
        return None
    value_str = str(value_str).strip()
    if not value_str:
        return None
    try:
        return float(value_str)
    except ValueError:
        return None

# Helper function to extract content from parentheses (from import_efsa_drvs.py)
def extract_parentheses_content(name_str):
    if name_str is None:
        return None
    match = re.search(r'\((.*?)\)', name_str)
    if match:
        return match.group(1).strip()
    return None

def get_nutrient_name_variants(nutrient_name):
    """
    Generates a list of name variants for a nutrient name for matching.
    """
    variants = set()
    
    # Return empty list for None or empty string
    if nutrient_name is None or not nutrient_name.strip():
        return list(variants)
    
    # Normalize whitespace - replace multiple spaces with a single space
    nutrient_name = " ".join(nutrient_name.strip().split())
    name_lower = nutrient_name.lower()

    # Original and lowercase
    variants.add(nutrient_name) # Already normalized
    variants.add(name_lower)

    # Hyphens removed / replaced by space
    name_no_hyphen = nutrient_name.replace('-', '')
    name_hyphen_as_space = nutrient_name.replace('-', ' ')
    variants.add(name_no_hyphen)
    variants.add(name_no_hyphen.lower())
    variants.add(name_hyphen_as_space)
    variants.add(name_hyphen_as_space.lower())

    # Content within parentheses
    content_in_paren = extract_parentheses_content(nutrient_name)
    if content_in_paren:
        variants.add(content_in_paren)
        variants.add(content_in_paren.lower())
        paren_no_hyphen = content_in_paren.replace('-', '')
        paren_hyphen_as_space = content_in_paren.replace('-', ' ')
        variants.add(paren_no_hyphen)
        variants.add(paren_no_hyphen.lower())
        variants.add(paren_hyphen_as_space)
        variants.add(paren_hyphen_as_space.lower())

    # Base part of name (before parentheses, " as ", or ",")
    # First handle base name without parenthetical content
    if "(" in nutrient_name:
        base_before_paren = nutrient_name.split("(")[0].strip()
        variants.add(base_before_paren)
        variants.add(base_before_paren.lower())
    
    # Then handle " as " or ","
    base_name = nutrient_name.split(" as ")[0].split(",")[0].strip()
    if base_name != nutrient_name.strip():
        variants.add(base_name)
        variants.add(base_name.lower())
        base_no_hyphen = base_name.replace('-', '')
        base_hyphen_as_space = base_name.replace('-', ' ')
        variants.add(base_no_hyphen)
        variants.add(base_no_hyphen.lower())
        variants.add(base_hyphen_as_space)
        variants.add(base_hyphen_as_space.lower())
    
    # Add a variant with " B" changed to " B-" for vitamins e.g. Vitamin B6 -> Vitamin B-6
    # This is more specific, might be better than overly general rules
    if "vitamin b" in name_lower and not "vitamin b-" in name_lower:
        modified_name = nutrient_name.replace("Vitamin B", "Vitamin B-").replace("vitamin b", "vitamin b-") # handle capitalization
        variants.add(modified_name)
        variants.add(modified_name.lower())

    return list(d for d in variants if d) # Filter out empty strings just in case

# Refined find_nutrient function
def find_nutrient(nutrient_name_csv, processed_db_nutrients_cache):
    """
    Finds a nutrient by matching CSV name against a cache of processed DB nutrient names.
    Returns the Nutrient object or None.
    processed_db_nutrients_cache is a list of dicts:
        [{'id': nutrient_id, 'original_name': name, 'name_variants': [variant1, variant2...]} ...]
    """
    if nutrient_name_csv is None or not nutrient_name_csv:
        return None
        
    csv_name_variants = get_nutrient_name_variants(nutrient_name_csv)

    # Exact matches first
    for csv_var in csv_name_variants:
        for db_entry in processed_db_nutrients_cache:
            if csv_var in db_entry['name_variants']:
                # To return the actual Nutrient object, we'd need to fetch it by id
                # For now, assume the cache might store the object or just id.
                # Let's refine this to return the Nutrient object directly if cache stores it,
                # or make the main loop fetch it using the id.
                # For simplicity, let's assume processed_db_nutrients_cache stores Nutrient objects directly.
                # This is not what the EFSA script did; it stored IDs. 
                # Let's stick to the structure: cache contains dicts with 'id' and 'name_variants'.
                # The main handle method will fetch Nutrient.objects.get(id=...) 
                return db_entry # Return the dict containing id and original_name
    
    # Starts-with matches (less precise, use with caution or add length checks)
    for csv_var in csv_name_variants:
        # Avoid overly short csv_var for startswith if they are just "b6" etc.
        if len(csv_var) < 3 and csv_var.isalnum(): continue
        for db_entry in processed_db_nutrients_cache:
            for db_var in db_entry['name_variants']:
                if len(db_var) < 3 and db_var.isalnum(): continue # Avoid short db_vars too
                if csv_var.startswith(db_var) or db_var.startswith(csv_var):
                    return db_entry
    
    # Special handling for "Vitamin K " (trailing space in CSV)
    # This might be covered by general variant generation if spaces are handled right.
    # Let's ensure `strip()` is used on CSV names early.
    if nutrient_name_csv.strip().lower() == "vitamin k":
        for db_entry in processed_db_nutrients_cache:
            if "vitamin k1" in db_entry['name_variants'] or "phylloquinone" in db_entry['name_variants']:
                return db_entry

    # Specific handling for combined EPA/DHA from CSV
    # "Eicosapentaenoic acid, Docosahexaenoic acid (EPA, DHA)"
    # This is complex as it maps one CSV entry to potentially two DB nutrients.
    # The current script structure (one DRV per row) doesn't easily support this split.
    # For now, if this exact string needs to map to a *single* combined nutrient if it exists,
    # or we log it as not found/needs special handling. 
    # The FDC import likely created separate EPA and DHA nutrients.
    # This function is designed to return ONE nutrient or None.
    # We will rely on the general variant matching. If the DB has a nutrient named
    # something like "EPA and DHA", it might be caught.

    return None

class Command(BaseCommand):
    help = "Imports Dietary Reference Values (DRVs) from data/drv.csv into the DietaryReferenceValue model."

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help='Update existing DRV entries if found, otherwise skip.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate the import process without making database changes.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        update_existing = options['update_existing']
        dry_run = options['dry_run']

        csv_path = get_csv_path()
        self.stdout.write(self.style.SUCCESS(f"Starting DRV import from {csv_path}"))
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run mode: No database changes will be made."))

        # Pre-fetch all Nutrient objects
        # db_nutrients_cache = {n.name.lower(): n for n in Nutrient.objects.all()}
        # Storing them as a list of objects for more flexible matching
        all_db_nutrients = list(Nutrient.objects.all())

        # Prepare a cache of DB nutrient names and their variants for matching
        processed_db_nutrients_cache = []
        for n_obj in all_db_nutrients:
            processed_db_nutrients_cache.append({
                'id': n_obj.id,
                'original_name': n_obj.name,
                'obj': n_obj, # Store the object itself for direct use
                'name_variants': get_nutrient_name_variants(n_obj.name)
            })

        created_count = 0
        updated_count = 0
        skipped_count = 0
        not_found_nutrient_count = 0
        error_count = 0
        
        processed_nutrients_log = set()


        try:
            csv_path = get_csv_path()
            with open(csv_path, mode='r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                if not reader.fieldnames:
                    self.stderr.write(self.style.ERROR(f"CSV file {csv_path} is empty or has no header."))
                    return

                expected_headers = ['Category', 'Nutrient', 'Target population', 'Age', 'Gender', 'frequency', 'unit', 'AI', 'AR', 'PRI', 'RI', 'UL']
                if not all(header in reader.fieldnames for header in expected_headers):
                    self.stderr.write(self.style.ERROR(f"CSV file {csv_path} is missing expected headers. Found: {reader.fieldnames}. Expected: {expected_headers}"))
                    return

                for row_num, row in enumerate(reader, start=2): # start=2 for 1-based header + 1-based data
                    try:
                        csv_nutrient_name = row['Nutrient'].strip()
                        if not csv_nutrient_name:
                            self.stdout.write(self.style.WARNING(f"Skipping row {row_num}: Nutrient name is blank."))
                            skipped_count += 1
                            continue

                        # The find_nutrient now returns a dict like {'id': ..., 'obj': NutrientObject, ...} or None
                        matched_nutrient_info = find_nutrient(csv_nutrient_name, processed_db_nutrients_cache)

                        if not matched_nutrient_info:
                            if csv_nutrient_name not in processed_nutrients_log:
                                self.stdout.write(self.style.WARNING(f"Nutrient '{csv_nutrient_name}' from CSV not found in DB. Skipping associated DRV entries."))
                                processed_nutrients_log.add(csv_nutrient_name)
                            not_found_nutrient_count += 1
                            skipped_count +=1
                            continue
                        
                        nutrient_obj = matched_nutrient_info['obj'] # Get the actual Nutrient model instance
                        
                        # Map CSV Gender to model Gender choices
                        csv_gender = row['Gender'].strip()
                        model_gender = None
                        if csv_gender.lower() == 'male':
                            model_gender = Gender.MALE
                        elif csv_gender.lower() == 'female':
                            model_gender = Gender.FEMALE
                        elif csv_gender.lower() == 'both genders':
                            model_gender = None # Stored as NULL for 'Both'
                        else:
                            self.stdout.write(self.style.WARNING(f"Skipping row {row_num} for nutrient '{csv_nutrient_name}': Unknown gender '{csv_gender}'."))
                            skipped_count += 1
                            continue
                        
                        # Prepare data for DietaryReferenceValue model
                        drv_data = {
                            'source_data_category': row['Category'].strip(),
                            'target_population': row['Target population'].strip(),
                            'age_range_text': row['Age'].strip(),
                            'gender': model_gender,
                            'frequency': row['frequency'].strip(),
                            'value_unit': row['unit'].strip(),
                            'ai': parse_float_or_none(row.get('AI')),
                            'ar': parse_float_or_none(row.get('AR')),
                            'pri': parse_float_or_none(row.get('PRI')),
                            'ri': parse_float_or_none(row.get('RI')),
                            'ul': parse_float_or_none(row.get('UL')),
                        }

                        # Unique key for get_or_create / update_or_create
                        # Based on DietaryReferenceValue.Meta.unique_together
                        unique_key_fields = {
                            'nutrient': nutrient_obj,
                            'target_population': drv_data['target_population'],
                            'age_range_text': drv_data['age_range_text'],
                            'gender': drv_data['gender'],
                            'source_data_category': drv_data['source_data_category'],
                            'value_unit': drv_data['value_unit']
                        }

                        if dry_run:
                            # Simulate finding or creating
                            # Check if it would be an update or create
                            existing_drv = DietaryReferenceValue.objects.filter(**unique_key_fields).first()
                            if existing_drv:
                                # Check if any values would change
                                changed = False
                                for k, v in drv_data.items():
                                    # Compare with existing_drv attributes. Only check value fields.
                                    if k in ['ai', 'ar', 'pri', 'ri', 'ul']:
                                        # Handle cases where existing_drv might have None and v is a float, or vice-versa
                                        current_val = getattr(existing_drv, k)
                                        # Basic comparison; float precision might be an issue if values are extremely close but not identical.
                                        # For DRVs, exact float match should be fine unless they are calculated with high precision elsewhere.
                                        if current_val != v and not (pd.isna(current_val) and pd.isna(v)):
                                            changed = True
                                            break
                                
                                if changed and update_existing:
                                    self.stdout.write(f"[Dry Run] Would update DRV for {nutrient_obj.name} ({drv_data['target_population']}, {drv_data['age_range_text']}, {csv_gender})")
                                    updated_count += 1
                                elif existing_drv and not update_existing:
                                    skipped_count +=1
                                else: # no change or not updating
                                    pass 
                            else:
                                self.stdout.write(f"[Dry Run] Would create DRV for {nutrient_obj.name} ({drv_data['target_population']}, {drv_data['age_range_text']}, {csv_gender})")
                                created_count += 1
                            continue # End of dry run logic for this row

                        # Actual DB operation
                        drv_instance, created = DietaryReferenceValue.objects.get_or_create(
                            defaults=drv_data,
                            **unique_key_fields
                        )

                        if created:
                            created_count += 1
                            self.stdout.write(self.style.SUCCESS(f"Created DRV for {nutrient_obj.name} ({drv_data['target_population']}, {drv_data['age_range_text']}, {csv_gender})"))
                        else: # Existing instance found
                            if update_existing:
                                # Check if any values need updating
                                has_changed = False
                                for field, value in drv_data.items():
                                     # Only update AI, AR, PRI, RI, UL
                                    if field in ['ai', 'ar', 'pri', 'ri', 'ul']:
                                        current_value = getattr(drv_instance, field)
                                        # Check for actual change, handling None vs float
                                        if current_value != value and not (pd.isna(current_value) and pd.isna(value)):
                                            setattr(drv_instance, field, value)
                                            has_changed = True
                                
                                if has_changed:
                                    drv_instance.save()
                                    updated_count += 1
                                    self.stdout.write(self.style.SUCCESS(f"Updated DRV for {nutrient_obj.name} ({drv_data['target_population']}, {drv_data['age_range_text']}, {csv_gender})"))
                                else:
                                    skipped_count += 1 # No changes needed or not updating
                            else: # not update_existing and instance exists
                                skipped_count += 1
                                self.stdout.write(f"Skipped existing DRV for {nutrient_obj.name} (use --update-existing to update)")
                    
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"Error processing row {row_num} for nutrient '{csv_nutrient_name if 'csv_nutrient_name' in locals() else 'Unknown'}': {e}"))
                        error_count += 1
                        # Decide if you want to continue or stop on error
                        # For now, continue processing other rows
        
        except FileNotFoundError:
            csv_path = get_csv_path()
            self.stderr.write(self.style.ERROR(f"Error: CSV file not found at {csv_path}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"An unexpected error occurred: {e}"))
            return
        
        if dry_run:
            self.stdout.write(self.style.WARNING("Dry run complete."))
        
        self.stdout.write(self.style.SUCCESS("DRV import process finished."))
        self.stdout.write(f"Successfully created entries: {created_count}")
        self.stdout.write(f"Successfully updated entries: {updated_count}")
        self.stdout.write(f"Skipped entries (exists, no update flag, blank nutrient, unknown gender, or no change): {skipped_count}")
        self.stdout.write(f"Nutrients from CSV not found in DB (leading to skipped DRV entries): {not_found_nutrient_count}")
        self.stdout.write(f"Errors during processing: {error_count}")

        if not_found_nutrient_count > 0:
             self.stdout.write(self.style.WARNING("Some nutrients in the CSV could not be matched to the database. Review the warnings above."))
        if error_count > 0:
            self.stdout.write(self.style.ERROR("Some rows could not be processed due to errors. Review the messages above."))

        if dry_run and (created_count > 0 or updated_count > 0):
            self.stdout.write(self.style.WARNING("To apply these changes, run the command again without --dry-run."))
        elif not dry_run and (created_count == 0 and updated_count == 0 and error_count == 0 and not_found_nutrient_count == 0):
             self.stdout.write(self.style.SUCCESS("No new data to import or update based on current settings.")) 