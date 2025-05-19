import NutritionalCalculator from './NutritionalCalculator';
import { vi } from 'vitest';

const mockNutrientConstants = {
  KJ_TO_KCAL_CONVERSION_FACTOR: 0.239006,
  FDC_NUM_ENERGY: '208', 
  FDC_NUM_PROTEIN: '203', 
  FDC_NUM_FAT: '204',     
  FDC_NUM_CARB: '205',     
};

describe('NutritionalCalculator', () => {
  let calculator;
  let mockLogger;

  beforeEach(() => {
    mockLogger = vi.fn();
    calculator = new NutritionalCalculator({ 
      nutrientConstants: mockNutrientConstants,
      logger: mockLogger
    });
  });

  describe('processNutrientContribution', () => {
    it('should process a simple nutrient without conversion', () => {
      const contribution = {
        nutrient_name: 'Protein ',
        nutrient_unit: 'g',
        scaled_amount: 50,
        fdc_nutrient_number: '203'
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Protein');
      expect(result.unitForDisplay).toBe('g');
      expect(result.amountToStore).toBe(50);
      expect(result.fdcNumForData).toBe('203');
      expect(result.nutrientKey).toBe('Protein (g)');
      // expect(mockLogger).toHaveBeenCalledWith('[NutritionalCalculator] processNutrientContribution - input:', contribution);
      // expect(mockLogger).toHaveBeenCalledWith('[NutritionalCalculator] processNutrientContribution - output:', result);
    });

    it('should convert energy from kJ to kcal', () => {
      const contribution = {
        nutrient_name: 'Energy',
        nutrient_unit: 'kJ',
        scaled_amount: 1000,
        fdc_nutrient_number: mockNutrientConstants.FDC_NUM_ENERGY 
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Energy');
      expect(result.unitForDisplay).toBe('kcal');
      expect(result.amountToStore).toBeCloseTo(1000 * mockNutrientConstants.KJ_TO_KCAL_CONVERSION_FACTOR);
      expect(result.fdcNumForData).toBe(mockNutrientConstants.FDC_NUM_ENERGY);
      expect(result.nutrientKey).toBe('Energy (kcal)');
      // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] Converted Energy from kJ to kcal. Amount: 1000 -> ${result.amountToStore}`);
      // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] Applied strategy standardizeEnergyToKcal for FDC ${mockNutrientConstants.FDC_NUM_ENERGY}`);
    });

    it('should handle energy already in kcal', () => {
      const contribution = {
        nutrient_name: 'Energy',
        nutrient_unit: 'kcal',
        scaled_amount: 250,
        fdc_nutrient_number: mockNutrientConstants.FDC_NUM_ENERGY
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.unitForDisplay).toBe('kcal');
      expect(result.amountToStore).toBe(250);
      expect(result.nutrientKey).toBe('Energy (kcal)');
      // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] No unit standardization applied for FDC ${mockNutrientConstants.FDC_NUM_ENERGY}, unit kcal. Returning original.`);
    });

    it('should guess FDC number for Protein if not provided', () => {
      const contribution = {
        nutrient_name: '  Crude Protein ',
        nutrient_unit: 'mg',
        scaled_amount: 5000,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.fdcNumForData).toBe(mockNutrientConstants.FDC_NUM_PROTEIN);
      expect(result.nutrientKey).toBe('Crude Protein (mg)'); 
      // expect(mockLogger).toHaveBeenCalledWith(`[FdcNumberGuesser] Guessed FDC number for Crude Protein using guessByProteinName: ${mockNutrientConstants.FDC_NUM_PROTEIN}`);
    });

    it('should guess FDC number for Carbohydrate if not provided', () => {
      const contribution = {
        nutrient_name: 'Total Carbohydrate, by difference',
        nutrient_unit: 'g',
        scaled_amount: 30,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.fdcNumForData).toBe(mockNutrientConstants.FDC_NUM_CARB);
      expect(result.nutrientKey).toBe('Total Carbohydrate, by difference (g)');
      // expect(mockLogger).toHaveBeenCalledWith(`[FdcNumberGuesser] Guessed FDC number for Total Carbohydrate, by difference using guessByCarbName: ${mockNutrientConstants.FDC_NUM_CARB}`);
    });

    it('should guess FDC number for Fat if not provided', () => {
      const contribution = {
        nutrient_name: 'Total lipid (fat)',
        nutrient_unit: 'g',
        scaled_amount: 15,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.fdcNumForData).toBe(mockNutrientConstants.FDC_NUM_FAT);
      expect(result.nutrientKey).toBe('Total lipid (g)'); 
      // expect(mockLogger).toHaveBeenCalledWith(`[FdcNumberGuesser] Guessed FDC number for Total lipid (fat) using guessByFatName: ${mockNutrientConstants.FDC_NUM_FAT}`);
      // expect(mockLogger).toHaveBeenCalledWith(`[NutritionalCalculator] Standardized displayKeyName for Total lipid (fat) to 'Total lipid'`);
    });
    
    it('should guess FDC number for Energy if not provided and convert if kJ', () => {
      const contribution = {
        nutrient_name: 'Energy expenditure',
        nutrient_unit: 'kJ',
        scaled_amount: 2000,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.fdcNumForData).toBe(mockNutrientConstants.FDC_NUM_ENERGY);
      expect(result.unitForDisplay).toBe('kcal');
      expect(result.amountToStore).toBeCloseTo(2000 * mockNutrientConstants.KJ_TO_KCAL_CONVERSION_FACTOR);
      expect(result.nutrientKey).toBe('Energy expenditure (kcal)');
      // expect(mockLogger).toHaveBeenCalledWith(`[FdcNumberGuesser] Guessed FDC number for Energy expenditure using guessByEnergyName: ${mockNutrientConstants.FDC_NUM_ENERGY}`);
      // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] Converted Energy from kJ to kcal. Amount: 2000 -> ${result.amountToStore}`);
      // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] Applied strategy standardizeEnergyToKcal for FDC ${mockNutrientConstants.FDC_NUM_ENERGY}`);
    });

    it('should return 0 for scaled_amount if it is null or undefined', () => {
      const contribution1 = { nutrient_name: 'Iron', nutrient_unit: 'mg', scaled_amount: null };
      const result1 = calculator.processNutrientContribution(contribution1);
      expect(result1.amountToStore).toBe(0);

      const contribution2 = { nutrient_name: 'Iron', nutrient_unit: 'mg', scaled_amount: undefined };
      const result2 = calculator.processNutrientContribution(contribution2);
      expect(result2.amountToStore).toBe(0);
    });

    it('should standardize displayKeyName for "Total lipid (fat)"', () => {
        const contribution = {
            nutrient_name: 'Total lipid (fat)',
            nutrient_unit: 'g',
            scaled_amount: 10,
            fdc_nutrient_number: mockNutrientConstants.FDC_NUM_FAT
        };
        const result = calculator.processNutrientContribution(contribution);
        expect(result.nutrientKey).toBe('Total lipid (g)');
        expect(result.pureNutrientName).toBe('Total lipid (fat)'); 
        // expect(mockLogger).toHaveBeenCalledWith(`[NutritionalCalculator] Standardized displayKeyName for Total lipid (fat) to 'Total lipid'`);
    });

    it('should not change displayKeyName for other fats', () => {
        const contribution = {
            nutrient_name: 'Saturated Fat',
            nutrient_unit: 'g',
            scaled_amount: 5,
            fdc_nutrient_number: '1258' 
        };
        const result = calculator.processNutrientContribution(contribution);
        expect(result.nutrientKey).toBe('Saturated Fat (g)');
        expect(result.pureNutrientName).toBe('Saturated Fat');
    });

  });

  // --- New Tests for Iodine Standardization ---
  describe('Iodine Standardization within processNutrientContribution', () => {
    it('should process Iodine in mcg without change', () => {
      const contribution = {
        nutrient_name: 'Iodine',
        nutrient_unit: 'mcg',
        scaled_amount: 150,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Iodine');
      expect(result.unitForDisplay).toBe('µg');
      expect(result.amountToStore).toBe(150);
      expect(result.nutrientKey).toBe('Iodine (µg)');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Applied strategy standardizeIodineToUg for nutrient name "Iodine"');
    });

    it('should convert Iodine from µg to mcg', () => {
      const contribution = {
        nutrient_name: 'Iodine',
        nutrient_unit: 'µg',
        scaled_amount: 120,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Iodine');
      expect(result.unitForDisplay).toBe('µg');
      expect(result.amountToStore).toBe(120);
      expect(result.nutrientKey).toBe('Iodine (µg)');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Normalized Iodine unit from µg to mcg. Amount: 120');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Applied strategy standardizeIodineToUg for nutrient name "Iodine"');
    });

    it('should convert Iodine from mg to mcg', () => {
      const contribution = {
        nutrient_name: 'Iodine',
        nutrient_unit: 'mg',
        scaled_amount: 0.15,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Iodine');
      expect(result.unitForDisplay).toBe('µg');
      expect(result.amountToStore).toBeCloseTo(150);
      expect(result.nutrientKey).toBe('Iodine (µg)');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Converted Iodine from mg to µg. Amount: 0.15 -> 150');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Applied strategy standardizeIodineToUg for nutrient name "Iodine"');
    });

    it('should convert Iodine from g to mcg', () => {
      const contribution = {
        nutrient_name: 'Iodine',
        nutrient_unit: 'g',
        scaled_amount: 0.00015,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Iodine');
      expect(result.unitForDisplay).toBe('µg');
      expect(result.amountToStore).toBeCloseTo(150);
      expect(result.nutrientKey).toBe('Iodine (µg)');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Converted Iodine from g to µg. Amount: 0.00015 -> 150');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Applied strategy standardizeIodineToUg for nutrient name "Iodine"');
    });

    it('should correctly process Iodine (mg to mcg) even if FDC number is not explicitly provided', () => {
      const contribution = { 
        nutrient_name: 'Iodine', 
        nutrient_unit: 'mg', 
        scaled_amount: 0.2 
        // fdc_nutrient_number is omitted to test name-based strategy lookup
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.unitForDisplay).toBe('µg');
      expect(result.amountToStore).toBeCloseTo(200);
      expect(result.nutrientKey).toBe('Iodine (µg)');
      // FdcNumberGuesser currently doesn't guess Iodine, so it would be null.
      // The UnitStandardizer should then pick it up by name.
      // expect(mockLogger).toHaveBeenCalledWith(`[FdcNumberGuesser] No FDC number found or guessed for nutrient: Iodine`);
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Converted Iodine from mg to µg. Amount: 0.2 -> 200');
      // expect(mockLogger).toHaveBeenCalledWith('[UnitStandardizer] Applied strategy standardizeIodineToUg for nutrient name "Iodine"');
    });
  });

  // --- Test for other nutrients and existing functionality ---
  describe('Other nutrients and existing functionality within processNutrientContribution', () => {
    it('should process Vitamin C in mg without change (no specific strategy)', () => {
      const contribution = {
        nutrient_name: 'Vitamin C',
        nutrient_unit: 'mg',
        scaled_amount: 60,
      };
      const result = calculator.processNutrientContribution(contribution);
      expect(result.pureNutrientName).toBe('Vitamin C');
      expect(result.unitForDisplay).toBe('mg');
      expect(result.amountToStore).toBe(60);
      expect(result.nutrientKey).toBe('Vitamin C (mg)');
      // expect(mockLogger).toHaveBeenCalledWith(`[FdcNumberGuesser] No FDC number found or guessed for nutrient: Vitamin C`);
      // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] No specific unit standardization applied for nutrient "Vitamin C" (FDC null), unit mg. Returning original.`);
    });

    it('should still convert energy from kJ to kcal (existing functionality)', () => {
        const contribution = {
            nutrient_name: 'Energy',
            nutrient_unit: 'kJ',
            scaled_amount: 500,
            fdc_nutrient_number: mockNutrientConstants.FDC_NUM_ENERGY
        };
        const result = calculator.processNutrientContribution(contribution);
        expect(result.unitForDisplay).toBe('kcal');
        expect(result.amountToStore).toBeCloseTo(500 * mockNutrientConstants.KJ_TO_KCAL_CONVERSION_FACTOR);
        // expect(mockLogger).toHaveBeenCalledWith('[NutritionalCalculator] processNutrientContribution - input:', contribution);
        // expect(mockLogger).toHaveBeenCalledWith('[NutritionalCalculator] processNutrientContribution - output:', result);
        // expect(mockLogger).toHaveBeenCalledWith(`[UnitStandardizer] Converted Energy from kJ to kcal. Amount: 500 -> ${result.amountToStore}`);
    });
  });
}); 