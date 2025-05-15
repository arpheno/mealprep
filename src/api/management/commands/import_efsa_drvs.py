import pandas as pd
import re
from django.core.management.base import BaseCommand
from api.models import Nutrient
from django.db import transaction

# Define the path to the Excel file, relative to the project root or where manage.py is
EXCEL_FILE_PATH = "data/DRVs_All_populations.xlsx"

# Define the target population strings we are interested in for general adults
ADULT_TARGET_POPULATIONS = ["Adults"] # Could be expanded, e.g., ["Adults", "Premenopausal women", "Postmenopausal women"]

# Define the priority for RDA value columns
RDA_COLUMN_PRIORITY = ["PRI", "RI", "AI"]  # Population Reference Intake, Reference Intake, Adequate Intake

def parse_value_string(value_str):
    """
    Parses a string like '10.5 mg/day', 'NA ', 'ND' to extract the numeric part.
    Returns the numeric value as a float, or None if not parseable/applicable.
    Units are ignored for now.
    """
    if pd.isna(value_str) or not isinstance(value_str, str):
        return None

    value_str_cleaned = value_str.strip().upper()

    if value_str_cleaned in ["NA", "NA.", "ND", "-", ""]:
        return None

    # Regex to find the first number (integer or float) in the string
    # Handles cases like "(+) 1 g/day", "<0.5", "2,500" (with comma)
    # It will take the first number it finds.
    # Remove commas from numbers to allow float conversion
    value_str_cleaned = value_str_cleaned.replace(",", "")
    
    match = re.search(r"[+-]?\d*\.?\d+", value_str_cleaned)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return None
    return None

# Helper function to extract content from parentheses
def extract_parentheses_content(name_str):
    match = re.search(r'\((.*?)\)', name_str)
    if match:
        return match.group(1).strip()
    return None

