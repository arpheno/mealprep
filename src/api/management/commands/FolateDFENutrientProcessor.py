from api.management.commands.BaseNutrientProcessor import BaseNutrientProcessor
from api.models import Nutrient


class FolateDFENutrientProcessor(BaseNutrientProcessor):
    TARGET_FDC_ID = 1190
    TARGET_FDC_NUMBER = "435"
    TARGET_NAME = "Folate, DFE"
    TARGET_UNIT = "µg" # Standard unit for Folate DFE, FDC uses μg or UG

    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_fdc_number = str(nutrient_data_from_fdc.get('number'))
        original_name = nutrient_data_from_fdc.get('name')
        # original_unit_name = nutrient_data_from_fdc.get('unitName') # Used in factory detection

        current_amount = float(original_amount_from_fdc)
        created_nutrient = False
        updated_nutrient = False
        skipped = False

        defaults = {
            'name': self.TARGET_NAME,
            'unit': self.TARGET_UNIT,
            'fdc_nutrient_number': self.TARGET_FDC_NUMBER,
        }

        try:
            nutrient_obj, created = Nutrient.objects.update_or_create(
                fdc_nutrient_id=self.TARGET_FDC_ID,
                defaults=defaults
            )
            created_nutrient = created
        except Exception as e:
            self.stderr.write(f'Error processing Folate, DFE nutrient (target ID {self.TARGET_FDC_ID}) from source {original_fdc_id} (\"{original_name}\"): {e}')
            return None, None, False, False, True

        if created:
            self.stdout.write(
                f'Created/Mapped Folate, DFE Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Original FDC ID: {original_fdc_id})'
            )
        elif self.update_existing:
            needs_save = False
            if nutrient_obj.name != defaults['name']:
                nutrient_obj.name = defaults['name']; needs_save = True
            if nutrient_obj.unit != defaults['unit']:
                nutrient_obj.unit = defaults['unit']; needs_save = True
            if nutrient_obj.fdc_nutrient_number != defaults['fdc_nutrient_number']:
                nutrient_obj.fdc_nutrient_number = defaults['fdc_nutrient_number']; needs_save = True

            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(
                    f'Updated Folate, DFE Nutrient to canonical: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Source FDC ID: {original_fdc_id})'
                )

        if original_fdc_id != self.TARGET_FDC_ID:
            self.stdout.write(f'Mapped Folate, DFE variant (ID: {original_fdc_id}, Name: "{original_name}", Num: {original_fdc_number}) to target (ID: {self.TARGET_FDC_ID})')

        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped