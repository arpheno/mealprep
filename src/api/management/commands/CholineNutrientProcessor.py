from api.management.commands.BaseNutrientProcessor import BaseNutrientProcessor
from api.models import Nutrient


class CholineNutrientProcessor(BaseNutrientProcessor):
    TARGET_FDC_ID = 1180
    TARGET_FDC_NUMBER = "421"
    TARGET_NAME = "Choline, total"
    TARGET_UNIT = "mg"

    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_fdc_number = str(nutrient_data_from_fdc.get('number'))
        # original_unit_name = nutrient_data_from_fdc.get('unitName') # Assumed 'mg' for Choline variants
        current_amount = float(original_amount_from_fdc) # No unit conversion needed for Choline (mg to mg)
        created_nutrient = False
        updated_nutrient = False
        skipped = False # Choline doesn't have skippable unit conditions here

        defaults = {
            'name': self.TARGET_NAME,
            'unit': self.TARGET_UNIT,
            'fdc_nutrient_number': self.TARGET_FDC_NUMBER,
        }
        nutrient_obj, created = Nutrient.objects.update_or_create(
            fdc_nutrient_id=self.TARGET_FDC_ID, # Use target ID for lookup and creation
            defaults=defaults
        )
        created_nutrient = created

        if created:
            self.stdout.write(
                f'Created/Mapped Choline Nutrient: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Original FDC ID: {original_fdc_id})'
            )
        elif self.update_existing: # Check if update is needed for the found canonical Choline nutrient
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
                    f'Updated Choline Nutrient to canonical: "{nutrient_obj.name}" ({nutrient_obj.unit}), FDC ID: {nutrient_obj.fdc_nutrient_id} (Source FDC ID: {original_fdc_id})'
                )

        if original_fdc_id != self.TARGET_FDC_ID:
            self.stdout.write(f'Mapped Choline variant (ID: {original_fdc_id}, Num: {original_fdc_number}) to target Choline (ID: {self.TARGET_FDC_ID})')

        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped