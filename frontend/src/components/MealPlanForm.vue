<template>
  <!-- Show MealComponentForm if editingComponent is set -->
  <div v-if="editingComponent">
    <MealComponentForm 
      :component-data-to-edit="editingComponent" 
      @form-closed="handleComponentFormClose" 
      @component-saved="handleComponentFormClose" 
    />
  </div>

  <!-- Otherwise, show the main meal plan form -->
  <form v-else @submit.prevent="submitMealPlan" class="meal-plan-form">
    <PlanHeader 
      :all-person-profiles="allPersonProfiles"
      :selected-people="selectedPeopleObjects"
      @add-person="handlePersonAdded"
      @remove-person="handlePersonRemoved"
    />

    <PlanDetailsForm 
      v-model:name="planData.name"
      v-model:notes="planData.notes"
      v-model:durationDays="planData.duration_days"
      v-model:servingsPerDayPerPerson="planData.servings_per_day_per_person"
    />
    
    <hr />

    <MealComponentSearch 
      :all-meal-components="allMealComponents"
      :is-loading="isLoadingMealComponents"
      :fetch-error="mealComponentsError"
      @component-selected="addComponentToPlan"
    />

    <AddedMealComponentsDisplay 
      :added-meal-components="addedMealComponents"
      :selected-people-in-plan="selectedPeopleObjects"
      @remove-component="removeComponentFromPlan"
      @update:assignment="handleComponentAssignmentUpdate"
      @edit-component="handleEditComponent"
    />
    
    <hr />
    
    <!-- Nutritional Breakdown Section - NOW A COMPONENT -->
    <NutritionalBreakdown
      :breakdownData="livePlanNutritionalBreakdown"
      :activeView="activeBreakdownView"
      @update:activeView="newVal => activeBreakdownView = newVal"
      :selectedPeople="selectedPeopleObjects"
      :planDurationDays="planData.duration_days"
    />

    <div class="form-actions">
      <button type="submit" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : 'Save Meal Plan' }}
      </button>
    </div>

     <div v-if="error" class="error-message">
        <p>Error: {{ error }}</p>
    </div>
  </form>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';
import {
    KJ_TO_KCAL_CONVERSION_FACTOR,
    KCAL_PER_GRAM_CARB,
    KCAL_PER_GRAM_PROTEIN,
    KCAL_PER_GRAM_FAT,
    FDC_NUM_ENERGY,
    FDC_NUM_PROTEIN,
    FDC_NUM_FAT,
    FDC_NUM_CARB,
    MACRO_FDC_NUMBERS
} from '../utils/nutritionConstants.js';
import NutritionalCalculator from '../utils/NutritionalCalculator/NutritionalCalculator.js'; // Import the new calculator
import NutritionalBreakdown from './NutritionalBreakdown.vue'; // Import the new component
import PlanHeader from './PlanHeader.vue'; // Import the new PlanHeader component
import PlanDetailsForm from './PlanDetailsForm.vue'; // Import the new PlanDetailsForm component
import MealComponentSearch from './MealComponentSearch.vue'; // Import the new MealComponentSearch component
import AddedMealComponentsDisplay from './AddedMealComponentsDisplay.vue'; // Import the new component
import MealComponentForm from './MealComponentForm.vue'; // Assuming this is your component form

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

// Instantiate the calculator
// Pass the required constants from nutritionConstants.js
const nutrientConstantsForCalculator = {
  KJ_TO_KCAL_CONVERSION_FACTOR,
  FDC_NUM_ENERGY,
  FDC_NUM_PROTEIN,
  FDC_NUM_FAT,
  FDC_NUM_CARB
};
const nutritionalCalculator = new NutritionalCalculator({
  nutrientConstants: nutrientConstantsForCalculator,
  logger: console.log // You can replace console.log with a more sophisticated logger if needed
});

const planData = ref({
  name: '',
  notes: '',
  duration_days: 7,
  servings_per_day_per_person: 1,
  target_people_ids: [],
  meal_component_ids: [],
  target_people_profiles: [],
  selected_person_profiles_in_form: [],
});

const allMealComponents = ref([]);
const allPersonProfiles = ref([]);

const addedMealComponents = ref([]);
const isSaving = ref(false);
const error = ref(null);
const isLoadingMealComponents = ref(false);
const mealComponentsError = ref(null);

const activeBreakdownView = ref('overall'); // 'overall' or a person_id
const editingComponent = ref(null); // Will hold the component being edited

onMounted(async () => {
  isLoadingMealComponents.value = true;
  mealComponentsError.value = null;
  try {
    const componentsResponse = await axios.get(`${API_BASE_URL}/mealcomponents/`);
    allMealComponents.value = componentsResponse.data.results || componentsResponse.data;
    console.log('Fetched all meal components:', allMealComponents.value);

    const profilesResponse = await axios.get(`${API_BASE_URL}/personprofiles/`);
    allPersonProfiles.value = profilesResponse.data.results || profilesResponse.data;
    console.log('Fetched all person profiles:', allPersonProfiles.value);

  } catch (err) {
    console.error('Error fetching initial data (components or profiles):', err);
    const errorMessage = 'Failed to load initial data. ' + (err.response?.data?.detail || err.message);
    error.value = errorMessage; // Set general form error
    mealComponentsError.value = 'Failed to load meal components.'; // Specific error for component search section
  } finally {
    isLoadingMealComponents.value = false;
  }
});

const selectedPeopleObjects = ref([]);

const handlePersonAdded = (personProfile) => {
  if (!personProfile || !personProfile.id) {
    console.error('[MealPlanForm] Invalid person profile to add:', personProfile);
    return;
  }
  if (!planData.value.target_people_ids.includes(personProfile.id)) {
    planData.value.target_people_ids.push(personProfile.id);
    // Ensure selectedPeopleObjects is also updated if it's not already there
    if (!selectedPeopleObjects.value.some(p => p.id === personProfile.id)) {
        const profileFromAll = allPersonProfiles.value.find(p => p.id === personProfile.id);
        if (profileFromAll) {
            selectedPeopleObjects.value.push(profileFromAll);
        } else {
            console.warn("[MealPlanForm] Added person not found in allPersonProfiles. This shouldn't happen.", personProfile);
            selectedPeopleObjects.value.push(personProfile); // Add what we received as a fallback
        }
    }
    console.log('[MealPlanForm] Updated selectedPeopleObjects after add:', JSON.parse(JSON.stringify(selectedPeopleObjects.value))); // Log here
     // Ensure new person is assigned to existing components if they were previously unassigned to anyone specific
    // OR if a global assignment strategy is desired upon adding a new person. Current logic assigns to all if selected.
    addedMealComponents.value.forEach(item => {
        if (!item.assigned_people_ids.includes(personProfile.id)) {
            // Optional: automatically assign new person to items. For now, let's keep it manual or based on component add logic.
            // item.assigned_people_ids.push(personProfile.id); 
        }
    });
  }
};

const handlePersonRemoved = (personProfile) => {
  if (!personProfile || !personProfile.id) {
    console.error('[MealPlanForm] Invalid person profile to remove:', personProfile);
    return;
  }
  planData.value.target_people_ids = planData.value.target_people_ids.filter(id => id !== personProfile.id);
  selectedPeopleObjects.value = selectedPeopleObjects.value.filter(p => p.id !== personProfile.id);
  console.log('[MealPlanForm] Updated selectedPeopleObjects after remove:', JSON.parse(JSON.stringify(selectedPeopleObjects.value))); // Log here

  // Also remove this person from any component assignments
  addedMealComponents.value.forEach(itemInPlan => {
    itemInPlan.assigned_people_ids = itemInPlan.assigned_people_ids.filter(id => id !== personProfile.id);
  });
};

const submitMealPlan = async () => {
  if (addedMealComponents.value.length === 0) {
    alert('Please add at least one meal component to the plan.');
    return;
  }
  isSaving.value = true;
  error.value = null;

  // Prepare plan_items_write from addedMealComponents
  const planItemsToWrite = addedMealComponents.value.map(item => ({
    meal_component_id: item.component.id,
    assigned_people_ids: item.assigned_people_ids
  }));

  const payload = {
    name: planData.value.name,
    notes: planData.value.notes,
    duration_days: planData.value.duration_days,
    servings_per_day_per_person: planData.value.servings_per_day_per_person,
    target_people_ids: planData.value.target_people_ids, // Changed from target_people_profiles for consistency if backend expects IDs for the M2M
    plan_items_write: planItemsToWrite // New field for backend
  };

  // Ensure target_people_ids is what the backend expects for the MealPlan.target_people_profiles M2M.
  // The MealPlanSerializer has `target_people_ids = PrimaryKeyRelatedField(source='target_people_profiles')`,
  // so sending `target_people_ids` directly should be correct.

  try {
    const response = await axios.post(`${API_BASE_URL}/mealplans/`, payload);
    console.log('Saved meal plan:', response.data);
    alert('Meal plan saved successfully!');
  } catch (err) {
    console.error('Error saving meal plan:', err.response ? err.response.data : err.message);
    error.value = 'Failed to save meal plan. ' + (err.response?.data ? JSON.stringify(err.response.data) : err.message);
  } finally {
    isSaving.value = false;
  }
};

const getHardcodedNutrientGroup = (nutrientName, fdcNumber) => {
    const nameLower = nutrientName.toLowerCase();

    // 1. Precise FDC Number checks - Prioritize Energy
    if (fdcNumber) {
        if (fdcNumber === FDC_NUM_ENERGY) { // Energy
            return 'Energy';
        }
        if (MACRO_FDC_NUMBERS.includes(fdcNumber)) { // Protein, Fat, Carb
            return 'Macronutrients';
        }
        // Note: FDC number for Fiber (e.g., "291") is not handled here by FDC number, 
        // but will be caught by name-based checks below if applicable.
    }

    // 2. Name-based checks for specific categories (Energy, Minerals, Vitamins)
    if (nameLower.includes('energy')) { // Catch energy by name if FDC# was missing
        return 'Energy';
    }

    if (nameLower.includes('calcium') || nameLower.includes('iron') || nameLower.includes('magnesium') ||
        nameLower.includes('phosphorus') || nameLower.includes('potassium') || nameLower.includes('sodium') ||
        nameLower.includes('zinc') || nameLower.includes('copper') || nameLower.includes('manganese') ||
        nameLower.includes('selenium') || nameLower.includes('fluoride') || nameLower.includes('iodine') || 
        nameLower.includes('chloride') || nameLower.includes('chromium') || nameLower.includes('molybdenum')) {
      return 'Minerals';
    }

    if (nameLower.includes('vitamin') || nameLower.includes('thiamin') || nameLower.includes('riboflavin') ||
        nameLower.includes('niacin') || nameLower.includes('folate') || nameLower.includes('choline') ||
        nameLower.includes('pantothenic') || nameLower.includes('biotin') || nameLower.includes('retinol') ||
        nameLower.includes('carotene') || nameLower.includes('cryptoxanthin') || nameLower.includes('lycopene') || 
        nameLower.includes('lutein') || nameLower.includes('tocopherol') || nameLower.includes('phylloquinone') || 
        nameLower.includes('menaquinone') || nameLower.includes('calciferol') || nameLower.includes('ergocalciferol') || 
        nameLower.includes('cholecalciferol') || nameLower.includes('cobalamin')) {
      return 'Vitamins';
    }

    // 3. Name-based checks for items that belong to "General & Other"
    // This includes Fiber explicitly.
    if (nameLower.includes('fiber') || 
        nameLower.includes('water') || 
        nameLower.includes('caffeine') || nameLower.includes('alcohol') || nameLower.includes('cholesterol') ||
        nameLower.includes('ash') || nameLower.includes('theobromine')) {
       return 'General & Other';
    }
    
    // 4. Default group for anything not categorized
    return 'General & Other';
};

const derivedPlanTargets = computed(() => {
  console.log('[MealPlanForm] Recalculating derivedPlanTargets. Selected People:', JSON.parse(JSON.stringify(selectedPeopleObjects.value)));
  const combinedTargets = {};
  const individualTargets = {};
  let hasAnyRdaOrUlOverall = false; // Tracks if any RDA or UL value is found across all people and nutrients
  const allNutrientKeysInPlan = new Set();

  // Step 1: Populate individualTargets and gather all nutrient keys
  selectedPeopleObjects.value.forEach(person => {
    if (person && person.id) {
      if (person.personalized_drvs && typeof person.personalized_drvs === 'object') {
        individualTargets[person.id] = JSON.parse(JSON.stringify(person.personalized_drvs));
        Object.keys(person.personalized_drvs).forEach(key => {
          allNutrientKeysInPlan.add(key);
        });
      } else {
        // If a person has no DRVs, initialize an empty object for them
        individualTargets[person.id] = {};
        console.warn(`[MealPlanForm] Person ${person.name} (ID: ${person.id}) has no personalized_drvs object or it's not an object.`);
      }
    } else {
        console.warn('[MealPlanForm] Encountered a person object without an ID in selectedPeopleObjects during DRV processing.');
    }
  });
  console.log('[MealPlanForm] All nutrient keys gathered from selected people:', Array.from(allNutrientKeysInPlan));
  console.log('[MealPlanForm] Initial individualTargets:', JSON.parse(JSON.stringify(individualTargets)));

  // Step 2: Build combinedTargets by iterating through all unique nutrient keys found
  allNutrientKeysInPlan.forEach(nutrientKey => {
    let rdaSum = 0;
    let ulMin = null;
    let unit = '';
    let fdc_nutrient_number = null;
    let nutrientPresentInAtLeastOnePerson = false;

    selectedPeopleObjects.value.forEach(person => {
      const personDrvs = individualTargets[person.id]; // Use the already populated individual targets
      if (personDrvs && personDrvs[nutrientKey]) {
        const drvEntry = personDrvs[nutrientKey];
        nutrientPresentInAtLeastOnePerson = true;

        if (drvEntry.rda !== null && drvEntry.rda !== undefined) {
          rdaSum += parseFloat(drvEntry.rda) || 0;
          hasAnyRdaOrUlOverall = true;
        }
        if (drvEntry.ul !== null && drvEntry.ul !== undefined) {
          const currentUl = parseFloat(drvEntry.ul);
          if (ulMin === null || currentUl < ulMin) {
            ulMin = currentUl;
          }
          hasAnyRdaOrUlOverall = true;
        }
        // Capture unit and FDC number from the first valid entry for this nutrient key
        if (!unit && drvEntry.unit) unit = drvEntry.unit;
        if (!fdc_nutrient_number && drvEntry.fdc_nutrient_number) fdc_nutrient_number = drvEntry.fdc_nutrient_number;
      }
    });

    if (nutrientPresentInAtLeastOnePerson) { // Only add to combined if at least one person had this nutrient DRV
      combinedTargets[nutrientKey] = {
        rda: rdaSum,
        ul: ulMin,
        unit: unit,
        fdc_nutrient_number: fdc_nutrient_number
      };
    }
  });
  console.log('[MealPlanForm] Constructed combinedTargets:', JSON.parse(JSON.stringify(combinedTargets)));

  // Step 3: Finalize combined_plan_targets - already filtered by nutrientPresentInAtLeastOnePerson
  // If no people are selected, or no DRVs were found at all, combinedTargets will be empty.
  const finalCombinedTargets = (selectedPeopleObjects.value.length > 0 && hasAnyRdaOrUlOverall) ? combinedTargets : {};

  const targetsResult = {
    combined_plan_targets: finalCombinedTargets,
    individual_person_targets: individualTargets,
    _debug_selected_people_count: selectedPeopleObjects.value.length,
    _debug_has_any_rda_ul_overall: hasAnyRdaOrUlOverall
  };
  console.log('[MealPlanForm] derivedPlanTargets CALCULATION RESULT:', JSON.parse(JSON.stringify(targetsResult)));
  return targetsResult;
});

const livePlanNutritionalBreakdown = computed(() => {
  console.log('[MealPlanForm] Initializing livePlanNutritionalBreakdown. Selected People:', JSON.parse(JSON.stringify(selectedPeopleObjects.value)), 'Added Components:', JSON.parse(JSON.stringify(addedMealComponents.value)));

  const result = {
    overallSummary: {
      'Energy': {},
      'Macronutrients': {},
      'Minerals': {},
      'Vitamins': {},
      'General & Other': {},
      'NoReferenceValues': {}
    },
    perPersonBreakdown: {}
  };

  result.perPersonBreakdown = {}; // Ensure it's initialized cleanly
  selectedPeopleObjects.value.forEach(person => {
    console.log(`[MealPlanForm] Initializing structure for person: ${person.name} (ID: ${person.id})`);
    result.perPersonBreakdown[person.id] = {
      personName: person.name,
      total_energy_kcal_for_person: 0,
      nutrientGroups: {
        'Energy': {},
        'Macronutrients': {},
        'Minerals': {},
        'Vitamins': {},
        'General & Other': {},
        'NoReferenceValues': {}
      }
    };
  });
  console.log('[MealPlanForm] Initialized perPersonBreakdown structure:', JSON.parse(JSON.stringify(result.perPersonBreakdown)));

  addedMealComponents.value.forEach((itemInPlan, itemIndex) => {
    console.log(`[MealPlanForm] Processing added component #${itemIndex}: ${itemInPlan.component.name}, Assigned to: ${JSON.stringify(itemInPlan.assigned_people_ids)}`);
    const component = itemInPlan.component;

    // Check if component and its ingredient usage set are available
    if (!component || !component.ingredientusage_set) {
        console.warn(`[MealPlanForm] Component ${component?.name || 'Unknown'} has no ingredientusage_set or component is null. Skipping.`);
        return;
    }
    if (component.ingredientusage_set.length === 0) {
        console.warn(`[MealPlanForm] Component ${component.name} has an empty ingredientusage_set. Skipping component for nutrient calculation.`);
        return;
    }

    const duration = planData.value.duration_days || 7;
    const servingsPerDayPerPerson = planData.value.servings_per_day_per_person || 1;
    let consumption_multiplier_per_person = 0;

    if (component.frequency === 'PER_BOX') consumption_multiplier_per_person = duration * servingsPerDayPerPerson;
    else if (component.frequency === 'DAILY') consumption_multiplier_per_person = duration;
    else if (component.frequency === 'WEEKLY') consumption_multiplier_per_person = duration / 7.0;
    else consumption_multiplier_per_person = 1; // Default, e.g. for ONE_TIME_CONSUMPTION or if frequency not set

    // Iterate over ingredient usages and their scaled nutrient contributions
    component.ingredientusage_set.forEach(usage => {
      if (!usage.scaled_nutrient_contributions) {
        console.warn(`[MealPlanForm] Ingredient usage ${usage.ingredient_name} in component ${component.name} has no scaled_nutrient_contributions. Skipping this usage.`);
        return;
      }

      usage.scaled_nutrient_contributions.forEach(contribution => {
        // contribution: { nutrient_name, nutrient_unit, scaled_amount, fdc_nutrient_number (optional) }
        // scaled_amount is the amount of the nutrient from this ingredient for ONE serving of the component.

        // *** USE THE NEW CALCULATOR ***
        const processedContribution = nutritionalCalculator.processNutrientContribution(contribution);
        const {
          pureNutrientName,
          unitForDisplay,
          amountToStore: baseAmountToStore, // Renamed to avoid conflict with amountToStore further down, this is pre-frequency scaling
          fdcNumForData,
          nutrientKey
        } = processedContribution;
        // *** END USE THE NEW CALCULATOR ***
        
        let nutrientAmountFromItemScaledByFreq = baseAmountToStore * consumption_multiplier_per_person;
        let amountToStore = nutrientAmountFromItemScaledByFreq; // This will be used for accumulation
        
        // The energy unit standardization is now handled by the calculator.
        // The fdcNumForData is also primarily determined by the calculator.
        // The nutrientKey is also generated by the calculator.

        // --- Overall Summary Calculation ---
        const overallPlanCombinedTargetData = derivedPlanTargets.value.combined_plan_targets || {};
        const overallPlanCombinedTarget = overallPlanCombinedTargetData[pureNutrientName] || overallPlanCombinedTargetData[`${pureNutrientName} (${unitForDisplay})`];
        
        const overallRdaFromPlanTarget = overallPlanCombinedTarget?.rda;
        const overallUlFromPlanTarget = overallPlanCombinedTarget?.ul;
        // Use FDC number from contribution if available, otherwise the one derived for overall target or guessed
        const fdcForOverallSummary = contribution.fdc_nutrient_number || (overallPlanCombinedTarget || {}).fdc_nutrient_number || fdcNumForData;

        let determinedOverallCategoryGroup = getHardcodedNutrientGroup(pureNutrientName, fdcForOverallSummary);
        const hasOverallReference = (overallRdaFromPlanTarget !== null && overallRdaFromPlanTarget !== undefined) ||
                                  (overallUlFromPlanTarget !== null && overallUlFromPlanTarget !== undefined);

        if (!hasOverallReference && determinedOverallCategoryGroup !== 'Energy' && determinedOverallCategoryGroup !== 'Macronutrients') {
          determinedOverallCategoryGroup = 'NoReferenceValues';
        }
        
        if (!result.overallSummary[determinedOverallCategoryGroup]) result.overallSummary[determinedOverallCategoryGroup] = {}; // Should be pre-initialized
        if (!result.overallSummary[determinedOverallCategoryGroup][nutrientKey]) {
          result.overallSummary[determinedOverallCategoryGroup][nutrientKey] = {
            total: 0, unit: unitForDisplay,
            rda: overallRdaFromPlanTarget,
            ul: overallUlFromPlanTarget,
            fdc_nutrient_number: fdcForOverallSummary,
            kcal_contribution: 0,
            percent_energy: null
          };
        }
        result.overallSummary[determinedOverallCategoryGroup][nutrientKey].total += amountToStore;

        if (MACRO_FDC_NUMBERS.includes(fdcForOverallSummary) && fdcForOverallSummary !== FDC_NUM_ENERGY) {
          let kcalPerGram = 0;
          if (fdcForOverallSummary === FDC_NUM_CARB) kcalPerGram = KCAL_PER_GRAM_CARB;
          else if (fdcForOverallSummary === FDC_NUM_PROTEIN) kcalPerGram = KCAL_PER_GRAM_PROTEIN;
          else if (fdcForOverallSummary === FDC_NUM_FAT) kcalPerGram = KCAL_PER_GRAM_FAT;
          result.overallSummary[determinedOverallCategoryGroup][nutrientKey].kcal_contribution += amountToStore * kcalPerGram;
        }

        // --- Per-Person Breakdown Calculation ---
        selectedPeopleObjects.value.forEach((person) => {
          if (itemInPlan.assigned_people_ids.includes(person.id)) {
            const numPeopleSharingThisItem = itemInPlan.assigned_people_ids.length;
            let amountForThisPerson = 0;
            if (numPeopleSharingThisItem > 0) {
              amountForThisPerson = amountToStore / numPeopleSharingThisItem; // amountToStore is already scaled by freq and converted (e.g. energy to kcal)
            } else {
              amountForThisPerson = 0;
            }
            
            let unitForPersonDisplay = unitForDisplay; // unitForDisplay is already standardized (e.g. energy to kcal)
            
            if (fdcForOverallSummary === FDC_NUM_ENERGY) { // Using fdcForOverallSummary as it's derived from contribution
               result.perPersonBreakdown[person.id].total_energy_kcal_for_person += amountForThisPerson;
            }
            
            const individualTargetsForThisPerson = derivedPlanTargets.value.individual_person_targets?.[person.id] || {};
            let personSpecificDRV = null;
            if (Object.keys(individualTargetsForThisPerson).length > 0) {
                personSpecificDRV = individualTargetsForThisPerson[nutrientKey] || // Check with standardized key first
                                    individualTargetsForThisPerson[pureNutrientName] || 
                                    individualTargetsForThisPerson[`${pureNutrientName} (${unitForDisplay})`]; // Check with original name/unit
                if (!personSpecificDRV && fdcForOverallSummary) {
                    const fdcNutrientNameKey = Object.keys(individualTargetsForThisPerson).find(k => individualTargetsForThisPerson[k]?.fdc_nutrient_number === fdcForOverallSummary);
                    if (fdcNutrientNameKey) personSpecificDRV = individualTargetsForThisPerson[fdcNutrientNameKey];
                }
            }
            
            let personDailyRda = personSpecificDRV ? personSpecificDRV.rda : null;
            let personDailyUl = personSpecificDRV ? personSpecificDRV.ul : null;
            let personFdcNumToUse = personSpecificDRV?.fdc_nutrient_number || fdcForOverallSummary;
            let personUnitForDRV = personSpecificDRV?.unit || unitForPersonDisplay;

            if (personFdcNumToUse === FDC_NUM_ENERGY && personUnitForDRV.toLowerCase() === 'kj') {
                if (personDailyRda !== null) personDailyRda *= KJ_TO_KCAL_CONVERSION_FACTOR;
                if (personDailyUl !== null) personDailyUl *= KJ_TO_KCAL_CONVERSION_FACTOR;
            }
            
            const personRdaForPlanDuration = personDailyRda; // Assuming daily DRVs are plan totals as per prior logic
            const personUlForPlanDuration = personDailyUl;

            let determinedPersonCategoryGroup = getHardcodedNutrientGroup(pureNutrientName, personFdcNumToUse);
            const hasPersonReference = (personRdaForPlanDuration !== null && personRdaForPlanDuration !== undefined) || 
                                     (personUlForPlanDuration !== null && personUlForPlanDuration !== undefined);

            if (!hasPersonReference && determinedPersonCategoryGroup !== 'Energy' && determinedPersonCategoryGroup !== 'Macronutrients') {
              determinedPersonCategoryGroup = 'NoReferenceValues';
            }
            
            const personNutrientKeyForStorage = nutrientKey; // Use the same standardized key

            if (!result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup]) {
               result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup] = {};
            }
            if (!result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage]) {
              result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage] = {
                total: 0, unit: unitForPersonDisplay,
                rda: personRdaForPlanDuration,
                ul: personUlForPlanDuration,
                fdc_nutrient_number: personFdcNumToUse,
                kcal_contribution: 0, percent_energy: null
              };
            }
            result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage].total += amountForThisPerson;
            
            if (MACRO_FDC_NUMBERS.includes(personFdcNumToUse) && personFdcNumToUse !== FDC_NUM_ENERGY) {
              let kcalPerGram = 0;
              if (personFdcNumToUse === FDC_NUM_CARB) kcalPerGram = KCAL_PER_GRAM_CARB;
              else if (personFdcNumToUse === FDC_NUM_PROTEIN) kcalPerGram = KCAL_PER_GRAM_PROTEIN;
              else if (personFdcNumToUse === FDC_NUM_FAT) kcalPerGram = KCAL_PER_GRAM_FAT;
              result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage].kcal_contribution += amountForThisPerson * kcalPerGram;
            }
          }
        }); // End of selectedPeopleObjects.forEach for per-person
      }); // End of usage.scaled_nutrient_contributions.forEach
    }); // End of component.ingredientusage_set.forEach
  }); // End of addedMealComponents.value.forEach

  // Calculate %E for overall Macronutrients
  if (result.overallSummary['Macronutrients']) {
    let totalOverallMacroEnergyContribution = 0;
    for (const nutrientKey in result.overallSummary['Macronutrients']) {
      const macroData = result.overallSummary['Macronutrients'][nutrientKey];
      if (MACRO_FDC_NUMBERS.includes(macroData.fdc_nutrient_number) && macroData.kcal_contribution > 0) {
        totalOverallMacroEnergyContribution += macroData.kcal_contribution;
      }
    }

    if (totalOverallMacroEnergyContribution > 0) {
      for (const nutrientKey in result.overallSummary['Macronutrients']) {
        const macroData = result.overallSummary['Macronutrients'][nutrientKey];
        if (MACRO_FDC_NUMBERS.includes(macroData.fdc_nutrient_number) && macroData.kcal_contribution > 0) {
          macroData.percent_energy = (macroData.kcal_contribution / totalOverallMacroEnergyContribution) * 100;
        }
      }
    }
  }

  // Calculate %E for per-person Macronutrients
  selectedPeopleObjects.value.forEach(person => {
    const personData = result.perPersonBreakdown[person.id];
    if (personData.nutrientGroups['Macronutrients']) {
      let totalPersonMacroEnergyContribution = 0;
      for (const nutrientKey in personData.nutrientGroups['Macronutrients']) {
        const macroData = personData.nutrientGroups['Macronutrients'][nutrientKey];
        if (MACRO_FDC_NUMBERS.includes(macroData.fdc_nutrient_number) && macroData.kcal_contribution > 0) {
          totalPersonMacroEnergyContribution += macroData.kcal_contribution;
        }
      }

      if (totalPersonMacroEnergyContribution > 0) {
        for (const nutrientKey in personData.nutrientGroups['Macronutrients']) {
          const macroData = personData.nutrientGroups['Macronutrients'][nutrientKey];
          if (MACRO_FDC_NUMBERS.includes(macroData.fdc_nutrient_number) && macroData.kcal_contribution > 0) {
            macroData.percent_energy = (macroData.kcal_contribution / totalPersonMacroEnergyContribution) * 100;
          }
        }
      }
    }
  });

  // DEBUG: Log per-person breakdown before cleanup
  console.log('[MealPlanForm] Per-Person Breakdown (Before Cleanup):', JSON.parse(JSON.stringify(result.perPersonBreakdown)));

  // Clean up totals and remove empty groups
  ['overallSummary', 'perPersonBreakdown'].forEach(summaryType => {
    const summaryObject = summaryType === 'overallSummary' ? result.overallSummary : null;
    const processGroups = (groupsObject) => {
        for (const groupName in groupsObject) {
            let groupHasNutrients = false;
            if (groupName === 'NoReferenceValues' && Object.keys(groupsObject[groupName]).length === 0) {
                delete groupsObject[groupName]; // Remove NoReferenceValues if empty
                return;
            }
            for (const nutrientKey in groupsObject[groupName]) {
                groupsObject[groupName][nutrientKey].total = parseFloat(groupsObject[groupName][nutrientKey].total.toFixed(2));
                // Keep group if it has nutrients, or if it's NoReferenceValues and has entries.
                if (groupsObject[groupName][nutrientKey].total > 0 || 
                    (groupsObject[groupName][nutrientKey].rda !== null && groupsObject[groupName][nutrientKey].rda !== undefined) || 
                    (groupName === 'NoReferenceValues' && Object.keys(groupsObject[groupName]).length > 0)) {
                    groupHasNutrients = true;
                }
            }
            if (!groupHasNutrients && groupName !== 'NoReferenceValues') { // Don't delete NoReferenceValues here if it was initially populated
                delete groupsObject[groupName];
            } else if (!groupHasNutrients && groupName === 'NoReferenceValues' && Object.keys(groupsObject[groupName]).length === 0) {
                 delete groupsObject[groupName]; // Ensure empty NoReferenceValues is removed
            }
        }
    };

    if (summaryObject) {
        processGroups(summaryObject);
    } else if (summaryType === 'perPersonBreakdown') {
        for (const personId in result.perPersonBreakdown) {
            processGroups(result.perPersonBreakdown[personId].nutrientGroups);
        }
    }
  });

  // DEBUG: Log final result of livePlanNutritionalBreakdown
  console.log('[MealPlanForm] Final livePlanNutritionalBreakdown result:', JSON.parse(JSON.stringify(result)));

  return {
    ...result,
    sourcePlanItems: addedMealComponents.value
  };
});

const addComponentToPlan = (componentToAdd) => {
  if (!componentToAdd || !componentToAdd.id) {
    console.error('[MealPlanForm] Invalid component to add:', componentToAdd);
    return;
  }
  const alreadyAdded = addedMealComponents.value.some(item => item.component.id === componentToAdd.id);
  if (!alreadyAdded) {
    addedMealComponents.value.push({
      id: Date.now() + Math.random(),
      component: componentToAdd, 
      assigned_people_ids: [...planData.value.target_people_ids]
    });
    console.log('[MealPlanForm] Component added:', componentToAdd.name, 'Current addedMealComponents:', JSON.parse(JSON.stringify(addedMealComponents.value)));
  } else {
    console.warn('[MealPlanForm] Component already added:', componentToAdd.name);
  }
};

const removeComponentFromPlan = (componentIdToRemove) => {
  const initialLength = addedMealComponents.value.length;
  addedMealComponents.value = addedMealComponents.value.filter(item => item.component.id !== componentIdToRemove);
  if (addedMealComponents.value.length < initialLength) {
    console.log('[MealPlanForm] Component removed. Current addedMealComponents:', JSON.parse(JSON.stringify(addedMealComponents.value)));
  } else {
    console.warn('[MealPlanForm] Attempted to remove component, but it was not found or list unchanged.');
  }
};

const handleComponentAssignmentUpdate = ({ itemInPlanId, newAssignedIds }) => {
  const itemIndex = addedMealComponents.value.findIndex(item => item.id === itemInPlanId);
  if (itemIndex !== -1) {
    addedMealComponents.value[itemIndex].assigned_people_ids = newAssignedIds;
    console.log('[MealPlanForm] Updated assignments for item:', addedMealComponents.value[itemIndex].component.name, 'New assignments:', newAssignedIds);
  } else {
    console.warn('[MealPlanForm] Could not find itemInPlan to update assignments for ID:', itemInPlanId);
  }
};

// Method to handle starting an edit
const handleEditComponent = (componentToEdit) => {
  console.log('Attempting to edit component:', componentToEdit);
  editingComponent.value = componentToEdit;
};

// Method to handle successful save from MealComponentForm (or cancellation)
const handleComponentFormClose = (updatedComponentData) => {
  if (updatedComponentData) {
    // Potentially refresh list of allMealComponents if it was a new one or name changed
    // For now, just find and update in addedMealComponents if it's there, or allMealComponents
    // This part might need more sophisticated state management or refetching allMealComponents
    const indexInAdded = addedMealComponents.value.findIndex(item => item.component.id === updatedComponentData.id);
    if (indexInAdded !== -1) {
      // Ensure we are updating the nested 'component' object
      addedMealComponents.value[indexInAdded].component = { ...addedMealComponents.value[indexInAdded].component, ...updatedComponentData };
    }
    // Also update in allMealComponents list
    const indexInAll = allMealComponents.value.findIndex(c => c.id === updatedComponentData.id);
    if (indexInAll !== -1) {
      allMealComponents.value[indexInAll] = { ...allMealComponents.value[indexInAll], ...updatedComponentData };
    } else {
      // If it was a new component, it might not be in allMealComponents yet unless we fetch again
      // Or if MealComponentForm handles adding to a global store/list
      // For simplicity, assume MealComponentForm might also emit an event to add to allMealComponents
      // or we refetch if a new component was created and saved.
    }
  }
  editingComponent.value = null; // Close the edit form
};

