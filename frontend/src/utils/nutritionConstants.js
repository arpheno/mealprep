// frontend/src/utils/nutritionConstants.js

// Nutrient calculation constants
export const KJ_TO_KCAL_CONVERSION_FACTOR = 0.239006;
export const KCAL_PER_GRAM_CARB = 4;
export const KCAL_PER_GRAM_PROTEIN = 4;
export const KCAL_PER_GRAM_FAT = 9;

// Target %E ranges
export const TARGET_E_PERCENT_CARB = { min: 45, max: 60 };
export const TARGET_E_PERCENT_FAT = { min: 20, max: 35 };
export const TARGET_E_PERCENT_PROTEIN = { min: 10, max: 35 };

// Nutrient Identifiers (using FDC numbers for robustness)
export const FDC_NUM_ENERGY = "208";
export const FDC_NUM_PROTEIN = "203";
export const FDC_NUM_FAT = "204"; // Total lipid (fat)
export const FDC_NUM_CARB = "205"; // Carbohydrate, by difference

export const MACRO_FDC_NUMBERS = [FDC_NUM_PROTEIN, FDC_NUM_FAT, FDC_NUM_CARB]; 