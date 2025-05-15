<template>
  <form @submit.prevent="submitMealPlan" class="meal-plan-form">
    <div class="plan-header">
      <h2>Create/Edit Meal Plan</h2>
      <div class="plan-target-people">
        <span 
          v-for="person in selectedPeopleObjects" 
          :key="person.id" 
          class="person-circle"
          :title="person.name"
        >
          {{ getProfileInitials(person.name) }}
        </span>
        <button 
          type="button" 
          @click="showPersonProfileSelector = !showPersonProfileSelector" 
          class="add-person-btn"
          title="Add person to plan"
        >
          +
        </button>
        <div v-if="showPersonProfileSelector" class="person-profile-selector">
          <ul v-if="availablePeopleToAdd.length > 0">
            <li 
              v-for="person in availablePeopleToAdd" 
              :key="person.id" 
              @click="addPersonToPlan(person)"
            >
              {{ person.name }}
            </li>
          </ul>
          <p v-else>No other person profiles available to add.</p>
          <router-link to="/create-person-profile" class="create-profile-link">Create New Profile</router-link>
        </div>
      </div>
    </div>

    <div class="form-group">
      <label for="plan-name">Plan Name:</label>
      <input type="text" id="plan-name" v-model="planData.name" required />
    </div>

    <div class="form-group">
      <label for="plan-description">Description:</label>
      <textarea id="plan-description" v-model="planData.description"></textarea>
    </div>
    
    <div class="form-group">
      <label for="duration-days">Duration (days):</label>
      <input type="number" id="duration-days" v-model.number="planData.duration_days" min="1" />
    </div>
    
    <div class="form-group">
      <label for="servings-per-day">Servings per Day (per person):</label>
      <input type="number" id="servings-per-day" v-model.number="planData.servings_per_day_per_person" min="1" />
    </div>

    <hr />

    <h3>Add Meal Components</h3>
    <div class="component-search-section">
      <div class="form-group">
        <label for="component-filter">Filter Components:</label>
        <input
          type="text"
          id="component-filter"
          v-model="mealComponentSearch"
          placeholder="Type to filter components..."
          @input="() => { /* Input handled by computed property automatically */ }"
        />

        <div v-if="allMealComponents.length > 0" class="component-tiles-container">
          <div 
            v-for="component in filteredMealComponents" 
            :key="component.id" 
            class="component-tile"
            @click="addComponentToPlan(component)"
            role="button"
            tabindex="0"
          >
            <span class="tile-name">{{ component.name }}</span>
            <span v-if="component.category_tag" class="tile-category">{{ component.category_tag }}</span>
            <span v-if="component.frequency" class="tile-frequency">{{ component.frequency }}</span>
          </div>
        </div>

        <p v-if="searchedAndNoResults && mealComponentSearch.length > 0" class="no-results-message">
          No meal components match "{{ mealComponentSearch }}".
        </p>
        <p v-if="allMealComponents.length === 0 && !error" class="no-results-message">
          No meal components available. Create some first!
        </p>
      </div>
    </div>

    <div v-if="addedMealComponents.length" class="added-components-list">
      <h4>Added Meal Components:</h4>
      <table>
        <thead>
          <tr>
            <th>Component Name</th>
            <th>Category</th>
            <th>Frequency</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="componentInPlan in addedMealComponents" :key="componentInPlan.id">
            <td>{{ componentInPlan.name }}</td>
            <td>{{ componentInPlan.category_tag }}</td>
            <td>{{ componentInPlan.frequency }}</td>
            <td>
              <button type="button" @click="removeComponentFromPlan(componentInPlan.id)" class="remove-btn">&times;</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <hr />
    
    <!-- Nutritional Breakdown for the Plan -->
    <div v-if="Object.keys(livePlanNutritionalBreakdown).length > 0" class="nutritional-breakdown-section plan-breakdown">
      <h3>Live Plan Nutritional Breakdown (for {{ planData.duration_days }} days)</h3>
      <table class="nutritional-breakdown-table">
        <thead>
          <tr>
            <th>Nutrient</th>
            <th>Total for Plan</th>
            <th>Daily Average</th>
            <th>RDA for Plan</th>
            <th>UL for Plan</th>
          </tr>
        </thead>
        <template v-for="(nutrientsInGroup, groupName) in livePlanNutritionalBreakdown" :key="groupName">
          <tbody v-if="Object.keys(nutrientsInGroup).length > 0" class="nutrient-group">
            <tr class="nutrient-group-header">
              <th :colspan="5">{{ groupName }}</th>
            </tr>
            <tr v-for="(nutrientData, nutrientKey) in nutrientsInGroup" :key="nutrientKey" :style="getPlanNutrientBarStyle(nutrientData)" class="nutrient-data-row">
              <td>{{ nutrientKey }}</td>
              <td class="nutrient-value-cell">{{ nutrientData.total.toFixed(2) }}</td>
              <td class="nutrient-value-cell">{{ (nutrientData.total / (planData.duration_days || 1)).toFixed(2) }}</td>
              <td class="nutrient-value-cell">{{ formatDRV(nutrientData.rda !== null ? nutrientData.rda * (planData.duration_days || 1) : null) }}</td>
              <td class="nutrient-value-cell">{{ formatDRV(nutrientData.ul !== null ? nutrientData.ul * (planData.duration_days || 1) : null) }}</td>
            </tr>
          </tbody>
        </template>
      </table>
    </div>

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
import { ref, computed, onMounted, watch } from 'vue';
import axios from 'axios';
import api from '../services/api.js';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

