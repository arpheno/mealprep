import AbstractCompositeFoodItem from './AbstractCompositeFoodItem.js';
import IngredientUsage from './IngredientUsage.js';

/**
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').NutritionalCalculator} NutritionalCalculator
 */

/**
 * Represents a recipe, which is a collection of ingredient usages.
 */
class Recipe extends AbstractCompositeFoodItem {
  /**
   * @param {string} name - The name of the recipe.
   * @param {Array<IngredientUsage>} ingredientUsages - An array of IngredientUsage objects.
   * @param {NutritionalCalculator} nutritionalCalculator - An instance of NutritionalCalculator.
   */
  constructor(name, ingredientUsages, nutritionalCalculator) {
    if (!ingredientUsages.every(item => item instanceof IngredientUsage)) {
      throw new Error('All items in a Recipe must be instances of IngredientUsage.');
    }
    super(name, ingredientUsages, nutritionalCalculator);
  }

  /**
   * Adds an ingredient usage to the recipe.
   * @param {IngredientUsage} ingredientUsage - The ingredient usage to add.
   */
  addIngredientUsage(ingredientUsage) {
    if (!(ingredientUsage instanceof IngredientUsage)) {
      throw new Error('Item must be an instance of IngredientUsage.');
    }
    this.items.push(ingredientUsage);
    this.logger(`[Recipe] Added ingredient ${ingredientUsage.ingredient.name} to ${this.name}`);
  }
}

export default Recipe; 