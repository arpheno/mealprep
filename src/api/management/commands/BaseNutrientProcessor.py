# --- Nutrient Processor Classes ---

import abc


class BaseNutrientProcessor(abc.ABC):
    """
    Abstract base class for nutrient processors.
    Each processor handles the logic for a specific type of nutrient or a default case.
    """
    def __init__(self, command_stdout, command_stderr, update_existing_flag):
        self.stdout = command_stdout
        self.stderr = command_stderr
        self.update_existing = update_existing_flag

    @abc.abstractmethod
    def process(self, nutrient_data_from_fdc, food_item_description, original_amount_from_fdc):
        """
        Processes the given nutrient data.

        Args:
            nutrient_data_from_fdc (dict): The nutrient block from FDC JSON (e.g., food_nutrient['nutrient']).
            food_item_description (str): Description of the food item for logging.
            original_amount_from_fdc (float): The original amount of the nutrient from FDC.

        Returns:
            tuple: (Nutrient_obj_or_None, final_amount_or_None, created_flag, updated_flag, skipped_flag)
                   - Nutrient_obj_or_None: The Django Nutrient model instance, or None if skipped.
                   - final_amount_or_None: The processed amount for the nutrient link, or None if skipped.
                   - created_flag (bool): True if a new Nutrient object was created.
                   - updated_flag (bool): True if an existing Nutrient object was updated.
                   - skipped_flag (bool): True if this nutrient was skipped (e.g., unsupported unit).
        """
        pass