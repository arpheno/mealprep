from api.management.commands.BaseNutrientProcessor import BaseNutrientProcessor
from api.management.commands.KCAL_PER_KJ import KCAL_PER_KJ
from api.models import Nutrient


class EnergyNutrientProcessor(BaseNutrientProcessor):
    TARGET_FDC_ID = 1008
    TARGET_FDC_NUMBER = "208"
    TARGET_NAME = "Energy"
    TARGET_UNIT = "kcal"

    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        original_nutrient_name = nutrient_data_from_fdc.get('name')
        original_unit_name = nutrient_data_from_fdc.get('unitName')
        current_amount = float(original_amount_from_fdc)
        created_nutrient = False
        updated_nutrient = False
        skipped = False

        if original_unit_name.lower() == "kj":
            current_amount = original_amount_from_fdc * KCAL_PER_KJ
            self.stdout.write(f'Converted Energy ({original_nutrient_name}) for "{food_item_description}": {original_amount_from_fdc} kJ -> {current_amount:.2f} kcal')
        elif original_unit_name.lower() == "kcal":
            pass # Amount is already in kcal
        else:
            self.stdout.write(self.stdout.style.WARNING(
                f'Energy variant ({original_nutrient_name}) for "{food_item_description}" has an unsupported unit: {original_unit_name}. Amount {original_amount_from_fdc} not converted. Skipping link.'
            ))
            return None, None, False, False, True # Skipped

        nutrient_obj, created = Nutrient.objects.get_or_create(
            name=self.TARGET_NAME,
            defaults={
                'unit': self.TARGET_UNIT,
                'fdc_nutrient_id': self.TARGET_FDC_ID,
                'fdc_nutrient_number': self.TARGET_FDC_NUMBER,
            }
        )
        created_nutrient = created
        if created:
            self.stdout.write(
                f'Created canonical Nutrient: "{nutrient_obj.name}" (Unit: {nutrient_obj.unit}, FDC ID: {nutrient_obj.fdc_nutrient_id})'
            )
        else: # Check if update is needed for the found canonical energy nutrient
            needs_save = False
            if nutrient_obj.unit != self.TARGET_UNIT:
                nutrient_obj.unit = self.TARGET_UNIT; needs_save = True
            if nutrient_obj.fdc_nutrient_id != self.TARGET_FDC_ID: # Should ideally not happen if name is unique key
                nutrient_obj.fdc_nutrient_id = self.TARGET_FDC_ID; needs_save = True
            if nutrient_obj.fdc_nutrient_number != self.TARGET_FDC_NUMBER:
                nutrient_obj.fdc_nutrient_number = self.TARGET_FDC_NUMBER; needs_save = True

            if needs_save:
                nutrient_obj.save()
                updated_nutrient = True
                self.stdout.write(
                    f'Updated canonical Nutrient: "{nutrient_obj.name}" to ensure (Unit: {nutrient_obj.unit}, FDC ID: {nutrient_obj.fdc_nutrient_id})'
                )
        return nutrient_obj, current_amount, created_nutrient, updated_nutrient, skipped