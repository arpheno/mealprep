// frontend/src/utils/nutritionDisplayUtils.js
import {
    MACRO_FDC_NUMBERS,
    FDC_NUM_CARB,
    FDC_NUM_FAT,
    FDC_NUM_PROTEIN,
    TARGET_E_PERCENT_CARB,
    TARGET_E_PERCENT_FAT,
    TARGET_E_PERCENT_PROTEIN
} from './nutritionConstants.js';

export const formatDRV = (value) => {
    if (value === null || value === undefined) return '-';
    if (typeof value === 'number') return Number.isInteger(value) ? value : value.toFixed(2);
    return value;
};

export const getPlanNutrientBarStyle = (nutrientData, planDurationDays) => {
    // Note: _breakdownType parameter was removed as the 'overall' logic is now the standard.
    // If per-person needs different styling fundamentally, it would need re-evaluation.
    const totalForDuration = nutrientData.total;
    const dailyRda = nutrientData.rda;
    const dailyUl = nutrientData.ul;
    const planDuration = planDurationDays || 1;

    const rdaForDuration = dailyRda !== null ? dailyRda * planDuration : null;
    const ulForDuration = dailyUl !== null ? dailyUl * planDuration : null;

    let percentageOfRDA = 0;
    if (rdaForDuration && rdaForDuration > 0) {
        percentageOfRDA = (totalForDuration / rdaForDuration) * 100;
    }

    const MUTED_SATURATION = 45;
    const MUTED_LIGHTNESS = 65;
    const MUTED_ALPHA = 0.8;
    const MUTED_DANGER_SATURATION = 50;
    const MUTED_DANGER_LIGHTNESS = 60;

    const NEUTRAL_BACKGROUND_HSLA = `hsla(0, 0%, 25%, ${MUTED_ALPHA - 0.05})`;
    const NEUTRAL_TEXT_COLOR = 'var(--color-text-secondary, #b0b0b0)';

    // Special case: Nutrient has RDA but current intake is 0 (completely unsatisfied)
    if (totalForDuration === 0 && rdaForDuration && rdaForDuration > 0) {
        // Faint glassy red gradient to indicate missing essential nutrient
        const faintRedGradient = `linear-gradient(135deg, 
            hsla(0, 35%, 75%, 0.15) 0%, 
            hsla(0, 40%, 70%, 0.25) 30%, 
            hsla(0, 30%, 80%, 0.1) 70%, 
            transparent 100%)`;
        return {
            background: faintRedGradient,
            color: NEUTRAL_TEXT_COLOR,
            borderLeft: '3px solid hsla(0, 50%, 60%, 0.3)', // Subtle red accent border
            transition: 'all 0.3s ease'
        };
    }

    if (totalForDuration === 0) {
        return {
            background: NEUTRAL_BACKGROUND_HSLA,
            color: NEUTRAL_TEXT_COLOR
        };
    }

    let percentageOfUL = 0;
    if (ulForDuration && ulForDuration > 0) {
        percentageOfUL = (totalForDuration / ulForDuration) * 100;
    }

    let currentBackgroundColor = 'transparent';
    let visualProgressPercentage = 0;
    const neutralColorForBar = NEUTRAL_BACKGROUND_HSLA;

    const R_HUE = 0;
    const Y_HUE = 60;
    const G_HUE = 120;

    // Logic for 'overall' summary view (now used as standard)
    if (ulForDuration && ulForDuration > 0 && totalForDuration >= ulForDuration) {
        currentBackgroundColor = `hsla(${R_HUE}, ${MUTED_DANGER_SATURATION}%, ${MUTED_DANGER_LIGHTNESS}%, ${MUTED_ALPHA})`;
        visualProgressPercentage = 100;
    } else if (ulForDuration && ulForDuration > 0 && totalForDuration > 0.9 * ulForDuration) {
        const ratioInUlWarning = (percentageOfUL - 90) / 10;
        let hue;
        if (ratioInUlWarning < 0.5) {
            hue = Y_HUE - (Y_HUE * (ratioInUlWarning / 0.5));
        } else {
            hue = Y_HUE * (1 - ((ratioInUlWarning - 0.5) / 0.5));
        }
        hue = Math.max(R_HUE, Math.min(Y_HUE, hue));
        if (percentageOfUL >= 95) {
            const progressToRed = (percentageOfUL - 95) / 5;
            hue = Y_HUE - (Y_HUE * progressToRed);
        }
        currentBackgroundColor = `hsla(${Math.max(0, hue)}, ${MUTED_SATURATION}%, ${MUTED_LIGHTNESS}%, ${MUTED_ALPHA})`;
        visualProgressPercentage = Math.min(percentageOfRDA, 110);
    } else if (rdaForDuration && rdaForDuration > 0) {
        if (percentageOfRDA >= 100) {
            currentBackgroundColor = `hsla(${G_HUE}, ${MUTED_SATURATION}%, ${MUTED_LIGHTNESS}%, ${MUTED_ALPHA})`;
            visualProgressPercentage = 100;
        } else {
            let hue;
            if (percentageOfRDA < 50) {
                hue = R_HUE + (Y_HUE - R_HUE) * (percentageOfRDA / 50);
            } else {
                hue = Y_HUE + (G_HUE - Y_HUE) * ((percentageOfRDA - 50) / 50);
            }
            currentBackgroundColor = `hsla(${hue}, ${MUTED_SATURATION}%, ${MUTED_LIGHTNESS}%, ${MUTED_ALPHA})`;
            visualProgressPercentage = percentageOfRDA;
        }
    } else if (totalForDuration > 0) {
        currentBackgroundColor = neutralColorForBar;
        visualProgressPercentage = 15;
        if (ulForDuration && ulForDuration > 0 && totalForDuration >= ulForDuration) {
            currentBackgroundColor = `hsla(${R_HUE}, ${MUTED_DANGER_SATURATION}%, ${MUTED_DANGER_LIGHTNESS}%, ${MUTED_ALPHA})`;
            visualProgressPercentage = 100;
        }
    } else {
        currentBackgroundColor = 'transparent';
        visualProgressPercentage = 0;
    }

    visualProgressPercentage = Math.max(0, Math.min(visualProgressPercentage, 100));
    const barFillColor = currentBackgroundColor;
    let textColor = (barFillColor === neutralColorForBar || barFillColor === 'transparent') ? NEUTRAL_TEXT_COLOR : 'inherit';
    
    // The gradient for the person view bar was more complex, let's simplify or ensure consistency.
    // The 'overall' view used a simpler gradient. Let's use a consistent gradient that works well with HSLA.
    if (visualProgressPercentage > 0 && barFillColor !== 'transparent') {
         const gradientEndColor = `color-mix(in srgb, ${barFillColor} 20%, transparent)`;
         return {
             background: `linear-gradient(to right, ${barFillColor} ${visualProgressPercentage}%, ${gradientEndColor} ${Math.min(100, visualProgressPercentage + 10)}%, var(--color-input-bg) ${Math.min(100, visualProgressPercentage + 10)}%)`,
             transition: 'background 0.5s ease',
             color: textColor
         };
    } else {
         return {
             background: barFillColor, // Solid color if no progress or transparent
             transition: 'background 0.5s ease',
             color: textColor
         };
    }
};

