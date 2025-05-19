/**
 * @typedef {import('./NutritionalCalculator.js').NutrientConstants} NutrientConstants
 */

/**
 * @callback FdcNumberGuessingStrategy
 * @param {string} lowerCaseNutrientName
 * @param {NutrientConstants} nutrientConstants
 * @returns {string|null}
 */

/** @type {FdcNumberGuessingStrategy} */
const guessByProteinName = (lowerCaseNutrientName, nutrientConstants) => {
  if (lowerCaseNutrientName.includes('protein')) {
    return nutrientConstants.FDC_NUM_PROTEIN;
  }
  return null;
};

/** @type {FdcNumberGuessingStrategy} */
const guessByCarbName = (lowerCaseNutrientName, nutrientConstants) => {
  if (lowerCaseNutrientName.includes('carbohydrate')) {
    return nutrientConstants.FDC_NUM_CARB;
  }
  return null;
};

/** @type {FdcNumberGuessingStrategy} */
const guessByFatName = (lowerCaseNutrientName, nutrientConstants) => {
  if (lowerCaseNutrientName.includes('total lipid') || lowerCaseNutrientName.includes('fat')) {
    return nutrientConstants.FDC_NUM_FAT;
  }
  return null;
};

/** @type {FdcNumberGuessingStrategy} */
const guessByEnergyName = (lowerCaseNutrientName, nutrientConstants) => {
  if (lowerCaseNutrientName.includes('energy')) {
    return nutrientConstants.FDC_NUM_ENERGY;
  }
  return null;
};

export const fdcNumberGuessingStrategies = [
  guessByProteinName,
  guessByCarbName,
  guessByFatName,
  guessByEnergyName,
];

/**
 * Iterates through defined strategies to guess an FDC number for a nutrient.
 * @param {string} pureNutrientName - The trimmed name of the nutrient.
 * @param {NutrientConstants} nutrientConstants - The nutrient constants object.
 * @param {function(...any):void} logger - Logger function.
 * @returns {string|null} The guessed FDC number or null if no strategy matched.
 */
export function getGuessedFdcNumber(pureNutrientName, nutrientConstants, logger) {
  const nameLower = pureNutrientName.toLowerCase();
  for (const strategy of fdcNumberGuessingStrategies) {
    const guessedFdc = strategy(nameLower, nutrientConstants);
    if (guessedFdc) {
      logger(`[FdcNumberGuesser] Guessed FDC number for ${pureNutrientName} using ${strategy.name}: ${guessedFdc}`);
      return guessedFdc;
    }
  }
  logger(`[FdcNumberGuesser] Could not guess FDC number for ${pureNutrientName}`);
  return null;
} 