const planData = ref({
  name: '',
  description: '',
  duration_days: 7,
  servings_per_day_per_person: 1,
  target_people_ids: [],
  meal_component_ids: [],
  target_people_profiles: [],
  selected_person_profiles_in_form: [],
});

const allNutrients = ref([]);
const allMealComponents = ref([]);
const allPersonProfiles = ref([]);
const showPersonProfileSelector = ref(false);

const mealComponentSearch = ref('');
const addedMealComponents = ref([]);
const isSaving = ref(false);
const error = ref(null);

const currentPlanTargets = ref({});

onMounted(async () => {
  try {
    const componentsResponse = await axios.get(`${API_BASE_URL}/mealcomponents/`);
    allMealComponents.value = componentsResponse.data.results || componentsResponse.data;
    console.log('Fetched all meal components:', allMealComponents.value);

    const profilesResponse = await axios.get(`${API_BASE_URL}/personprofiles/`);
    allPersonProfiles.value = profilesResponse.data.results || profilesResponse.data;
    console.log('Fetched all person profiles:', allPersonProfiles.value);

  } catch (err) {
    console.error('Error fetching initial data (components or profiles):', err);
    error.value = 'Failed to load initial data. ' + (err.response?.data?.detail || err.message);
  }
});

const filteredMealComponents = computed(() => {
  if (!mealComponentSearch.value) {
    return allMealComponents.value;
  }
  const searchTermLower = mealComponentSearch.value.toLowerCase();
  const results = allMealComponents.value.filter(component => 
    component.name.toLowerCase().includes(searchTermLower) ||
    (component.category_tag && component.category_tag.toLowerCase().includes(searchTermLower))
  );
  return results;
});

const searchedAndNoResults = computed(() => {
  return mealComponentSearch.value.length > 0 && filteredMealComponents.value.length === 0;
});

const selectedPeopleObjects = ref([]);
const availablePeopleToAdd = computed(() => {
  const selectedIds = new Set(planData.value.target_people_ids);
  return allPersonProfiles.value.filter(p => !selectedIds.has(p.id));
});

const addPersonToPlan = (personProfile) => {
  if (!personProfile || !personProfile.id) {
    console.error('Invalid person profile selected:', personProfile);
    return;
  }
  if (!planData.value.selected_person_profiles_in_form.some(p => p.id === personProfile.id)) {
    planData.value.selected_person_profiles_in_form.push(personProfile);
    planData.value.target_people_profiles.push(personProfile.id);
    planData.value.target_people_ids.push(personProfile.id);
    
    if (!selectedPeopleObjects.value.some(p => p.id === personProfile.id)) {
        selectedPeopleObjects.value.push(allPersonProfiles.value.find(p => p.id === personProfile.id));
    }
  }
  showPersonProfileSelector.value = false;
};

const getProfileInitials = (name) => {
  if (!name) return '?';
  const parts = name.split(' ');
  if (parts.length > 1) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
};

