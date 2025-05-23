import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from api.models import Nutrient, NutrientAlias, NutrientCategory

class Command(BaseCommand):
    help = (
        'Imports authoritative nutrient list from a JSON file. ' 
        'Default behavior: Updates/creates nutrients from JSON and deletes any DB nutrients not in the JSON. ' 
        '--delete-all: Deletes ALL existing nutrients and aliases before import.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'json_file',
            type=str,
            nargs='?',
            default='data/authoritative_nutrients.json',
            help='Path to the authoritative nutrients JSON file (default: data/authoritative_nutrients.json)'
        )
        parser.add_argument(
            '--delete-all',
            action='store_true',
            help='Delete ALL existing Nutrient and NutrientAlias records before importing. Overrides default sync behavior.'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        json_file_path = options['json_file']
        delete_all = options['delete_all']

        self.stdout.write(self.style.SUCCESS(f'Starting authoritative nutrient import from {json_file_path}'))

        if delete_all:
            self.stdout.write(self.style.WARNING(
                'Deleting ALL existing NutrientAlias and Nutrient records as per --delete-all flag...'
            ))
            NutrientAlias.objects.all().delete()
            Nutrient.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('All existing nutrients and aliases deleted.'))

        try:
            with open(json_file_path, 'r') as f:
                authoritative_nutrients_data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'Authoritative nutrients JSON file "{json_file_path}" not found.')
        except json.JSONDecodeError:
            raise CommandError(f'Error decoding JSON from "{json_file_path}". Make sure it is valid JSON.')
        except Exception as e:
            raise CommandError(f'An unexpected error occurred while reading "{json_file_path}": {e}')

        if not isinstance(authoritative_nutrients_data, list):
            raise CommandError('Authoritative nutrients JSON should be a list of nutrient objects.')

        nutrients_created_count = 0
        nutrients_updated_count = 0
        aliases_created_count = 0
        processed_fdc_ids = set()

        for nutrient_data in authoritative_nutrients_data:
            try:
                fdc_id = nutrient_data.get('fdc_nutrient_id')
                if fdc_id is None: # Ensure fdc_id is present for processing and tracking
                    self.stderr.write(self.style.ERROR(
                        f"Skipping nutrient due to missing fdc_nutrient_id: {nutrient_data.get('name', 'Unnamed Nutrient')}"
                    ))
                    continue
                
                processed_fdc_ids.add(fdc_id) # Add to set of processed FDC IDs

                name = nutrient_data.get('name')
                unit = nutrient_data.get('unit')
                category_str = nutrient_data.get('category')
                is_essential = nutrient_data.get('is_essential', False)
                description = nutrient_data.get('description', '')
                source_notes = nutrient_data.get('source_notes', '')
                aliases_list = nutrient_data.get('aliases', [])

                if not name or not unit or not category_str: # fdc_id already checked
                    self.stderr.write(self.style.ERROR(
                        f"Skipping nutrient (FDC ID: {fdc_id}) due to missing name, unit, or category: {nutrient_data.get('name', 'Unnamed Nutrient')}"
                    ))
                    continue
                
                if not hasattr(NutrientCategory, str(category_str).upper()): # Ensure category_str is a string before upper()
                    
                    self.stderr.write(self.style.ERROR(
                        f"Skipping nutrient \"{name}\" (FDC ID: {fdc_id}): Invalid category ''{category_str}''. Must be one of {NutrientCategory.names}."
                    ))
                    continue
                category_enum_val = NutrientCategory[str(category_str).upper()]

                nutrient_defaults = {
                    'name': name,
                    'unit': unit,
                    'category': category_enum_val,
                    'is_essential': is_essential,
                    'description': description,
                    'source_notes': source_notes,
                }

                nutrient_obj, created = Nutrient.objects.update_or_create(
                    fdc_nutrient_id=fdc_id,
                    defaults=nutrient_defaults
                )

                if created:
                    nutrients_created_count += 1
                    self.stdout.write(f'Created Nutrient: "{nutrient_obj.name}" (FDC ID: {nutrient_obj.fdc_nutrient_id})')
                else:
                    nutrients_updated_count += 1
                    self.stdout.write(f'Updated Nutrient: "{nutrient_obj.name}" (FDC ID: {nutrient_obj.fdc_nutrient_id})')

                nutrient_obj.aliases.all().delete()
                current_nutrient_aliases_created = 0
                for alias_name in aliases_list:
                    if alias_name:
                        try:
                            _alias_obj, alias_created = NutrientAlias.objects.get_or_create(
                                name=alias_name,
                                nutrient=nutrient_obj
                            )
                            if alias_created:
                                aliases_created_count += 1
                                current_nutrient_aliases_created +=1
                        except Exception as alias_e:
                            self.stderr.write(self.style.ERROR(f'Error creating alias "{alias_name}" for nutrient "{name}" (FDC ID: {fdc_id}): {alias_e}'))
                if current_nutrient_aliases_created > 0:
                     self.stdout.write(f'  Added {current_nutrient_aliases_created} alias(es) for "{name}".')

            except KeyError as e:
                self.stderr.write(self.style.ERROR(f"Skipping nutrient due to missing key {e} in entry: {nutrient_data}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error processing nutrient entry {nutrient_data.get('name', '')}: {e}"))

        orphans_deleted_count = 0
        if not delete_all:
            # Delete nutrients from DB that are not in the processed_fdc_ids set
            # Important: Ensure fdc_nutrient_id cannot be null in the DB for this to work reliably without extra checks.
            # The model Nutrient.fdc_nutrient_id allows null=True, blank=True. This might lead to issues
            # if DB has nutrients with fdc_nutrient_id=NULL, as they won't be in processed_fdc_ids AND exclude won't catch them well.
            # For robust sync, fdc_nutrient_id should ideally be unique and non-null for authoritative entries.
            # Assuming fdc_nutrient_id in the DB are actual IDs or None.
            
            # We only want to delete nutrients that HAVE an FDC ID but that ID is not in our authoritative list.
            # Nutrients with fdc_nutrient_id=None in the DB are ignored by this orphan deletion logic.
            orphaned_nutrients = Nutrient.objects.filter(fdc_nutrient_id__isnull=False).exclude(fdc_nutrient_id__in=processed_fdc_ids)
            orphans_deleted_count = orphaned_nutrients.count()
            if orphans_deleted_count > 0:
                self.stdout.write(self.style.WARNING(
                    f'Deleting {orphans_deleted_count} orphaned nutrient(s) (and their aliases/links) from DB not present in the JSON file...'
                ))
                orphaned_nutrients.delete()
                self.stdout.write(self.style.SUCCESS(f'{orphans_deleted_count} orphaned nutrient(s) deleted.'))
            else:
                self.stdout.write(self.style.SUCCESS('No orphaned nutrients found in the DB to delete.'))

        self.stdout.write(self.style.SUCCESS(
            f'Authoritative nutrient import finished. \n'
            f'Nutrients: {nutrients_created_count} created, {nutrients_updated_count} updated. \n'
            f'Nutrient Aliases: {aliases_created_count} created. \n'
            f'Orphaned Nutrients Deleted: {orphans_deleted_count}.'
        )) 