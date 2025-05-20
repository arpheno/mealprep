from api.management.commands.CholineNutrientProcessor import CholineNutrientProcessor
from api.management.commands.DefaultNutrientProcessor import DefaultNutrientProcessor
from api.management.commands.FolateDFENutrientProcessor import FolateDFENutrientProcessor
from api.management.commands.EnergyNutrientProcessor import EnergyNutrientProcessor


class NutrientProcessorFactory:
    def __init__(self, command_stdout, command_stderr, update_existing_flag):
        self.stdout = command_stdout
        self.stderr = command_stderr
        self.update_existing = update_existing_flag

        # Energy Constants
        self.TARGET_ENERGY_FDC_ID = 1008
        self.FDC_ENERGY_VARIANTS_BY_NUMBER = {"208": self.TARGET_ENERGY_FDC_ID, "957": self.TARGET_ENERGY_FDC_ID}
        self.FDC_ENERGY_VARIANTS_BY_ID = {1008: self.TARGET_ENERGY_FDC_ID, 2047: self.TARGET_ENERGY_FDC_ID}

        # Choline Constants
        self.TARGET_CHOLINE_FDC_ID = 1180
        self.FDC_CHOLINE_VARIANTS_BY_NUMBER = {"437": self.TARGET_CHOLINE_FDC_ID}
        self.FDC_CHOLINE_VARIANTS_BY_ID = {1186: self.TARGET_CHOLINE_FDC_ID, 1180: self.TARGET_CHOLINE_FDC_ID}

        # Folate, DFE Constants
        self.TARGET_FOLATE_DFE_FDC_ID = 1190
        self.TARGET_FOLATE_DFE_NUMBER = "435"
        self.TARGET_FOLATE_DFE_NAME_LOWER = "folate, dfe"
        self.TARGET_FOLATE_DFE_UNITS_NORMALIZED = ["µg", "ug", "mcg"]
        self.FDC_FOLATE_DFE_VARIANTS_BY_NUMBER = {"435": self.TARGET_FOLATE_DFE_FDC_ID} # Number for ID 1190
        self.FDC_FOLATE_DFE_VARIANTS_BY_ID = {1190: self.TARGET_FOLATE_DFE_FDC_ID} # ID 1190 itself

    def get_processor(self, nutrient_data_from_fdc):
        original_fdc_id = nutrient_data_from_fdc.get('id')
        original_nutrient_name = nutrient_data_from_fdc.get('name', "").lower() # Ensure lowercase for name checks
        original_unit_name = nutrient_data_from_fdc.get('unitName', "").lower() # Ensure lowercase for unit checks
        original_nutrient_number = str(nutrient_data_from_fdc.get('number'))

        # Check for Energy
        if (original_nutrient_number in self.FDC_ENERGY_VARIANTS_BY_NUMBER or
            original_fdc_id in self.FDC_ENERGY_VARIANTS_BY_ID or
            (original_nutrient_name == "energy" and original_unit_name in ["kcal", "kj"])):
            return EnergyNutrientProcessor(self.stdout, self.stderr, self.update_existing)

        # Check for Choline
        if (original_nutrient_number in self.FDC_CHOLINE_VARIANTS_BY_NUMBER or
            original_fdc_id in self.FDC_CHOLINE_VARIANTS_BY_ID):
            return CholineNutrientProcessor(self.stdout, self.stderr, self.update_existing)

        # Check for Folate, DFE
        if (original_nutrient_number in self.FDC_FOLATE_DFE_VARIANTS_BY_NUMBER or
            original_fdc_id in self.FDC_FOLATE_DFE_VARIANTS_BY_ID or
            (original_nutrient_name == self.TARGET_FOLATE_DFE_NAME_LOWER and original_unit_name in self.TARGET_FOLATE_DFE_UNITS_NORMALIZED)):
            return FolateDFENutrientProcessor(self.stdout, self.stderr, self.update_existing)

        # Default processor
        return DefaultNutrientProcessor(self.stdout, self.stderr, self.update_existing)