</script>

<style scoped>
/* Add these to your CSS variables elsewhere or define them here */
:root {
  --color-nutrient-bar-low: #ffe0b2; /* Light Orange/Peach for low %E */
  --color-nutrient-bar-high: #ffcdd2; /* Light Red/Pink for high %E */
  --color-nutrient-bar-good: #c8e6c9; /* Softer Light Green for good %E */
  --color-background-mute: #3a3a3a;  /* Default Muted Background (Dark Gray) */
  --color-text-secondary: #cccccc;   /* Default Text for Muted Background (Light Gray) */
  --color-nutrient-bar-danger: #f8d7da; /* For UL violations (from getPlanNutrientBarStyle) */
  --color-text-dark: #2c3e50; /* Darker text for better contrast on light backgrounds */
}

/* Ensure nutrient-data-row can have its background changed by :style binding */
.nutrient-data-row {
  /* If you have existing background-color here, it might be overridden by the :style binding.
     Ensure specificity or remove if not needed. */
}

.meal-plan-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 20px;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  background-color: var(--color-background);
  max-width: 800px;
  margin: 20px auto;
}
.form-group {
  display: flex;
  flex-direction: column;
}
.form-group label {
  margin-bottom: 5px;
  font-weight: bold;
  color: var(--color-text);
}
.form-group input[type="text"],
.form-group input[type="number"],
.form-group textarea {
  padding: 10px;
  border: 1px solid var(--color-input-border);
  border-radius: 4px;
  font-size: 1em;
  background-color: var(--color-input-bg);
  color: var(--color-text);
}
.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb, 66, 185, 131), 0.3);
}
.form-group textarea {
  min-height: 80px;
  resize: vertical;
}
hr {
  border: none;
  border-top: 1px solid var(--color-border);
  margin-top: 15px;
  margin-bottom: 15px;
}
h2, h3, h4 {
  color: var(--color-text);
  margin-top: 10px;
  margin-bottom: 10px;
}
.component-search-section {
  border: 1px solid var(--color-border);
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  background-color: var(--color-background-soft);
}
.component-tiles-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 15px;
  padding: 10px;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background-color: var(--color-background-mute);
  min-height: 100px;
  max-height: 300px;
  overflow-y: auto;
}
.component-tile {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 12px;
  min-width: 150px;
  max-width: 200px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.component-tile:hover, .component-tile:focus {
  transform: translateY(-3px);
  box-shadow: 0 4px 8px rgba(0,0,0,0.1);
  border-color: var(--color-primary);
  outline: none;
}
.tile-name {
  font-weight: bold;
  color: var(--color-heading);
  margin-bottom: 5px;
  font-size: 0.95em;
  word-break: break-word;
}
.tile-category, .tile-frequency {
  font-size: 0.8em;
  color: var(--color-text-secondary);
  background-color: var(--color-background-mute);
  padding: 2px 6px;
  border-radius: 3px;
  margin-top: 4px;
}
.no-results-message {
  padding: 10px;
  color: var(--color-text-secondary);
  font-style: italic;
  margin-top: 10px;
  text-align: center;
  width: 100%;
}
.added-components-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
}
.added-components-tiles-container {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  padding: 10px;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background-color: var(--color-background-mute);
  min-height: 120px;
}
.added-component-tile {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 15px;
  width: calc(50% - 10px);
  box-shadow: 0 2px 5px rgba(0,0,0,0.07);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
@media (max-width: 768px) {
  .added-component-tile {
    width: calc(100% - 10px);
  }
}
.remove-component-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background-color: var(--color-danger, #e74c3c);
  color: white;
  border: none;
  font-size: 14px;
  font-weight: bold;
  line-height: 22px;
  text-align: center;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: background-color 0.2s ease;
}
.remove-component-btn:hover {
  background-color: var(--color-danger-dark, #c0392b);
}
.component-tile-header .tile-name {
  font-weight: bold;
  font-size: 1.1em;
  color: var(--color-heading);
  margin-bottom: 5px;
}
.component-tile-details {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.component-tile-details .tile-category,
.component-tile-details .tile-frequency {
  font-size: 0.8em;
  color: var(--color-text-secondary);
  background-color: var(--color-background-mute);
  padding: 3px 7px;
  border-radius: 4px;
}
.person-assignment-section h5 {
  font-size: 0.9em;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  font-weight: normal;
}
.person-assignment-checkboxes {
  display: flex;
  flex-direction: column;
  gap: 5px;
  max-height: 100px;
  overflow-y: auto;
  padding-right: 5px;
}
.person-checkbox-label {
  display: flex;
  align-items: center;
  font-size: 0.9em;
  color: var(--color-text);
  cursor: pointer;
}
.person-checkbox-label input[type="checkbox"] {
  margin-right: 8px;
  cursor: pointer;
}
.person-checkbox-label input[type="checkbox"]:checked {
  background-color: var(--color-primary);
  border-color: var(--color-primary);
}
.person-checkbox-label input[type="checkbox"]:checked:hover {
  background-color: var(--color-primary-dark);
}
.no-people-in-plan-message {
  font-size: 0.85em;
  color: var(--color-text-secondary);
  font-style: italic;
}
.form-actions {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.form-actions button {
  padding: 12px 25px;
  background-color: var(--color-button-bg);
  color: var(--color-button-text);
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  font-weight: bold;
}
.form-actions button:disabled {
  background-color: var(--color-border);
  opacity: 0.7;
  cursor: not-allowed;
}
.error-message {
  color: var(--color-danger, #e74c3c);
  margin-top: 15px;
  padding: 10px;
  border: 1px solid var(--color-danger, #e74c3c);
  background-color: rgba(231, 76, 60, 0.1);
  border-radius: 4px;
}
.nutritional-breakdown-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
}
.nutritional-breakdown-table {
  width: 100%;
  border-collapse: collapse;
}
.nutritional-breakdown-table th,
.nutritional-breakdown-table td {
  border: 1px solid var(--color-border);
  padding: 8px;
  text-align: left;
  color: var(--color-text);
}
.nutritional-breakdown-table th {
  background-color: var(--color-input-bg);
}
.nutrient-group {
  background-color: var(--color-background-soft);
}
.nutrient-group-header {
  background-color: var(--color-input-bg);
}
.nutrient-data-row {
  background-color: var(--color-background);
}
.nutrient-value-cell {
  text-align: right;
}
.plan-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}
.plan-target-people {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative;
}
.person-circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--color-primary-light);
  color: var(--color-primary-dark);
  font-weight: bold;
  font-size: 0.8em;
  border: 1px solid var(--color-primary);
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  cursor: default;
}
.add-person-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--color-button-bg);
  color: var(--color-button-text);
  border: none;
  font-size: 1.2em;
  font-weight: bold;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}
