import Ingredient from './Ingredient.js';

/**
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').ScaledNutrientContribution} ScaledNutrientContribution
 */

/**
 * Represents an ingredient used in a specific quantity within a recipe or meal.
 * It calculates the scaled nutrient contributions based on its quantity and the base nutritional data of the ingredient.
 */
class IngredientUsage {
  /**
   * @param {Ingredient} ingredient - The ingredient being used.
   * @param {number} amount - The quantity of the ingredient used.
   * @param {string} unit - The unit for the quantity (e.g., "g", "ml", "piece").
   */
  constructor(ingredient, amount, unit) {
    if (!(ingredient instanceof Ingredient)) {
      throw new Error('Invalid ingredient provided to IngredientUsage.');
    }
    if (typeof amount !== 'number' || amount < 0) { // Amount can be 0
      throw new Error('Amount must be a non-negative number.');
    }
    if (typeof unit !== 'string' || !unit.trim()) {
      throw new Error('Unit must be a non-empty string.');
    }

    this.ingredient = ingredient;
    this.amount = amount;
    this.unit = unit;
  }

  /**
   * Calculates the scaled nutrient contributions for this specific usage of the ingredient.
   * Assumes for now that `this.unit` is compatible with `this.ingredient.baseUnit` for direct scaling (e.g., both are weight units like 'g').
   * More complex unit conversions (e.g., volume to weight via density, or pieces to weight) are not handled here.
   * @returns {Array<ScaledNutrientContribution>} An array of nutrient contributions, scaled to the amount of this ingredient usage.
   */
  getScaledNutrientContributions() {
    // Basic scaling: if ingredient is 100g and usage is 50g, factor is 0.5.
    // This requires units to be compatible. For simplicity, we assume this for now.
    // If this.unit is different from this.ingredient.baseUnit but they are convertible (e.g. kg vs g), a conversion step would be needed here.
    // For now, we assume they are the same or directly proportional for scaling.
    if (this.unit.toLowerCase() !== this.ingredient.baseUnit.toLowerCase()) {
      // This is a simplification. Real-world applications need robust unit conversion.
      // For instance, converting 'kg' to 'g' before scaling if baseUnit is 'g'.
      // Or handling pieces if the ingredient has a weight per piece.
      console.warn(`[IngredientUsage] Unit mismatch for ingredient "${this.ingredient.name}": usage unit "${this.unit}" vs base unit "${this.ingredient.baseUnit}". Assuming direct scalability. This may lead to incorrect calculations if units are not compatible (e.g. grams vs milliliters without density).`);
    }

    const scalingFactor = this.amount / this.ingredient.baseAmount;
    if (this.amount === 0) return []; // No contribution if amount is zero

    return this.ingredient.baseNutrients.map(nutrient => ({
      nutrient_name: nutrient.nutrient_name,
      nutrient_unit: nutrient.nutrient_unit, // The unit of the nutrient itself (e.g., protein in 'g')
      scaled_amount: nutrient.amount * scalingFactor,
      fdc_nutrient_number: nutrient.fdc_nutrient_number || null,
    }));
  }
}

export default IngredientUsage; 