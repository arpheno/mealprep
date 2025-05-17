<template>
  <form @submit.prevent="submitMealPlan" class="meal-plan-form">
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
import NutritionalBreakdown from './NutritionalBreakdown.vue'; // Import the new component
import PlanHeader from './PlanHeader.vue'; // Import the new PlanHeader component
import PlanDetailsForm from './PlanDetailsForm.vue'; // Import the new PlanDetailsForm component
import MealComponentSearch from './MealComponentSearch.vue'; // Import the new MealComponentSearch component
import AddedMealComponentsDisplay from './AddedMealComponentsDisplay.vue'; // Import the new component

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

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
  const combinedTargets = {};
  const individualTargets = {};
  let hasAnyRdaOrUl = false;

  // Initialize combinedTargets with all system nutrients from the first available person's DRVs 
  // or a fallback structure if no people are selected yet or if DRVs are sparse.
  // This is a simplified approach; ideally, you'd have a base list of all possible nutrients.
  // For now, we build it dynamically.
  const allNutrientKeysInPlan = new Set();

  selectedPeopleObjects.value.forEach(person => {
    if (person.personalized_drvs) {
      Object.keys(person.personalized_drvs).forEach(key => {
        allNutrientKeysInPlan.add(key);
      });
    }
  });

  allNutrientKeysInPlan.forEach(key => {
    combinedTargets[key] = { rda: 0, ul: null, unit: '', fdc_nutrient_number: null };
  });


  selectedPeopleObjects.value.forEach(person => {
    individualTargets[person.id] = {};
    if (person.personalized_drvs) {
      // Store a deep copy for individual use to avoid unintended mutations if DRV objects are reused.
      // Also, ensure all nutrients from combinedTargets are present for consistency.
      allNutrientKeysInPlan.forEach(key => {
        const drv = person.personalized_drvs[key];
        individualTargets[person.id][key] = drv 
            ? JSON.parse(JSON.stringify(drv)) 
            : { rda: null, ul: null, unit: combinedTargets[key]?.unit || '', fdc_nutrient_number: combinedTargets[key]?.fdc_nutrient_number || null };
      });
      
      // Aggregate for combined targets
      for (const nutrientKey in person.personalized_drvs) {
        const drv_values = person.personalized_drvs[nutrientKey];
        if (!combinedTargets[nutrientKey]) { // Should be initialized above, but as a safeguard
          combinedTargets[nutrientKey] = { rda: 0, ul: null, unit: drv_values.unit || '', fdc_nutrient_number: drv_values.fdc_nutrient_number || null };
        } else { // Ensure unit and FDC number are set if missing from initial pass
             if (!combinedTargets[nutrientKey].unit && drv_values.unit) combinedTargets[nutrientKey].unit = drv_values.unit;
             if (!combinedTargets[nutrientKey].fdc_nutrient_number && drv_values.fdc_nutrient_number) combinedTargets[nutrientKey].fdc_nutrient_number = drv_values.fdc_nutrient_number;
        }

        if (drv_values.rda !== null && drv_values.rda !== undefined) {
          combinedTargets[nutrientKey].rda += drv_values.rda;
          hasAnyRdaOrUl = true;
        }
        if (drv_values.ul !== null && drv_values.ul !== undefined) {
          hasAnyRdaOrUl = true;
          if (combinedTargets[nutrientKey].ul === null || drv_values.ul < combinedTargets[nutrientKey].ul) {
            combinedTargets[nutrientKey].ul = drv_values.ul;
          }
        }
      }
    } else {
        // If a person has no personalized_drvs, ensure their entry exists with null/default values for all keys
        allNutrientKeysInPlan.forEach(key => {
            individualTargets[person.id][key] = { 
                rda: null, 
                ul: null, 
                unit: combinedTargets[key]?.unit || '', 
                fdc_nutrient_number: combinedTargets[key]?.fdc_nutrient_number || null 
            };
        });
    }
  });

  // Filter out nutrients from combinedTargets that ended up with no RDA and no UL,
  // unless they were present in at least one person's DRVs (even if values were null).
  const finalCombinedTargets = {};
  for (const key in combinedTargets) {
    if ((combinedTargets[key].rda !== 0 && combinedTargets[key].rda !== null) || combinedTargets[key].ul !== null || allNutrientKeysInPlan.has(key)) {
       finalCombinedTargets[key] = combinedTargets[key];
    }
  }
  
  // If no people, or no one has DRVs, combined targets will be empty or all zeros.
  // If no RDAs/ULs at all, hasAnyRdaOrUl remains false.
  // The structure expects `combined_plan_targets` and `individual_person_targets`.
  return {
    combined_plan_targets: (selectedPeopleObjects.value.length > 0 && hasAnyRdaOrUl) ? finalCombinedTargets : {},
    individual_person_targets: individualTargets,
    _debug_selected_people_count: selectedPeopleObjects.value.length,
    _debug_has_any_rda_ul_overall: hasAnyRdaOrUl
  };
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
  let totalPlanEnergyKcalOverall = 0; // For overall summary %E

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
    if (!component.nutritional_totals || Object.keys(component.nutritional_totals).length === 0) {
        console.warn(`[MealPlanForm] Component ${component.name} has no nutritional_totals. Skipping.`);
        return;
    }

    const duration = planData.value.duration_days || 7;
    const servingsPerDayPerPerson = planData.value.servings_per_day_per_person || 1;
    let consumption_multiplier_per_person = 0;

    if (component.frequency === 'PER_BOX') consumption_multiplier_per_person = duration * servingsPerDayPerPerson;
    else if (component.frequency === 'DAILY') consumption_multiplier_per_person = duration;
    else if (component.frequency === 'WEEKLY') consumption_multiplier_per_person = duration / 7.0;
    else consumption_multiplier_per_person = 1; // Default, e.g. for ONE_TIME_CONSUMPTION or if frequency not set

    for (const nutrientFullName in component.nutritional_totals) {
      const nutrientNameMatch = nutrientFullName.match(/^(.*?) *\(/);
      const pureNutrientName = nutrientNameMatch ? nutrientNameMatch[1].trim() : nutrientFullName.trim();
      const nutrientDataFromComponent = component.nutritional_totals[nutrientFullName];
      
      let nutrientAmountFromItemScaledByFreq = (nutrientDataFromComponent.amount || 0) * consumption_multiplier_per_person;
      let unitForDisplay = nutrientDataFromComponent.unit || 'N/A';
      
      // Accessing COMBINED targets for OVERALL summary:
      const overallPlanCombinedTargetData = derivedPlanTargets.value.combined_plan_targets || {};
      const overallPlanCombinedTarget = overallPlanCombinedTargetData[pureNutrientName] || overallPlanCombinedTargetData[`${pureNutrientName} (${unitForDisplay})`];
      
      let fdcNumForData = (overallPlanCombinedTarget || {}).fdc_nutrient_number || null;
      if (!fdcNumForData) { 
        const nameLower = pureNutrientName.toLowerCase();
        if (nameLower.includes('protein')) fdcNumForData = FDC_NUM_PROTEIN;
        else if (nameLower.includes('carbohydrate')) fdcNumForData = FDC_NUM_CARB;
        else if (nameLower.includes('total lipid') || nameLower.includes('total fat')) fdcNumForData = FDC_NUM_FAT;
        else if (nameLower.includes('energy')) fdcNumForData = FDC_NUM_ENERGY;
      }

      let itemEnergyKcal = 0;
      if (fdcNumForData === FDC_NUM_ENERGY) {
        itemEnergyKcal = (unitForDisplay.toLowerCase() === 'kj') ? nutrientAmountFromItemScaledByFreq * KJ_TO_KCAL_CONVERSION_FACTOR : nutrientAmountFromItemScaledByFreq;
        if (unitForDisplay.toLowerCase() === 'kj') unitForDisplay = 'kcal'; // Standardize display unit for energy
        nutrientAmountFromItemScaledByFreq = itemEnergyKcal; // Use kcal amount for further calcs for energy
      }
      
      let displayKeyName = pureNutrientName;
      if (fdcNumForData === FDC_NUM_FAT && pureNutrientName.toLowerCase().includes("total lipid (fat)")) {
        displayKeyName = "Total lipid";
      }
      const nutrientKey = `${displayKeyName} (${unitForDisplay})`;
      let determinedOverallCategoryGroup = getHardcodedNutrientGroup(pureNutrientName, fdcNumForData);
      
      const overallRdaFromPlanTarget = overallPlanCombinedTarget?.rda;
      const overallUlFromPlanTarget = overallPlanCombinedTarget?.ul;
      const hasOverallReference = (overallRdaFromPlanTarget !== null && overallRdaFromPlanTarget !== undefined) || 
                                (overallUlFromPlanTarget !== null && overallUlFromPlanTarget !== undefined);

      if (!hasOverallReference && determinedOverallCategoryGroup !== 'Energy' && determinedOverallCategoryGroup !== 'Macronutrients') {
        determinedOverallCategoryGroup = 'NoReferenceValues';
      }
      
      if (!result.overallSummary[determinedOverallCategoryGroup]) result.overallSummary[determinedOverallCategoryGroup] = {};
      if (!result.overallSummary[determinedOverallCategoryGroup][nutrientKey]) {
        result.overallSummary[determinedOverallCategoryGroup][nutrientKey] = {
          total: 0, unit: unitForDisplay, 
          rda: overallRdaFromPlanTarget,
          ul: overallUlFromPlanTarget,
          fdc_nutrient_number: fdcNumForData,
          kcal_contribution: 0, 
          percent_energy: null 
        };
      }
      
      // Corrected logic for overall summary: sum the total produced by the component instance
      result.overallSummary[determinedOverallCategoryGroup][nutrientKey].total += nutrientAmountFromItemScaledByFreq;
      if (fdcNumForData === FDC_NUM_ENERGY) {
         totalPlanEnergyKcalOverall += nutrientAmountFromItemScaledByFreq; // Use itemEnergyKcal if already calculated, or nutrientAmountFromItemScaledByFreq if energy
      }

      if (MACRO_FDC_NUMBERS.includes(fdcNumForData)) {
        let kcalPerGram = 0;
        if (fdcNumForData === FDC_NUM_CARB) kcalPerGram = KCAL_PER_GRAM_CARB;
        else if (fdcNumForData === FDC_NUM_PROTEIN) kcalPerGram = KCAL_PER_GRAM_PROTEIN;
        else if (fdcNumForData === FDC_NUM_FAT) kcalPerGram = KCAL_PER_GRAM_FAT;
        result.overallSummary[determinedOverallCategoryGroup][nutrientKey].kcal_contribution += nutrientAmountFromItemScaledByFreq * kcalPerGram;
      }

      selectedPeopleObjects.value.forEach((person) => {
        if (itemInPlan.assigned_people_ids.includes(person.id)) {
          console.log(`[MealPlanForm] Component ${component.name} IS ASSIGNED to person ${person.name}. Processing nutrient: ${nutrientFullName}`);
          
          const numPeopleSharingThisItem = itemInPlan.assigned_people_ids.length;
          let amountForThisPerson = 0;
          if (numPeopleSharingThisItem > 0) {
            amountForThisPerson = nutrientAmountFromItemScaledByFreq / numPeopleSharingThisItem;
          } else {
            // This case should ideally not happen if itemInPlan.assigned_people_ids.includes(person.id) is true
            // and numPeopleSharingThisItem is derived from that same list.
            // However, as a safeguard:
            amountForThisPerson = 0; 
          }
          
          let unitForPersonDisplay = unitForDisplay; // Assuming unit is same as overall for now

          let currentPersonEnergyContribution = 0;
          if (fdcNumForData === FDC_NUM_ENERGY) { // Energy would have been converted to kcal if originally kJ
             currentPersonEnergyContribution = (unitForDisplay.toLowerCase() === 'kj' && nutrientDataFromComponent.unit.toLowerCase() === 'kj') 
                                             ? (amountForThisPerson * KJ_TO_KCAL_CONVERSION_FACTOR) 
                                             : amountForThisPerson;
             if (unitForDisplay.toLowerCase() === 'kj') unitForPersonDisplay = 'kcal';
             result.perPersonBreakdown[person.id].total_energy_kcal_for_person += currentPersonEnergyContribution;
          }
          
          // REVISED LOGIC FOR PER-PERSON RDA/UL using individual_person_targets from derivedPlanTargets:
          const individualTargetsForThisPerson = derivedPlanTargets.value.individual_person_targets?.[person.id] || {};

          let personSpecificDRV = null;
          if (Object.keys(individualTargetsForThisPerson).length > 0) {
              personSpecificDRV = individualTargetsForThisPerson[nutrientKey] || 
                                  individualTargetsForThisPerson[pureNutrientName] || 
                                  individualTargetsForThisPerson[`${pureNutrientName} (${nutrientDataFromComponent.unit})`];
              if (!personSpecificDRV && fdcNumForData) { // fdcNumForData here is from the overall combined target, might need person-specific if different
                  const fdcNutrientNameKey = Object.keys(individualTargetsForThisPerson).find(k => individualTargetsForThisPerson[k]?.fdc_nutrient_number === fdcNumForData);
                  if (fdcNutrientNameKey) personSpecificDRV = individualTargetsForThisPerson[fdcNutrientNameKey];
              }
          } else {
            console.warn(`[MealPlanForm] No individual_person_targets found for person ${person.name} (ID: ${person.id}). Individual targets object for this person:`, JSON.parse(JSON.stringify(individualTargetsForThisPerson)), 'Full individual_person_targets state:', JSON.parse(JSON.stringify(derivedPlanTargets.value.individual_person_targets)));
          }
          
          // --- BEGIN DEBUG LOG ---
          if (pureNutrientName.toLowerCase().includes('energy')) { // Log only for energy to reduce noise
            console.log(`[MealPlanForm DEBUG] For ${person.name}, Nutrient: ${nutrientKey}`);
            console.log(`  Raw personSpecificDRV (daily):`, JSON.parse(JSON.stringify(personSpecificDRV)));
            console.log(`  derivedPlanTargets.individual_person_targets for ${person.name}:`, JSON.parse(JSON.stringify(derivedPlanTargets.value.individual_person_targets?.[person.id])));
          }
          // --- END DEBUG LOG ---

          let personDailyRda = personSpecificDRV ? personSpecificDRV.rda : null;
          let personDailyUl = personSpecificDRV ? personSpecificDRV.ul : null;
          
          let personFdcNumToUse = personSpecificDRV?.fdc_nutrient_number || fdcNumForData; 

          if (personFdcNumToUse === FDC_NUM_ENERGY && unitForPersonDisplay.toLowerCase() === 'kcal' && personSpecificDRV && personSpecificDRV.unit && personSpecificDRV.unit.toLowerCase() === 'kj') {
              if (personDailyRda !== null) personDailyRda *= KJ_TO_KCAL_CONVERSION_FACTOR;
              if (personDailyUl !== null) personDailyUl *= KJ_TO_KCAL_CONVERSION_FACTOR;
          }
          
          // Multiply daily RDA and UL by plan duration for this person
          const planDurationDays = planData.value.duration_days || 1; // Default to 1 if duration is 0 or undefined
          
          // NEW logic (assuming personDailyRda/Ul are already effectively plan totals based on user feedback):
          const personRdaForPlanDuration = personDailyRda;
          const personUlForPlanDuration = personDailyUl;

          console.log(`[MealPlanForm DEBUG DRV] Person: ${person.name}, Nutrient: ${nutrientKey}`);
          console.log(`  planData.duration_days (source): ${planData.value.duration_days}`);
          console.log(`  planDurationDays (used for scaling): ${planDurationDays}`);
          console.log(`  personDailyRda: ${personDailyRda}, personDailyUl: ${personDailyUl}`);
          console.log(`  personRdaForPlanDuration: ${personRdaForPlanDuration}, personUlForPlanDuration: ${personUlForPlanDuration}`);

          let determinedPersonCategoryGroup = getHardcodedNutrientGroup(pureNutrientName, personFdcNumToUse);
          const hasPersonReference = (personRdaForPlanDuration !== null && personRdaForPlanDuration !== undefined) || 
                                   (personUlForPlanDuration !== null && personUlForPlanDuration !== undefined);

          if (!hasPersonReference && determinedPersonCategoryGroup !== 'Energy' && determinedPersonCategoryGroup !== 'Macronutrients') {
            determinedPersonCategoryGroup = 'NoReferenceValues';
          }
          
          const personNutrientKeyForStorage = nutrientKey; 

          if (!result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup]) {
             result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup] = {};
          }
          if (!result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage]) {
            result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage] = {
              total: 0, unit: unitForPersonDisplay,
              rda: personRdaForPlanDuration, // Use plan duration RDA
              ul: personUlForPlanDuration,   // Use plan duration UL
              fdc_nutrient_number: personFdcNumToUse,
              kcal_contribution: 0, percent_energy: null // Add for per-person macros
            };
          }
          result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage].total += amountForThisPerson;
          
          if (MACRO_FDC_NUMBERS.includes(personFdcNumToUse)) {
            let kcalPerGram = 0;
            if (personFdcNumToUse === FDC_NUM_CARB) kcalPerGram = KCAL_PER_GRAM_CARB;
            else if (personFdcNumToUse === FDC_NUM_PROTEIN) kcalPerGram = KCAL_PER_GRAM_PROTEIN;
            else if (personFdcNumToUse === FDC_NUM_FAT) kcalPerGram = KCAL_PER_GRAM_FAT;
            // Use amountForThisPerson for kcal_contribution
            result.perPersonBreakdown[person.id].nutrientGroups[determinedPersonCategoryGroup][personNutrientKeyForStorage].kcal_contribution += amountForThisPerson * kcalPerGram;
          }
          // console.log(`[MealPlanForm] For ${person.name}, Nutrient ${nutrientKey}: RDA = ${personRdaForPlanDuration}, UL = ${personUlForPlanDuration}`); // Original log, now updated
        }
      });
    }
  });
  
  if (totalPlanEnergyKcalOverall > 0 && result.overallSummary['Macronutrients']) {
    for (const nutrientKey in result.overallSummary['Macronutrients']) {
      const macroData = result.overallSummary['Macronutrients'][nutrientKey];
      if (MACRO_FDC_NUMBERS.includes(macroData.fdc_nutrient_number) && macroData.kcal_contribution > 0) {
        macroData.percent_energy = (macroData.kcal_contribution / totalPlanEnergyKcalOverall) * 100;
      }
    }
  }

  // Calculate %E for per-person Macronutrients
  selectedPeopleObjects.value.forEach(person => {
    const personData = result.perPersonBreakdown[person.id];
    if (personData.total_energy_kcal_for_person > 0 && personData.nutrientGroups['Macronutrients']) {
      for (const nutrientKey in personData.nutrientGroups['Macronutrients']) {
        const macroData = personData.nutrientGroups['Macronutrients'][nutrientKey];
        if (MACRO_FDC_NUMBERS.includes(macroData.fdc_nutrient_number) && macroData.kcal_contribution > 0) {
          macroData.percent_energy = (macroData.kcal_contribution / personData.total_energy_kcal_for_person) * 100;
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