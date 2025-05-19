import AbstractCompositeFoodItem from './AbstractCompositeFoodItem.js';
import Meal from './Meal.js';

/**
 * @typedef {import('../utils/NutritionalCalculator/NutritionalCalculator.js').NutritionalCalculator} NutritionalCalculator
 */

/**
 * Represents a meal plan, which is a collection of meals.
 */
class MealPlan extends AbstractCompositeFoodItem {
  /**
   * @param {string} name - The name of the meal plan (e.g., "John Doe's Weekly Plan").
   * @param {Array<Meal>} meals - An array of Meal objects.
   * @param {NutritionalCalculator} nutritionalCalculator - An instance of NutritionalCalculator.
   */
  constructor(name, meals, nutritionalCalculator) {
    if (!meals.every(item => item instanceof Meal)) {
      throw new Error('All items in a MealPlan must be instances of Meal.');
    }
    super(name, meals, nutritionalCalculator);
  }

  /**
   * Adds a meal to the meal plan.
   * @param {Meal} meal - The meal to add.
   */
  addMeal(meal) {
    if (!(meal instanceof Meal)) {
      throw new Error('Item must be an instance of Meal.');
    }
    this.items.push(meal);
    this.logger(`[MealPlan] Added meal ${meal.name} to ${this.name}`);
  }
}

export default MealPlan; 