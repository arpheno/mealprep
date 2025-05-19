import IngredientUsage from './IngredientUsage.js';
// The NutritionalCalculator will be used for processing individual nutrient contributions.
// We need to import its type definitions for JSDoc and the class itself for instantiation or injection.
/**
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').NutritionalCalculator} NutritionalCalculator
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').ScaledNutrientContribution} ScaledNutrientContribution
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').ProcessedNutrientContribution} ProcessedNutrientContribution
 */

/**
 * @typedef {object} NutrientSummary
 * @property {string} pureNutrientName
 * @property {string} unitForDisplay
 * @property {number} totalAmount
 * @property {string|null} fdcNumForData
 */

/**
 * Base class for food items that are composed of other food items (e.g., ingredients, recipes).
 * Manages a list of items and provides a mechanism to calculate total nutrients.
 */
class AbstractCompositeFoodItem {
  /**
   * @param {string} name - The name of this composite food item (e.g., "Chicken Salad Recipe", "Daily Meal Plan").
   * @param {Array<IngredientUsage | AbstractCompositeFoodItem>} items - The constituent items.
   * @param {NutritionalCalculator} nutritionalCalculator - An instance of NutritionalCalculator for processing nutrients.
   */
  constructor(name, items, nutritionalCalculator) {
    if (typeof name !== 'string' || !name.trim()) {
      throw new Error('Composite food item name must be a non-empty string.');
    }
    if (!Array.isArray(items)) {
      throw new Error('Items must be an array.');
    }
    if (!nutritionalCalculator || typeof nutritionalCalculator.processNutrientContribution !== 'function') {
      throw new Error('A valid NutritionalCalculator instance must be provided.');
    }

    this.name = name;
    this.items = items; // Can be IngredientUsage or other AbstractCompositeFoodItem instances
    this.nutritionalCalculator = nutritionalCalculator;
    this.logger = nutritionalCalculator.logger || console.log; // Use logger from calculator or default
  }

  /**
   * Retrieves all processed nutrient contributions from all constituent items.
   * @returns {Array<ProcessedNutrientContribution>} A flat list of all processed nutrient contributions.
   */
  getAllProcessedNutrientContributions() {
    this.logger(`[${this.constructor.name}] getAllProcessedNutrientContributions for: ${this.name}`);
    /** @type {Array<ProcessedNutrientContribution>} */
    const allProcessedNutrients = [];

    this.items.forEach(item => {
      if (item instanceof IngredientUsage) {
        const scaledContributions = item.getScaledNutrientContributions();
        scaledContributions.forEach(scaledContribution => {
          try {
            const processed = this.nutritionalCalculator.processNutrientContribution(scaledContribution);
            allProcessedNutrients.push(processed);
          } catch (error) {
            this.logger(`[${this.constructor.name}] Error processing nutrient contribution for ingredient ${item.ingredient.name}:`, error, scaledContribution);
            // Decide how to handle: throw, skip, log? For now, log and skip.
          }
        });
      } else if (item instanceof AbstractCompositeFoodItem) {
        // Recursively get contributions from sub-composites
        allProcessedNutrients.push(...item.getAllProcessedNutrientContributions());
      } else {
        this.logger(`[${this.constructor.name}] Unknown item type in ${this.name}:`, item);
        // Potentially throw an error or handle differently
      }
    });
    return allProcessedNutrients;
  }

  /**
   * Calculates the total nutritional summary for this composite item.
   * It aggregates all processed nutrient contributions from its constituent items.
   * @returns {Map<string, NutrientSummary>} A map where keys are nutrientKeys (e.g., "Protein (g)")
   *                                       and values are objects containing the total amount and unit.
   */
  getNutritionalSummary() {
    this.logger(`[${this.constructor.name}] getNutritionalSummary for: ${this.name}`);
    const allProcessedNutrients = this.getAllProcessedNutrientContributions();
    
    /** @type {Map<string, NutrientSummary>} */
    const summary = new Map();

    allProcessedNutrients.forEach(processedNutrient => {
      const key = processedNutrient.nutrientKey;
      if (summary.has(key)) {
        const existing = summary.get(key);
        existing.totalAmount += processedNutrient.amountToStore;
      } else {
        summary.set(key, {
          pureNutrientName: processedNutrient.pureNutrientName,
          unitForDisplay: processedNutrient.unitForDisplay,
          totalAmount: processedNutrient.amountToStore,
          fdcNumForData: processedNutrient.fdcNumForData,
        });
      }
    });

    this.logger(`[${this.constructor.name}] Nutritional summary for ${this.name}:`, summary);
    return summary;
  }

  /**
   * Gathers all unique ingredients used within this composite food item and its sub-items.
   * @returns {Map<string, {ingredient: Ingredient, totalAmount: number, unit: string}>} A map where keys are ingredient IDs.
   */
  getAggregatedIngredients() {
    this.logger(`[${this.constructor.name}] getAggregatedIngredients for: ${this.name}`);
    const aggregated = new Map();

    function processItem(item) {
      if (item instanceof IngredientUsage) {
        const ingredientId = item.ingredient.id;
        if (aggregated.has(ingredientId)) {
          const existing = aggregated.get(ingredientId);
          // This basic aggregation assumes compatible units. 
          // A more robust solution would standardize units before summing.
          if (existing.unit.toLowerCase() === item.unit.toLowerCase()) {
            existing.totalAmount += item.amount;
          } else {
            // If units differ and no conversion logic, store separately or log warning
            // For simplicity, creating a combined key if units differ for the same ingredient ID
            const complexKey = `${ingredientId}_${item.unit}`;
            if (aggregated.has(complexKey)) {
                 aggregated.get(complexKey).totalAmount += item.amount;
            } else {
                 aggregated.set(complexKey, {
                    ingredient: item.ingredient,
                    totalAmount: item.amount,
                    unit: item.unit
                });
            }
             console.warn(`[${this.constructor.name}] Ingredient "${item.ingredient.name}" (${ingredientId}) has mixed units ("${existing.unit}", "${item.unit}") without conversion. Amounts may not be correctly summed.`);
          }
        } else {
          aggregated.set(ingredientId, {
            ingredient: item.ingredient,
            totalAmount: item.amount,
            unit: item.unit,
          });
        }
      } else if (item instanceof AbstractCompositeFoodItem) {
        item.items.forEach(processItem); // Recursively process sub-items
      }
    }

    this.items.forEach(processItem);
    this.logger(`[${this.constructor.name}] Aggregated ingredients for ${this.name}:`, aggregated);
    return aggregated;
  }
}

export default AbstractCompositeFoodItem; 