const submitMealPlan = async () => {
  if (addedMealComponents.value.length === 0) {
    alert('Please add at least one meal component to the plan.');
    return;
  }
  isSaving.value = true;
  error.value = null;

  const payload = {
    name: planData.value.name,
    description: planData.value.description,
    duration_days: planData.value.duration_days,
    servings_per_day_per_person: planData.value.servings_per_day_per_person,
    meal_component_ids: planData.value.meal_component_ids,
    target_people_profiles: planData.value.target_people_ids,
  };

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
    if (["203", "204", "205", "291"].includes(fdcNumber)) return 'Macronutrients';
    if (nameLower.includes('protein') || nameLower.includes('fat') || nameLower.includes('lipid') || 
        nameLower.includes('carbohydrate') || nameLower.includes('fiber')) {
      return 'Macronutrients';
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
    if (fdcNumber === "208" || nameLower.includes('energy') || nameLower.includes('water') || 
        nameLower.includes('caffeine') || nameLower.includes('alcohol') || nameLower.includes('cholesterol') ||
        nameLower.includes('ash') || nameLower.includes('theobromine')) {
      return 'General & Other';
    }
    return 'General & Other';
};

const livePlanNutritionalBreakdown = computed(() => {
  const groupedBreakdown = {
    'Macronutrients': {},
    'Minerals': {},
    'Vitamins': {},
    'General & Other': {}
  };

  const numPeople = planData.value.target_people_ids.length > 0 ? planData.value.target_people_ids.length : 1;

  addedMealComponents.value.forEach(component => {
    if (!component.nutritional_totals || Object.keys(component.nutritional_totals).length === 0) {
      console.warn(`Component ${component.name} (ID: ${component.id}) has no nutritional_totals. Skipping in plan breakdown.`);
      return;
    }

    let consumption_occasions_per_person = 0;
    const duration = planData.value.duration_days || 7;
    const servingsPerDayPerPerson = planData.value.servings_per_day_per_person || 1;

    if (component.frequency === 'PER_BOX') {
      consumption_occasions_per_person = duration * servingsPerDayPerPerson;
    } else if (component.frequency === 'DAILY') {
      consumption_occasions_per_person = duration;
    } else if (component.frequency === 'WEEKLY') {
      consumption_occasions_per_person = duration / 7.0;
    } else {
        console.warn(`Unknown component frequency: ${component.frequency} for component ${component.name}. Defaulting multiplier to 1.`);
        consumption_occasions_per_person = 1;
    }

    for (const nutrientFullName in component.nutritional_totals) {
      const nutrientNameMatch = nutrientFullName.match(/^(.*?) *\(/);
      const pureNutrientName = nutrientNameMatch ? nutrientNameMatch[1].trim() : nutrientFullName.trim();
      
      const nutrientDataFromComponent = component.nutritional_totals[nutrientFullName];
      const scaledAmount = (nutrientDataFromComponent.amount || 0) * consumption_occasions_per_person * numPeople;

      const planTargetForNutrient = currentPlanTargets.value[pureNutrientName] || currentPlanTargets.value[nutrientFullName];
      
      const baseNutrientInfo = allNutrients.value.find(n => n.name === pureNutrientName);
      
      const nutrientKey = `${pureNutrientName} (${nutrientDataFromComponent.unit || (baseNutrientInfo ? baseNutrientInfo.unit : 'N/A')})`;
      const categorySource = planTargetForNutrient || baseNutrientInfo;
      const categoryGroup = categorySource ? getHardcodedNutrientGroup(categorySource.name || pureNutrientName, categorySource.fdc_nutrient_number) : getHardcodedNutrientGroup(pureNutrientName, null);

      if (!groupedBreakdown[categoryGroup][nutrientKey]) {
        groupedBreakdown[categoryGroup][nutrientKey] = {
          total: 0,
          unit: nutrientDataFromComponent.unit || (categorySource ? categorySource.unit : 'N/A'),
          rda: planTargetForNutrient ? planTargetForNutrient.rda : (baseNutrientInfo ? baseNutrientInfo.default_rda : null),
          ul: planTargetForNutrient ? planTargetForNutrient.ul : (baseNutrientInfo ? baseNutrientInfo.upper_limit : null),
        };
      }

      groupedBreakdown[categoryGroup][nutrientKey].total += scaledAmount;
    }
  });
  
  const finalBreakdown = {};
  for (const groupName in groupedBreakdown) {
    const group = groupedBreakdown[groupName];
    const filteredGroupNutrients = {};
    let groupHasNutrients = false;

    for (const nutrientKey in group) {
      group[nutrientKey].total = parseFloat(group[nutrientKey].total.toFixed(2));
      if (group[nutrientKey].total > 0 || group[nutrientKey].rda !== null) {
        filteredGroupNutrients[nutrientKey] = group[nutrientKey];
        groupHasNutrients = true;
      }
    }
    if (groupHasNutrients) {
      finalBreakdown[groupName] = filteredGroupNutrients;
    }
  }
  return finalBreakdown;
});

const formatDRV = (value) => {
  if (value === null || value === undefined) return '-';
  if (typeof value === 'number') return Number.isInteger(value) ? value : value.toFixed(2);
  return value;
};

const getPlanNutrientBarStyle = (nutrientData) => {
  const totalForDuration = nutrientData.total;
  const dailyRda = nutrientData.rda;
  const dailyUl = nutrientData.ul;
  const planDuration = planData.value.duration_days || 1;

  const rdaForDuration = dailyRda !== null ? dailyRda * planDuration : null;
  const ulForDuration = dailyUl !== null ? dailyUl * planDuration : null;
  
  let percentage = 0;
  if (rdaForDuration && rdaForDuration > 0) {
    percentage = (totalForDuration / rdaForDuration) * 100;
  }

  const baseGreenH = 120; 
  const baseGreenS = 50;  
  const baseGreenL = 60;  
  const targetGreenS = 70; 
  const targetGreenL = 50; 
  const dangerColor = 'var(--color-nutrient-bar-danger)';
  let currentBackgroundColor = 'transparent';

  if (ulForDuration && ulForDuration > 0 && totalForDuration > ulForDuration) {
    currentBackgroundColor = dangerColor;
  } else if (rdaForDuration && rdaForDuration > 0) {
    if (totalForDuration >= 0) {
      const saturationRatio = Math.min(percentage / 100, 1);
      const currentS = baseGreenS + (targetGreenS - baseGreenS) * saturationRatio;
      const currentL = baseGreenL - (baseGreenL - targetGreenL) * saturationRatio;
      currentBackgroundColor = `hsl(${baseGreenH}, ${currentS.toFixed(0)}%, ${currentL.toFixed(0)}%)`;
    }
  } else if (totalForDuration > 0) {
    if (ulForDuration && ulForDuration > 0 && totalForDuration > ulForDuration) {
      currentBackgroundColor = dangerColor;
    } else {
      currentBackgroundColor = `hsl(${baseGreenH}, ${baseGreenS * 0.5}%, ${baseGreenL * 1.1}%)`;
    }
  }

  if (totalForDuration === 0 && (!rdaForDuration || rdaForDuration === 0)) {
    return { background: 'transparent' };
  }
   if ((!rdaForDuration || rdaForDuration <= 0) && totalForDuration > 0 ) {
      if (ulForDuration && ulForDuration > 0 && totalForDuration > ulForDuration) {
          return { background: dangerColor };
      }
      return { background: `linear-gradient(to right, ${currentBackgroundColor} 15px, var(--color-input-bg) 15px)` };
  }

  const visualProgressPercentage = Math.max(0, Math.min(percentage, 100));
  return {
    background: `linear-gradient(to right, ${currentBackgroundColor} ${visualProgressPercentage}%, color-mix(in srgb, ${currentBackgroundColor} 20%, transparent) ${Math.min(100, visualProgressPercentage + 5)}%, transparent ${Math.min(100, visualProgressPercentage + 10)}%)`,
    transition: 'background 0.5s ease',
  };
};

const fetchPlanNutritionalTargets = async (personProfileIds) => {
  if (!personProfileIds || personProfileIds.length === 0) {
    currentPlanTargets.value = {};
    return;
  }
  try {
    const response = await api.post('/calculate-nutritional-targets/', { person_profile_ids: personProfileIds });
    currentPlanTargets.value = response.data;
  } catch (error) {
    console.error('Error fetching plan nutritional targets:', error);
    currentPlanTargets.value = {};
  }
};

watch(() => planData.value.target_people_ids, (newVal) => {
  fetchPlanNutritionalTargets(newVal);
}, { deep: true, immediate: true });

const addComponentToPlan = (component) => {
  if (!component || !component.id) {
    console.error('Invalid component to add:', component);
    return;
  }
  const alreadyAdded = addedMealComponents.value.some(c => c.id === component.id);
  if (!alreadyAdded) {
    addedMealComponents.value.push(component);
  } else {
    console.warn('Component already added:', component.name);
  }
};

const removeComponentFromPlan = (componentId) => {
  addedMealComponents.value = addedMealComponents.value.filter(c => c.id !== componentId);
};

watch(addedMealComponents, (newComponents) => {
  planData.value.meal_component_ids = newComponents.map(c => c.id);
}, { deep: true });

</script>

<style scoped>
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
.added-components-list table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 10px;
}
.added-components-list th,
.added-components-list td {
  border: 1px solid var(--color-border);
  padding: 8px;
  text-align: left;
  color: var(--color-text);
}
.added-components-list th {
  background-color: var(--color-input-bg);
}
.remove-btn {
  background: transparent;
  border: none;
  color: var(--color-danger, #e74c3c);
  font-size: 1.2em;
  cursor: pointer;
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
</style> 