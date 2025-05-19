import AbstractCompositeFoodItem from './AbstractCompositeFoodItem.js';
import Recipe from './Recipe.js';
import IngredientUsage from './IngredientUsage.js';

/**
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').NutritionalCalculator} NutritionalCalculator
 */

/**
 * Represents a meal, which can be composed of multiple recipes and/or individual ingredient usages.
 */
class Meal extends AbstractCompositeFoodItem {
  /**
   * @param {string} name - The name of the meal (e.g., "Lunch", "Post-Workout Snack").
   * @param {Array<Recipe | IngredientUsage>} items - An array of Recipe or IngredientUsage objects.
   * @param {NutritionalCalculator} nutritionalCalculator - An instance of NutritionalCalculator.
   */
  constructor(name, items, nutritionalCalculator) {
    if (!items.every(item => item instanceof Recipe || item instanceof IngredientUsage)) {
      throw new Error('All items in a Meal must be instances of Recipe or IngredientUsage.');
    }
    super(name, items, nutritionalCalculator);
  }

  /**
   * Adds an item (Recipe or IngredientUsage) to the meal.
   * @param {Recipe | IngredientUsage} item - The item to add.
   */
  addItem(item) {
    if (!(item instanceof Recipe || item instanceof IngredientUsage)) {
      throw new Error('Item must be an instance of Recipe or IngredientUsage.');
    }
    this.items.push(item);
    this.logger(`[Meal] Added item ${item.name} to ${this.name}`);
  }
}

export default Meal; 