.add-person-btn:hover {
  background-color: var(--color-primary-dark);
}
.person-profile-selector {
  position: absolute;
  top: 100%;
  right: 0;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 10px;
  margin-top: 5px;
  min-width: 200px;
  z-index: 10;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}
.person-profile-selector ul {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
}
.person-profile-selector li {
  padding: 8px 10px;
  cursor: pointer;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-hover);
}
.person-profile-selector li:last-child {
  border-bottom: none;
}
.person-profile-selector li:hover {
  background-color: var(--color-primary-light);
  color: var(--color-primary-dark);
}
.person-profile-selector p {
  font-size: 0.9em;
  color: var(--color-text-secondary);
  padding: 5px 0;
  text-align: center;
}
.create-profile-link {
  display: block;
  text-align: center;
  margin-top: 10px;
  padding: 8px;
  background-color: var(--color-primary);
  color: var(--color-button-text);
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.9em;
}
.create-profile-link:hover {
  background-color: var(--color-primary-dark);
}

/* Tabs for breakdown */
.breakdown-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 15px;
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 10px;
}
.breakdown-tabs button {
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  background-color: var(--color-background-soft);
  color: var(--color-text);
  cursor: pointer;
  border-radius: 4px 4px 0 0;
  font-size: 0.9em;
  margin-bottom: -1px; /* Overlap border-bottom */
}
.breakdown-tabs button.active {
  background-color: var(--color-background);
  border-bottom-color: var(--color-background);
  font-weight: bold;
  color: var(--color-primary);
}
.breakdown-tabs button:hover:not(.active) {
  background-color: var(--color-background-mute);
}
.breakdown-content h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.no-reference-table {
  margin-top: 25px;
  font-size: 0.9em; /* Slightly smaller font */
}
.no-reference-table th,
.no-reference-table td {
  padding: 6px 8px; /* Adjust padding */
  color: var(--color-text-secondary); /* Muted text color */
}
.no-reference-table th {
   background-color: var(--color-input-bg); /* Consistent header background */
}
.no-reference-table .nutrient-data-row {
    background-color: var(--color-background-mute); /* Muted background for rows */
}
.no-reference-table .nutrient-value-cell {
    text-align: right;
}

</style> 