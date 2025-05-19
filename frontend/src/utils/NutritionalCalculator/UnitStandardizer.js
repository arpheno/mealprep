/**
 * @typedef {import('./NutritionalCalculator.js').NutrientConstants} NutrientConstants
 */

/**
 * @typedef {object} StandardizationResult
 * @property {number} amount
 * @property {string} unit
 */

/**
 * @callback UnitStandardizationStrategy
 * @param {string} originalUnit
 * @param {number} originalAmount
 * @param {NutrientConstants} nutrientConstants
 * @param {function(...any):void} logger - Logger function.
 * @returns {StandardizationResult|null} Null if no standardization applied by this strategy.
 */

/** 
 * Strategy for standardizing energy units from kJ to kcal.
 * @type {UnitStandardizationStrategy} 
 */
const standardizeEnergyToKcal = (originalUnit, originalAmount, nutrientConstants, logger) => {
  if (originalUnit.toLowerCase() === 'kj') {
    const amountInKcal = originalAmount * nutrientConstants.KJ_TO_KCAL_CONVERSION_FACTOR;
    logger(`[UnitStandardizer] Converted Energy from kJ to kcal. Amount: ${originalAmount} -> ${amountInKcal}`);
    return { amount: amountInKcal, unit: 'kcal' };
  }
  return null;
};

/**
 * Strategy for standardizing Iodine units to µg.
 * @type {UnitStandardizationStrategy}
 */
const standardizeIodineToUg = (originalUnit, originalAmount, _nutrientConstants, logger) => {
  const unitLower = originalUnit.toLowerCase();
  if (unitLower === 'mg') {
    const amountInUg = originalAmount * 1000;
    logger(`[UnitStandardizer] Converted Iodine from mg to µg. Amount: ${originalAmount} -> ${amountInUg}`);
    return { amount: amountInUg, unit: 'µg' };
  }
  if (unitLower === 'g') {
    const amountInUg = originalAmount * 1000000;
    logger(`[UnitStandardizer] Converted Iodine from g to µg. Amount: ${originalAmount} -> ${amountInUg}`);
    return { amount: amountInUg, unit: 'µg' };
  }
  if (unitLower === 'mcg') { // Handle mcg as equivalent or to be converted
    logger(`[UnitStandardizer] Normalized Iodine unit from mcg to µg. Amount: ${originalAmount}`);
    return { amount: originalAmount, unit: 'µg' };
  }
  if (unitLower === 'µg') { // Already in µg
    return { amount: originalAmount, unit: 'µg' };
  }
  return null;
};

/**
 * A map of nutrient names (lowercase) to their standardization strategies.
 * @type {Object.<string, UnitStandardizationStrategy[]>}
 */
const unitStandardizationByNameStrategyMap = {
  'iodine': [standardizeIodineToUg],
  // Future: Add other nutrients like 'iron', 'vitamin d', etc.
  // 'iron': [standardizeIronToMg], // Example
};

/**
 * Applies unit standardization strategies based on the nutrient's FDC number or name.
 * @param {string} pureNutrientName - The pure name of the nutrient (e.g., "Iodine").
 * @param {string|null} fdcNumForData - The FDC number of the nutrient.
 * @param {string} originalUnit - The original unit of the nutrient.
 * @param {number} originalAmount - The original amount of the nutrient.
 * @param {NutrientConstants} nutrientConstants - Nutrient constants, including conversion factors.
 * @param {function(...any):void} logger - Logger function.
 * @returns {StandardizationResult} The standardized amount and unit, or original if no strategy applied.
 */
export function getStandardizedUnitAndAmount(pureNutrientName, fdcNumForData, originalUnit, originalAmount, nutrientConstants, logger) {
  // 1. FDC Number based strategy (currently specific to Energy)
  if (String(fdcNumForData) === String(nutrientConstants.FDC_NUM_ENERGY)) {
    // Using standardizeEnergyToKcal directly for now as it was the only one in the map
    const energyResult = standardizeEnergyToKcal(originalUnit, originalAmount, nutrientConstants, logger);
    if (energyResult) {
      logger(`[UnitStandardizer] Applied energy standardization for FDC ${fdcNumForData}`);
      return energyResult;
    }
  }

  // 2. Name-based strategy
  const nameLower = pureNutrientName.toLowerCase();
  const nameStrategies = unitStandardizationByNameStrategyMap[nameLower];
  if (nameStrategies) {
    for (const strategy of nameStrategies) {
      const result = strategy(originalUnit, originalAmount, nutrientConstants, logger);
      if (result) {
        logger(`[UnitStandardizer] Applied strategy ${strategy.name} for nutrient name "${pureNutrientName}"`);
        return result;
      }
    }
  }
  
  logger(`[UnitStandardizer] No specific unit standardization applied for nutrient "${pureNutrientName}" (FDC ${fdcNumForData}), unit ${originalUnit}. Returning original.`);
  return { amount: originalAmount, unit: originalUnit };
} 