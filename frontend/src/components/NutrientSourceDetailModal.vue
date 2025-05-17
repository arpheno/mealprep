<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <button class="close-button" @click="$emit('close')">&times;</button>
      <h3 v-if="nutrientDetail">Nutrient Source Breakdown: {{ nutrientDetail.key }}</h3>
      <div v-if="nutrientDetail" class="nutrient-total-summary">
        Total in Plan {{ activeView === 'overall' ? '' : 'for ' + personName(activeView) }}:
        <strong>{{ nutrientDetail.total.toFixed(2) }} {{ nutrientDetail.unit }}</strong>
         (for {{ planDurationDays }} {{ planDurationDays === 1 ? 'day' : 'days' }})
      </div>

      <div v-if="loading">Loading breakdown...</div>
      <div v-else-if="processedSources.length === 0">No significant sources found for this nutrient in the current view.</div>
      <div v-else class="sources-table-container">
        <table>
          <thead>
            <tr>
              <th>Meal Component</th>
              <th>Ingredient</th>
              <th>Contribution ({{ nutrientDetail.unit }})</th>
              <th>% of Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(source, index) in processedSources" :key="index">
              <td>{{ source.componentName }}</td>
              <td>{{ source.ingredientName }}</td>
              <td>{{ source.amount.toFixed(2) }}</td>
              <td>{{ source.percentage.toFixed(1) }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, computed, watch } from 'vue';

const props = defineProps({
  nutrientDetail: { // { key: 'Nutrient Name (unit)', total: Number, unit: String, fdc_nutrient_number: String, ... }
    type: Object,
    default: null
  },
  planItemsData: { // Array of meal components in the plan (MealPlan.plan_items from backend, which are MealPlanItem instances)
                  // Each item should have: meal_component_detail (which has ingredientusage_set with scaled_nutrient_contributions)
                  // and assigned_people_ids
    type: Array,
    default: () => []
  },
  activeView: { // 'overall' or a person ID
    type: [String, Number],
    required: true
  },
  selectedPeople: { // Array of person objects {id, name, ...}
    type: Array,
    default: () => []
  },
  planDurationDays: {
      type: Number,
      required: true
  }
});

defineEmits(['close']);

const loading = ref(false);
const processedSources = ref([]);

const personName = (personId) => {
  const person = props.selectedPeople.find(p => p.id === personId);
  return person ? person.name : 'Selected User';
};

const getFrequencyMultiplier = (componentFrequency) => {
    const duration = props.planDurationDays || 7;
    const servingsPerDayPerPerson = 1; // This might need to come from planData if it varies

    if (componentFrequency === 'PER_BOX') return duration * servingsPerDayPerPerson;
    if (componentFrequency === 'DAILY') return duration;
    if (componentFrequency === 'WEEKLY') return duration / 7.0;
    return 1; // Default (e.g., ONE_TIME_CONSUMPTION or if frequency not set)
};

watch(() => [props.nutrientDetail, props.planItemsData, props.activeView], () => {
  if (!props.nutrientDetail || !props.planItemsData) {
    processedSources.value = [];
    return;
  }
  loading.value = true;
  const sources = [];
  const targetFdcNumber = props.nutrientDetail.fdc_nutrient_number;
  // nutrientDetail.key is "Nutrient Name (Unit)", nutrientDetail.unit is "Unit"
  const targetNutrientName = props.nutrientDetail.key.replace(` (${props.nutrientDetail.unit})`, '').toLowerCase();

  // Calculate total amount for percentage calculation, considering the active view
  let totalAmountForContext = props.nutrientDetail.total;

  props.planItemsData.forEach(planItem => {
    const component = planItem.meal_component_detail;
    if (!component || !component.ingredientusage_set) return;

    const frequencyMultiplier = getFrequencyMultiplier(component.frequency);

    let isComponentRelevantForView = false;
    let numPeopleSharingComponent = 1;

    if (props.activeView === 'overall') {
      isComponentRelevantForView = true;
      // For overall, if multiple people are assigned, the total contribution of the component instance is what matters.
      // The component.nutritional_totals already reflect this (summed for all its servings based on frequency).
      // Here, we are breaking it down by ingredient within that total component contribution.
    } else {
      // Per-person view: component must be assigned to this person
      if (planItem.assigned_people_ids && planItem.assigned_people_ids.includes(props.activeView)) {
        isComponentRelevantForView = true;
        numPeopleSharingComponent = planItem.assigned_people_ids.length > 0 ? planItem.assigned_people_ids.length : 1;
      }
    }

    if (!isComponentRelevantForView) return;

    component.ingredientusage_set.forEach(usage => {
      if (!usage.scaled_nutrient_contributions) return;
      
      usage.scaled_nutrient_contributions.forEach(contribution => {
        const matchesFdc = targetFdcNumber && contribution.fdc_nutrient_number === targetFdcNumber;
        const matchesName = !targetFdcNumber && contribution.nutrient_name.toLowerCase() === targetNutrientName && contribution.nutrient_unit === props.nutrientDetail.unit;
        
        if (matchesFdc || matchesName) {
          let amount = contribution.scaled_amount * frequencyMultiplier; // Amount from this ingredient for one serving of component, scaled by freq

          if (props.activeView !== 'overall') {
            amount /= numPeopleSharingComponent; // Divide by people sharing if per-person view
          }
          
          if (amount > 0.001) { // Only add if contribution is somewhat significant
            sources.push({
              componentName: component.name,
              ingredientName: usage.ingredient_name,
              amount: amount,
              percentage: totalAmountForContext > 0 ? (amount / totalAmountForContext) * 100 : 0,
            });
          }
        }
      });
    });
  });

  // Sort by amount descending
  sources.sort((a, b) => b.amount - a.amount);
  processedSources.value = sources;
  loading.value = false;
}, { immediate: true, deep: true });

</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background-color: var(--color-background-soft, #fff);
  padding: 25px;
  border-radius: 8px;
  min-width: 500px;
  max-width: 90%;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  position: relative;
  color: var(--color-text);
}

.close-button {
  position: absolute;
  top: 10px;
  right: 10px;
  background: none;
  border: none;
  font-size: 1.8em;
  cursor: pointer;
  color: var(--color-text-secondary);
}
.close-button:hover {
    color: var(--color-danger);
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: var(--color-heading);
}

.nutrient-total-summary {
  margin-bottom: 20px;
  font-size: 1.1em;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
}

.sources-table-container {
  margin-top: 15px;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  border: 1px solid var(--color-border);
  padding: 10px 12px;
  text-align: left;
}

th {
  background-color: var(--color-input-bg);
  font-weight: bold;
}

tbody tr:nth-child(odd) {
  background-color: var(--color-background);
}

tbody tr:hover {
  background-color: var(--color-background-mute);
}

</style> 