class Command(BaseCommand):
    help = "Imports EFSA Dietary Reference Values (DRVs) from an Excel file into the Nutrient model."

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(f"Starting EFSA DRV import from {EXCEL_FILE_PATH}"))

        try:
            df = pd.read_excel(EXCEL_FILE_PATH, sheet_name="Sheet1")
            self.stdout.write(self.style.SUCCESS(f"Successfully read {len(df)} rows from Excel."))
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"Error: Excel file not found at {EXCEL_FILE_PATH}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading Excel file: {e}"))
            return

        updated_count = 0
        not_found_count = 0
        parse_error_count = 0
        
        # Normalize column names for easier access (e.g. lower case, replace space with underscore)
        # df.columns = [col.strip().lower().replace(" ", "_").replace("(", "").replace(")", "") for col in df.columns]
        # For now, assume column names are exact as per inspect_excel.py output

        # Pre-fetch all nutrient names from DB for more flexible local matching
        db_nutrients_cache = list(Nutrient.objects.all().values('id', 'name'))
        # Prepare them for matching: store original and normalized versions
        processed_db_nutrients = []
        for db_n in db_nutrients_cache:
            db_name_lower = db_n['name'].lower()
            processed_db_nutrients.append({
                'id': db_n['id'],
                'original_name': db_n['name'],
                'name_variants': list(dict.fromkeys([
                    db_name_lower,
                    db_name_lower.replace('-', ''),
                    db_name_lower.replace('-', ' ') # also try replacing hyphen with space
                ]))
            })

        with transaction.atomic():
            for index, row in df.iterrows():
                try:
                    target_population = str(row["Target population"]).strip()
                    nutrient_name_excel = str(row["Nutrient"]).strip()
                    gender = str(row["Gender"]).strip()

                    if not nutrient_name_excel:
                        continue # Skip if nutrient name is blank

                    if target_population in ADULT_TARGET_POPULATIONS:
                        nutrient_db_id = None # ID of the matched DB nutrient
                        
                        # --- Generate potential names from Excel data ---
                        excel_name_variants = set() # Use a set to auto-handle duplicates initially
                        
                        # 1. Original Excel name (and its lowercase)
                        excel_name_variants.add(nutrient_name_excel)
                        excel_name_variants.add(nutrient_name_excel.lower())
                        
                        # 2. Excel name with hyphens removed / replaced by space
                        excel_name_no_hyphen = nutrient_name_excel.replace('-', '')
                        excel_name_hyphen_as_space = nutrient_name_excel.replace('-', ' ')
                        excel_name_variants.add(excel_name_no_hyphen)
                        excel_name_variants.add(excel_name_no_hyphen.lower())
                        excel_name_variants.add(excel_name_hyphen_as_space)
                        excel_name_variants.add(excel_name_hyphen_as_space.lower())

                        # 3. Content within parentheses from Excel name
                        content_in_paren = extract_parentheses_content(nutrient_name_excel)
                        if content_in_paren:
                            excel_name_variants.add(content_in_paren)
                            excel_name_variants.add(content_in_paren.lower())
                            # Also no-hyphen/space version of parenthesis content
                            paren_no_hyphen = content_in_paren.replace('-', '')
                            paren_hyphen_as_space = content_in_paren.replace('-', ' ')
                            excel_name_variants.add(paren_no_hyphen)
                            excel_name_variants.add(paren_no_hyphen.lower())
                            excel_name_variants.add(paren_hyphen_as_space)
                            excel_name_variants.add(paren_hyphen_as_space.lower())

                        # 4. Handle "X as Y" or "X, Y" from Excel name (base part)
                        #    (Covers "X as Y" and simple "X, Y (details)" cases by taking the first part)
                        base_name_excel = nutrient_name_excel.split(" as ")[0].split(",")[0].strip()
                        if base_name_excel != nutrient_name_excel: # Add if different
                            excel_name_variants.add(base_name_excel)
                            excel_name_variants.add(base_name_excel.lower())
                            # Also no-hyphen/space version of base name
                            base_no_hyphen = base_name_excel.replace('-', '')
                            base_hyphen_as_space = base_name_excel.replace('-', ' ')
                            excel_name_variants.add(base_no_hyphen)
                            excel_name_variants.add(base_no_hyphen.lower())
                            excel_name_variants.add(base_hyphen_as_space)
                            excel_name_variants.add(base_hyphen_as_space.lower())
                        
                        # Convert set to list to maintain an order if desired, though set iteration is fine
                        final_excel_variants = list(excel_name_variants)

                        # --- Attempt to match against cached & processed DB nutrient names ---
                        # Priority:
                        # 1. Exact match of any Excel variant with any DB variant.
                        # 2. Starts-with match (Excel variant starts with a DB variant, or DB variant starts with Excel variant)
                        
                        # Exact matches
                        found_match = False
                        for excel_var in final_excel_variants:
                            for db_entry in processed_db_nutrients:
                                for db_var in db_entry['name_variants']:
                                    if excel_var == db_var: # Exact match (case handled by lowercasing earlier)
                                        nutrient_db_id = db_entry['id']
                                        found_match = True
                                        break
                                if found_match: break
                            if found_match: break
                        
                        # Starts-with matches if no exact match
                        if not found_match:
                            for excel_var in final_excel_variants:
                                # Avoid overly short excel variants for startswith if they are just "b6" etc.
                                if len(excel_var) < 3 and excel_var.isalnum(): continue

                                for db_entry in processed_db_nutrients:
                                    for db_var in db_entry['name_variants']:
                                        if len(db_var) < 3 and db_var.isalnum(): continue # Avoid short db vars too

                                        if excel_var.startswith(db_var) or db_var.startswith(excel_var):
                                            nutrient_db_id = db_entry['id']
                                            found_match = True
                                            break
                                    if found_match: break
                                if found_match: break

                        if nutrient_db_id:
                            nutrient = Nutrient.objects.get(id=nutrient_db_id)
                            rda_value_to_use = None
                            ul_value_excel = row["UL"] # Tolerable Upper Intake Level
                            
                            # Find the best RDA value based on priority
                            for col_name in RDA_COLUMN_PRIORITY:
                                if col_name in row and pd.notna(row[col_name]):
                                    parsed_rda = parse_value_string(str(row[col_name]))
                                    if parsed_rda is not None:
                                        rda_value_to_use = parsed_rda
                                        break # Found a usable RDA value
                            
                            parsed_ul = parse_value_string(str(ul_value_excel))

                            changed = False
                            if gender == "Male" or gender == "Both genders":
                                if rda_value_to_use is not None and nutrient.default_rda_male != rda_value_to_use:
                                    nutrient.default_rda_male = rda_value_to_use
                                    changed = True
                            
                            if gender == "Female" or gender == "Both genders":
                                if rda_value_to_use is not None and nutrient.default_rda_female != rda_value_to_use:
                                    nutrient.default_rda_female = rda_value_to_use
                                    changed = True

                            if parsed_ul is not None and nutrient.upper_limit != parsed_ul:
                                nutrient.upper_limit = parsed_ul
                                changed = True
                            
                            if changed:
                                nutrient.save()
                                updated_count += 1
                                self.stdout.write(self.style.SUCCESS(f"Updated DRVs for: {nutrient.name} (Excel: {nutrient_name_excel}, Gender: {gender})"))
                            elif rda_value_to_use is None and parsed_ul is None:
                                # Only count as parse error if we expected to find values for this adult row
                                # but couldn't parse any relevant RDA or UL.
                                parse_error_count +=1
                                self.stdout.write(self.style.WARNING(f"Could not parse RDA or UL for: {nutrient_name_excel} (Gender: {gender})"))

                        else: # Nutrient not found in DB after all attempts
                            not_found_count += 1
                            self.stdout.write(self.style.WARNING(f"Nutrient not found in DB: {nutrient_name_excel}"))
                            continue # Skip to next row if nutrient not matched

                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error processing row {index} ({nutrient_name_excel if 'nutrient_name_excel' in locals() else 'Unknown'}): {e}"))
                    # Optionally, re-raise or handle more gracefully
                    # continue 

        self.stdout.write(self.style.SUCCESS(f"EFSA DRV import finished."))
        self.stdout.write(f"Successfully updated nutrients: {updated_count}")
        self.stdout.write(f"Nutrients from Excel not found in DB: {not_found_count}")
        self.stdout.write(f"Entries for adults where RDA/UL values were unparseable or missing: {parse_error_count}") 