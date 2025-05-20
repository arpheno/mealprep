from api.management.commands.BaseNutrientProcessor import BaseNutrientProcessor
from api.models import Nutrient


class DefaultNutrientProcessor(BaseNutrientProcessor):
    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_name = nutrient_data_from_fdc.get('name')
        original_unit_name = nutrient_data_from_fdc.get('unitName')
        original_fdc_number = str(nutrient_data_from_fdc.get('number'))
        current_amount = float(original_amount_from_fdc) # No conversion for default
        created_nutrient = False
        updated_nutrient = False
        skipped = False

        defaults = {
            'name': original_name,
            'unit': original_unit_name,
            'fdc_nutrient_number': original_fdc_number,
        }
        try:
            nutrient_obj, created = Nutrient.objects.update_or_create(
                fdc_nutrient_id=original_fdc_id,
                defaults=defaults
            )
            created_nutrient = created
        except Exception as e:

            self.stderr.write(f'Error processing nutrient {original_fdc_id}{defaults} ("{original_name}"): {e}')
            return None, None, False, False, True # Skipped

        if created:
            self.stdout.write(f'Created Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id}')
        elif self.update_existing:
            needs_save = False
            # Compare all fields from defaults
            if nutrient_obj.name != defaults['name']:
                nutrient_obj.name = defaults['name']; needs_save = True
            if nutrient_obj.unit != defaults['unit']:
                nutrient_obj.unit = defaults['unit']; needs_save = True
            if nutrient_obj.fdc_nutrient_number != defaults['fdc_nutrient_number']:
                nutrient_obj.fdc_nutrient_number = defaults['fdc_nutrient_number']; needs_save = True

            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(f'Updated Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id}')

        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped