import { getGuessedFdcNumber } from './FdcNumberGuesser.js';

/**
 * @typedef {object} ScaledNutrientContribution
 * @property {string} nutrient_name
 * @property {string} nutrient_unit
 * @property {number} scaled_amount
 * @property {string|null} [fdc_nutrient_number]
 * @property {number|null} [fdc_id]
 */

/**
 * @typedef {object} ProcessedNutrientContribution
 * @property {string} pureNutrientName
 * @property {string} unitForDisplay
 * @property {number} amountToStore
 * @property {string|null} fdcNumForData
 * @property {string} nutrientKey
 * @property {number} originalAmount
 * @property {string} originalUnit
 * @property {number|null} fdcIdForData
 */

/**
 * @typedef {object} NutrientConstants
 * @property {number} KJ_TO_KCAL_CONVERSION_FACTOR
 * @property {string} FDC_NUM_ENERGY // Changed to string to match usage
 * @property {string} FDC_NUM_PROTEIN // Changed to string
 * @property {string} FDC_NUM_FAT // Changed to string
 * @property {string} FDC_NUM_CARB // Changed to string
 */

class NutritionalCalculator {
  /**
   * @param {object} [options={}]
   * @param {NutrientConstants} [options.nutrientConstants]
   * @param {function(...any):void} [options.logger=console.log]
   */
  constructor(options = {}) {
    this.nutrientConstants = options.nutrientConstants || {
      KJ_TO_KCAL_CONVERSION_FACTOR: 0.239006, 
      FDC_NUM_ENERGY: '208',   
      FDC_NUM_PROTEIN: '203', 
      FDC_NUM_FAT: '204',     
      FDC_NUM_CARB: '205',     
    };
    this.logger = options.logger || console.log; 
    this.logger('[NutritionalCalculator] initialized with constants:', this.nutrientConstants);
  }

  /**
   * Processes a single nutrient contribution, standardizing units (especially energy)
   * and determining its FDC number and display key.
   *
   * @param {ScaledNutrientContribution} contribution - The raw nutrient contribution from an ingredient usage.
   * @returns {ProcessedNutrientContribution} The processed nutrient data.
   */
  processNutrientContribution(contribution) {
    this.logger('[NutritionalCalculator] processNutrientContribution - input:', JSON.parse(JSON.stringify(contribution)));

    const pureNutrientName = contribution.nutrient_name.trim();
    const originalUnit = contribution.nutrient_unit;
    const originalAmount = contribution.scaled_amount || 0;

    let fdcNumForData = contribution.fdc_nutrient_number || null;
    if (!fdcNumForData) {
      fdcNumForData = getGuessedFdcNumber(pureNutrientName, this.nutrientConstants, this.logger);
    }

    const fdcIdForData = contribution.fdc_id || null;

    const standardizedAmount = originalAmount;
    const standardizedUnit = originalUnit;

    

    let displayKeyName = pureNutrientName;
    if (String(fdcNumForData) === String(this.nutrientConstants.FDC_NUM_FAT) && pureNutrientName.toLowerCase().includes("total lipid (fat)")) {
      displayKeyName = "Total lipid";
      this.logger(`[NutritionalCalculator] Standardized displayKeyName for ${pureNutrientName} to '${displayKeyName}'`);
    }
    const nutrientKey = `${displayKeyName} (${standardizedUnit})`;

    const result = {
      pureNutrientName,
      unitForDisplay: standardizedUnit,
      amountToStore: standardizedAmount,
      fdcNumForData,
      nutrientKey,
      originalAmount,
      originalUnit,
      fdcIdForData,
    };
    this.logger('[NutritionalCalculator] processNutrientContribution - output:', JSON.parse(JSON.stringify(result)));
    return result;
  }
}

export default NutritionalCalculator; 