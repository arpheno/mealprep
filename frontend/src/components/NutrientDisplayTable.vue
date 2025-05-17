<template>
  <table class="nutritional-breakdown-table" :class="{ 'no-reference-table': tableConfig.isNoReferenceTable }">
    <thead>
      <tr>
        <th>Nutrient</th>
        <th>{{ tableConfig.colHeaderTotal }}</th>
        <th v-if="!tableConfig.isNoReferenceTable">{{ tableConfig.colHeaderRda }}</th>
        <th v-if="!tableConfig.isNoReferenceTable">{{ tableConfig.colHeaderUl }}</th>
      </tr>
    </thead>
    <template v-for="(nutrientsInGroup, groupName) in nutrientGroupsData" :key="groupName">
      <tbody v-if="Object.keys(nutrientsInGroup).length > 0" class="nutrient-group">
        <tr v-if="!tableConfig.isNoReferenceTable" class="nutrient-group-header">
          <th :colspan="tableConfig.isNoReferenceTable ? 2 : 4">{{ groupName }}</th>
        </tr>
        <tr
          v-for="(nutrientData, nutrientKey) in nutrientsInGroup"
          :key="nutrientKey"
          :style="displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number) && !tableConfig.isNoReferenceTable
            ? stylingFunctions.getMacroStyle(nutrientData)
            : stylingFunctions.getPlanNutrientBarStyle(nutrientData, planDurationDays)"
          class="nutrient-data-row"
        >
          <td>
            {{ nutrientKey }}
            <span @click="$emit('nutrient-drilldown', { nutrientKey, nutrientData })" class="drilldown-icon" title="View Sources">ℹ️</span>
          </td>
          <td class="nutrient-value-cell">
            {{ nutrientData.total.toFixed(displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number) ? 1 : 2) }} {{ nutrientData.unit }}
            <span v-if="!tableConfig.isNoReferenceTable && displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number) && nutrientData.percent_energy !== null && nutrientData.percent_energy !== undefined">
              ({{ nutrientData.percent_energy.toFixed(1) }}% E)
            </span>
          </td>
          <td v-if="!tableConfig.isNoReferenceTable" class="nutrient-value-cell">
            <span v-if="tableConfig.isOverallSummaryView && displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number) && nutrientData.fdc_nutrient_number === displayConstants.FDC_NUM_CARB">
                {{ displayConstants.TARGET_E_PERCENT_CARB.min }}-{{ displayConstants.TARGET_E_PERCENT_CARB.max }}% E
            </span>
            <span v-else-if="tableConfig.isOverallSummaryView && displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number) && nutrientData.fdc_nutrient_number === displayConstants.FDC_NUM_FAT">
                {{ displayConstants.TARGET_E_PERCENT_FAT.min }}-{{ displayConstants.TARGET_E_PERCENT_FAT.max }}% E
            </span>
            <span v-else-if="tableConfig.isOverallSummaryView && displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number) && nutrientData.fdc_nutrient_number === displayConstants.FDC_NUM_PROTEIN">
                {{ displayConstants.TARGET_E_PERCENT_PROTEIN.min }}-{{ displayConstants.TARGET_E_PERCENT_PROTEIN.max }}% E
            </span>
            <span v-else>
              {{ stylingFunctions.formatDRV(nutrientData.rda !== null ? nutrientData.rda * planDurationDays : null) }} {{ nutrientData.unit }}
            </span>
          </td>
          <td v-if="!tableConfig.isNoReferenceTable" class="nutrient-value-cell">
            <span v-if="displayConstants.MACRO_FDC_NUMBERS.includes(nutrientData.fdc_nutrient_number)">-</span>
            <span v-else>
              {{ stylingFunctions.formatDRV(nutrientData.ul !== null ? nutrientData.ul * planDurationDays : null) }} {{ nutrientData.unit }}
            </span>
          </td>
        </tr>
      </tbody>
    </template>
  </table>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

// Props define the data and configuration for this display table
defineProps({
  nutrientGroupsData: { // The actual { 'GroupName': { 'NutrientKey': {details...} }, ... }
    type: Object,
    required: true,
  },
  tableConfig: { // Configuration for table headers and specific logic
    type: Object,
    required: true,
    default: () => ({
      isNoReferenceTable: false,
      isOverallSummaryView: false,
      colHeaderTotal: 'Total',
      colHeaderRda: 'RDA',
      colHeaderUl: 'UL',
    })
  },
  planDurationDays: {
    type: Number,
    required: true,
  },
  stylingFunctions: { // Pass down imported styling utility functions
    type: Object,
    required: true, // { getMacroStyle, getPlanNutrientBarStyle, formatDRV }
  },
  displayConstants: { // Pass down imported display-related constants
    type: Object,
    required: true, // { MACRO_FDC_NUMBERS, FDC_NUM_CARB, etc. }
  }
});

const emit = defineEmits(['nutrient-drilldown']); // Define the event
</script>

<style scoped>
/* Styles for .nutritional-breakdown-table, .nutrient-group, .nutrient-group-header, 
   .nutrient-data-row, .nutrient-value-cell, and .no-reference-table 
   are assumed to be either global, inherited from NutritionalBreakdown.vue's parent (MealPlanForm),
   or defined in NutritionalBreakdown.vue itself. 
   This component focuses on the table structure.
   If these styles need to be specific here, they can be copied or moved.
*/
.nutritional-breakdown-table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 15px; /* Add some space between tables if multiple are used */
}

/* Style for .no-reference-table will be applied if tableConfig.isNoReferenceTable is true */
.no-reference-table .nutrient-data-row td {
  background-color: var(--color-background-mute); /* Muted background for these rows */
  color: var(--color-text-secondary); /* Muted text */
}
.no-reference-table .nutrient-group-header {
    display: none; /* No group headers for no-reference table */
}

.drilldown-icon {
  margin-left: 8px;
  cursor: pointer;
  font-size: 0.9em;
  color: var(--color-primary); /* Or any other suitable color */
}

.drilldown-icon:hover {
  opacity: 0.7;
}
</style> 