export const getMacroStyle = (nutrientData) => {
    const MUTED_ALPHA = 0.8;
    const NEUTRAL_BACKGROUND_HSLA = `hsla(0, 0%, 25%, ${MUTED_ALPHA - 0.05})`;
    const NEUTRAL_TEXT_COLOR = 'var(--color-text-secondary, #b0b0b0)';

    if (!nutrientData) return { backgroundColor: NEUTRAL_BACKGROUND_HSLA, color: NEUTRAL_TEXT_COLOR};


    if (nutrientData.total === 0) {
        return {
            backgroundColor: NEUTRAL_BACKGROUND_HSLA,
            color: NEUTRAL_TEXT_COLOR
        };
    }

    if (nutrientData.percent_energy === undefined || nutrientData.percent_energy === null || !MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number)) {
      // If not a primary macro, or no %E data, give it a slightly distinct but neutral style
      // or fall back to a general plan style if that's preferred.
      // For now, let's use a very subtle neutral style for macros without %E to avoid errors.
      return { 
        backgroundColor: `hsla(0, 0%, 30%, ${MUTED_ALPHA - 0.1})`, // Slightly different neutral
        color: NEUTRAL_TEXT_COLOR 
      };
    }

    const percentE = nutrientData.percent_energy;
    let targetRange = null;
    let backgroundColor = NEUTRAL_BACKGROUND_HSLA; // Default to neutral if no specific range applies
    const textColor = 'var(--color-text-dark, #2c3e50)'; // Standard text for macro rows

    if (nutrientData.fdc_nutrient_number === FDC_NUM_CARB) targetRange = TARGET_E_PERCENT_CARB;
    else if (nutrientData.fdc_nutrient_number === FDC_NUM_FAT) targetRange = TARGET_E_PERCENT_FAT;
    else if (nutrientData.fdc_nutrient_number === FDC_NUM_PROTEIN) targetRange = TARGET_E_PERCENT_PROTEIN;

    if (targetRange) {
        const MUTED_SATURATION = 45; // Re-define locally or pass as param if preferred
        const MUTED_LIGHTNESS = 65;
        const MUTED_DANGER_SATURATION = 50;

        if (percentE < targetRange.min) {
            backgroundColor = `hsla(30, ${MUTED_SATURATION}%, ${MUTED_LIGHTNESS}%, ${MUTED_ALPHA})`; // Muted Orange/Yellow for low
        } else if (percentE > targetRange.max) {
            backgroundColor = `hsla(0, ${MUTED_DANGER_SATURATION - 5}%, ${MUTED_LIGHTNESS}%, ${MUTED_ALPHA})`; // Muted Red-ish for high
        } else {
            backgroundColor = `hsla(120, ${MUTED_SATURATION}%, ${MUTED_LIGHTNESS}%, ${MUTED_ALPHA})`; // Muted Green for good
        }
    }
    // Override text color for dark backgrounds of macros
    const effectiveTextColor = (backgroundColor.startsWith('hsla') && (parseInt(backgroundColor.split(',')[2]) < 50 || parseInt(backgroundColor.split(',')[3]) > 0.5 )) 
                           ? 'var(--color-text-light, #f8f9fa)' 
                           : textColor;

    return { backgroundColor, color: effectiveTextColor };
}; 