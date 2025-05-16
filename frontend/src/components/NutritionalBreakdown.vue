<template>
  <div v-if="overallSummaryWithRef.hasData || perPersonBreakdownWithRef.hasData" class="nutritional-breakdown-section plan-breakdown">
    <h3>Live Plan Nutritional Breakdown (for {{ planDurationDays }} days)</h3>

    <div class="breakdown-tabs">
      <button
        type="button"
        :class="{'active': activeViewInternal === 'overall'}"
        @click="setActiveView('overall')"
      >
        Overall Summary
      </button>
      <button
        type="button"
        v-for="person in selectedPeople"
        :key="person.id"
        :class="{'active': activeViewInternal === person.id}"
        @click="setActiveView(person.id)"
      >
        {{ person.name }}
      </button>
    </div>

    <!-- Overall Summary -->
    <div v-if="activeViewInternal === 'overall'" class="breakdown-content overall-breakdown-content">
      <h4>Overall Plan Summary</h4>
      <NutrientDisplayTable
        v-if="overallSummaryWithRef.hasData"
        :nutrientGroupsData="overallSummaryWithRef.data"
        :tableConfig="overallTableConfig"
        :planDurationDays="planDurationDays"
        :stylingFunctions="stylingUtils"
        :displayConstants="nutritionConsts"
      />
      <div v-if="overallSummaryNoRef.hasData" class="no-reference-values-section">
        <h5 class="no-reference-table-title">Other Components (No RDA/UL specified)</h5>
        <NutrientDisplayTable
          :nutrientGroupsData="overallSummaryNoRef.data"
          :tableConfig="noRefTableConfig"
          :planDurationDays="planDurationDays"
          :stylingFunctions="stylingUtils"
          :displayConstants="nutritionConsts"
        />
      </div>
    </div>

    <!-- Per-Person Breakdown -->
    <div v-else-if="activeViewInternal && perPersonBreakdownWithRef.data[activeViewInternal]" class="breakdown-content person-breakdown-content">
      <h4 v-if="perPersonBreakdownWithRef.data[activeViewInternal]">
          Nutritional Breakdown for {{ perPersonBreakdownWithRef.data[activeViewInternal].personName }}
      </h4>
      <NutrientDisplayTable
        v-if="perPersonBreakdownWithRef.data[activeViewInternal].hasData"
        :nutrientGroupsData="perPersonBreakdownWithRef.data[activeViewInternal].nutrientGroups"
        :tableConfig="perPersonTableConfig"
        :planDurationDays="planDurationDays"
        :stylingFunctions="stylingUtils"
        :displayConstants="nutritionConsts"
      />
      <div v-if="perPersonBreakdownNoRef.data[activeViewInternal] && perPersonBreakdownNoRef.data[activeViewInternal].hasData" class="no-reference-values-section">
        <h5 class="no-reference-table-title">Other Components (No RDA/UL specified)</h5>
        <NutrientDisplayTable
          :nutrientGroupsData="perPersonBreakdownNoRef.data[activeViewInternal].nutrientGroups"
          :tableConfig="noRefTableConfig"
          :planDurationDays="planDurationDays"
          :stylingFunctions="stylingUtils"
          :displayConstants="nutritionConsts"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, watch, computed } from 'vue';
import NutrientDisplayTable from './NutrientDisplayTable.vue'; // Import the new component
import * as stylingUtils from '../utils/nutritionDisplayUtils.js';
import * as nutritionConsts from '../utils/nutritionConstants.js';

const props = defineProps({
  breakdownData: {
    type: Object,
    required: true,
    default: () => ({ overallSummary: {}, perPersonBreakdown: {} })
  },
  activeView: {
    type: [String, Number],
    required: true
  },
  selectedPeople: {
    type: Array,
    required: true,
    default: () => []
  },
  planDurationDays: {
    type: Number,
    required: true,
    default: 7
  }
});

const emit = defineEmits(['update:activeView']);
const activeViewInternal = ref(props.activeView);

watch(() => props.activeView, (newVal) => {
  activeViewInternal.value = newVal;
});

const setActiveView = (viewId) => {
  activeViewInternal.value = viewId;
  emit('update:activeView', viewId);
};

// Helper function to filter nutrient groups
const filterNutrientGroups = (sourceGroups, excludeNoRef) => {
  if (!sourceGroups) return { data: {}, hasData: false };
  const filtered = {};
  let hasData = false;
  for (const groupName in sourceGroups) {
    if (excludeNoRef && groupName === 'NoReferenceValues') continue;
    if (!excludeNoRef && groupName !== 'NoReferenceValues') continue;
    if (Object.keys(sourceGroups[groupName]).length > 0) {
      filtered[groupName] = sourceGroups[groupName];
      hasData = true;
    }
  }
  return { data: filtered, hasData };
};

