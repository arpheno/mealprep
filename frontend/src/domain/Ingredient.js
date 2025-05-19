/**
 * @typedef {object} BaseNutrient
 * @property {string} nutrient_name - The common name of the nutrient (e.g., "Protein", "Energy").
 * @property {string} nutrient_unit - The unit of measurement (e.g., "g", "kcal").
 * @property {number} amount - The quantity of the nutrient per base amount of the ingredient.
 * @property {string|null} [fdc_nutrient_number] - The FDC ID for the nutrient, if available.
 */

/**
 * Represents a food ingredient and its base nutritional information.
 * The nutritional information is typically provided per a standard amount, like 100 grams.
 */
class Ingredient {
  /**
   * @param {string} id - A unique identifier for the ingredient (e.g., "chicken_breast_raw").
   * @param {string} name - The display name of the ingredient (e.g., "Chicken Breast, Raw").
   * @param {Array<BaseNutrient>} baseNutrients - Array of nutrient objects, defining nutrition per `baseAmount` of the ingredient.
   * @param {number} [baseAmount=100] - The amount for which `baseNutrients` are specified (e.g., 100).
   * @param {string} [baseUnit="g"] - The unit for `baseAmount` (e.g., "g", "ml").
   */
  constructor(id, name, baseNutrients, baseAmount = 100, baseUnit = "g") {
    if (!id || typeof id !== 'string') {
      throw new Error('Ingredient ID must be a non-empty string.');
    }
    if (!name || typeof name !== 'string') {
      throw new Error('Ingredient name must be a non-empty string.');
    }
    if (!Array.isArray(baseNutrients) || baseNutrients.some(n => typeof n.nutrient_name !== 'string' || typeof n.nutrient_unit !== 'string' || typeof n.amount !== 'number')) {
      throw new Error('baseNutrients must be an array of valid nutrient objects.');
    }
    if (typeof baseAmount !== 'number' || baseAmount <= 0) {
      throw new Error('baseAmount must be a positive number.');
    }
    if (typeof baseUnit !== 'string' || !baseUnit.trim()) {
      throw new Error('baseUnit must be a non-empty string.');
    }

    this.id = id;
    this.name = name;
    this.baseNutrients = baseNutrients; // Expected to be like [{ nutrient_name: 'Protein', nutrient_unit: 'g', amount: 20, fdc_nutrient_number: '203' }, ...]
    this.baseAmount = baseAmount;
    this.baseUnit = baseUnit; // Unit for the baseAmount, e.g., "g"
  }
}

export default Ingredient; 