// Computed properties to prepare data for NutrientDisplayTable
const overallSummaryWithRef = computed(() => filterNutrientGroups(props.breakdownData.overallSummary, true));
const overallSummaryNoRef = computed(() => filterNutrientGroups(props.breakdownData.overallSummary, false));

const perPersonBreakdownWithRef = computed(() => {
  const result = { data: {}, hasData: false };
  if (!props.breakdownData.perPersonBreakdown) return result;
  for (const personId in props.breakdownData.perPersonBreakdown) {
    const personData = props.breakdownData.perPersonBreakdown[personId];
    const filtered = filterNutrientGroups(personData.nutrientGroups, true);
    result.data[personId] = {
      personName: personData.personName,
      nutrientGroups: filtered.data,
      hasData: filtered.hasData
    };
    if (filtered.hasData) result.hasData = true;
  }
  return result;
});

const perPersonBreakdownNoRef = computed(() => {
  const result = { data: {}, hasData: false };
  if (!props.breakdownData.perPersonBreakdown) return result;
  for (const personId in props.breakdownData.perPersonBreakdown) {
    const personData = props.breakdownData.perPersonBreakdown[personId];
    const filtered = filterNutrientGroups(personData.nutrientGroups, false);
    result.data[personId] = {
      personName: personData.personName,
      nutrientGroups: filtered.data,
      hasData: filtered.hasData
    };
    if (filtered.hasData) result.hasData = true;
  }
  return result;
});

// Table configurations
const overallTableConfig = computed(() => ({
  isNoReferenceTable: false,
  isOverallSummaryView: true,
  colHeaderTotal: 'Total for Plan',
  colHeaderRda: `Target RDA (for ${props.planDurationDays} ${props.planDurationDays === 1 ? 'day' : 'days'})`,
  colHeaderUl: `Target UL (for ${props.planDurationDays} ${props.planDurationDays === 1 ? 'day' : 'days'})`,
}));

const perPersonTableConfig = computed(() => ({
  isNoReferenceTable: false,
  isOverallSummaryView: false,
  colHeaderTotal: 'Your Total',
  colHeaderRda: `Your RDA (for ${props.planDurationDays} ${props.planDurationDays === 1 ? 'day' : 'days'})`,
  colHeaderUl: `Your UL (for ${props.planDurationDays} ${props.planDurationDays === 1 ? 'day' : 'days'})`,
}));

const noRefTableConfig = {
  isNoReferenceTable: true,
  isOverallSummaryView: false, // Does not apply, but set to avoid issues
  colHeaderTotal: 'Total for Plan', // For overall
                                  // For per-person, it will be 'Your Total' - handled by context if needed, or make dynamic
};

</script>

<style scoped>
/* Styles from the original NutritionalBreakdown.vue */
.nutritional-breakdown-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
}

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

.no-reference-values-section {
  margin-top: 15px;
  padding-top: 15px;
  border-top: 1px dashed var(--color-border-hover);
}
.no-reference-table-title {
  font-size: 0.95em;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  font-weight: bold;
}

/* General table styles that were in MealPlanForm.vue and might be needed if not global */
/* These are now also present in NutrientDisplayTable.vue, consider where to keep them for DRY principle */
:global(.nutritional-breakdown-table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 15px;
}
:global(.nutritional-breakdown-table th),
:global(.nutritional-breakdown-table td) {
  border: 1px solid var(--color-border);
  padding: 8px;
  text-align: left;
  color: var(--color-text);
}
:global(.nutritional-breakdown-table th) {
  background-color: var(--color-input-bg);
}
:global(.nutrient-group) {
  /* background-color: var(--color-background-soft); optional, can make groups distinct */
}
:global(.nutrient-group-header th) { /* Target th directly inside this specific header row */
  background-color: var(--color-input-bg);
  font-weight: bold;
}
:global(.nutrient-data-row) {
  /* background-color: var(--color-background); default row color */
}
:global(.nutrient-value-cell) {
  text-align: right;
}

/* Specifically for no-reference-table styling from NutrientDisplayTable, if using :global */
:global(.no-reference-table .nutrient-data-row td) {
  background-color: var(--color-background-mute) !important; /* Ensure override if needed */
  color: var(--color-text-secondary) !important;
}
:global(.no-reference-table .nutrient-group-header) {
    display: none !important;
}
</style> 