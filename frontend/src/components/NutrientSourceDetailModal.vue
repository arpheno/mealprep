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
      <div v-else-if="!sankeyOption || !sankeyOption.series || sankeyOption.series.length === 0 || sankeyOption.series[0].data.length === 0 || sankeyOption.series[0].links.length === 0">
        No significant sources found for this nutrient, or not enough data to display chart. Check console for details.
      </div>
      <div v-else class="sankey-chart-container">
        <v-chart 
          class="chart" 
          :option="sankeyOption" 
          :key="sankeyChartKey" 
          autoresize
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, ref, watch, computed } from 'vue';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { SankeyChart } from 'echarts/charts';
import { TooltipComponent, TitleComponent, LegendComponent } from 'echarts/components';
import VChart, { THEME_KEY } from 'vue-echarts';
import { provide } from 'vue';

use([
  CanvasRenderer,
  SankeyChart,
  TooltipComponent,
  TitleComponent,
  LegendComponent
]);

provide(THEME_KEY, 'light');

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
const sankeyChartKey = ref(0); // Key for forcing re-render

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

watch(() => [props.nutrientDetail, props.planItemsData, props.activeView], (newValues) => {
  console.log('[SankeyModal] Watch triggered. NutrientDetail:', newValues[0], 'PlanItemsData:', newValues[1], 'ActiveView:', newValues[2]);
  if (!props.nutrientDetail || !props.planItemsData) {
    console.log('[SankeyModal] Watch: NutrientDetail or PlanItemsData is null/empty. Clearing processedSources.');
    processedSources.value = [];
    sankeyChartKey.value++; // Increment key to force re-render if chart was previously shown
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
    const component = planItem.component;
    if (!component || !component.ingredientusage_set) {
      console.warn('[SankeyModal] Watch: Skipping planItem due to missing component or ingredientusage_set', planItem);
      return;
    }

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
  console.log('[SankeyModal] Watch: Calculated processedSources:', JSON.parse(JSON.stringify(sources)));
  processedSources.value = sources;
  sankeyChartKey.value++; // Increment key to force re-render
  loading.value = false;
}, { immediate: true, deep: true });

const sankeyOption = computed(() => {
  console.log('[SankeyModal] Computing sankeyOption. NutrientDetail:', props.nutrientDetail, 'ProcessedSources:', processedSources.value);

  if (!props.nutrientDetail) {
    console.log('[SankeyModal] sankeyOption: No nutrientDetail. Returning null.');
    return null;
  }
  if (processedSources.value.length === 0 && props.nutrientDetail.total <= 0.001) {
     console.log('[SankeyModal] sankeyOption: No processed sources and total is negligible. Returning null.');
    return null;
  }

  const nodes = [];
  const links = [];
  const nodeSet = new Set();

  // Add the main nutrient node (source of everything)
  const nutrientNodeName = `${props.nutrientDetail.key}`;
  if (!nodeSet.has(nutrientNodeName)) {
    nodes.push({ name: nutrientNodeName });
    nodeSet.add(nutrientNodeName);
  }

  let totalFromProcessedSources = 0;
  processedSources.value.forEach(source => totalFromProcessedSources += source.amount);
  
  console.log(`[SankeyModal] sankeyOption: Total from processed sources: ${totalFromProcessedSources}, NutrientDetail total: ${props.nutrientDetail.total}`);

  // Case 1: No processed sources, but there is a total for the nutrient.
  // Attribute this to "Other/Unspecified Sources".
  if (processedSources.value.length === 0 && props.nutrientDetail.total > 0.001) {
    console.log('[SankeyModal] sankeyOption: No processed sources, but nutrientDetail.total > 0. Adding "Other/Unspecified Sources" link.');
    const otherNodeName = "Other/Unspecified Sources";
    if (!nodeSet.has(otherNodeName)) {
        nodes.push({ name: otherNodeName });
        nodeSet.add(otherNodeName);
    }
    links.push({
        source: nutrientNodeName,
        target: otherNodeName,
        value: props.nutrientDetail.total // Link value is the total nutrient amount
    });
  } else {
    // Case 2: We have processed sources. Build the Sankey from these.
    // Aggregate links from Nutrient (overall total) to each Meal Component
    const componentContributions = {};
    processedSources.value.forEach(source => {
      if (!componentContributions[source.componentName]) {
        componentContributions[source.componentName] = 0;
      }
      componentContributions[source.componentName] += source.amount;

      // Add component node if not present
      if (!nodeSet.has(source.componentName)) {
        nodes.push({ name: source.componentName });
        nodeSet.add(source.componentName);
      }

      // Add ingredient node (uniquely named) if not present
      const uniqueIngredientNodeName = `${source.ingredientName} (from ${source.componentName.substring(0,10)}${source.componentName.length > 10 ? '...' : ''})`;
      if (!nodeSet.has(uniqueIngredientNodeName)) {
          nodes.push({ name: uniqueIngredientNodeName });
          nodeSet.add(uniqueIngredientNodeName);
      }
    });

    // Create links: Nutrient -> Meal Component
    for (const compName in componentContributions) {
      if (componentContributions[compName] > 0.001) {
        links.push({
          source: nutrientNodeName,
          target: compName,
          value: componentContributions[compName]
        });
      }
    }

    // Create links: Meal Component -> Ingredient
    processedSources.value.forEach(source => {
      const componentNodeName = source.componentName;
      const uniqueIngredientNodeName = `${source.ingredientName} (from ${source.componentName.substring(0,10)}${source.componentName.length > 10 ? '...' : ''})`;
      if (source.amount > 0.001) {
        links.push({
          source: componentNodeName,
          target: uniqueIngredientNodeName,
          value: source.amount
        });
      }
    });
    
    // If there's a discrepancy between sum of processed sources and nutrientDetail.total, add "Other"
    const discrepancy = props.nutrientDetail.total - totalFromProcessedSources;
    console.log(`[SankeyModal] sankeyOption: Discrepancy between nutrient total and sum of sources: ${discrepancy}`);
    if (discrepancy > 0.001) {
        console.log('[SankeyModal] sankeyOption: Adding link for discrepancy to "Other/Unspecified Sources".');
        const otherNodeName = "Other/Unspecified Sources";
        if (!nodeSet.has(otherNodeName)) {
            nodes.push({ name: otherNodeName });
            nodeSet.add(otherNodeName);
        }
        links.push({
            source: nutrientNodeName,
            target: otherNodeName,
            value: discrepancy
        });
    }
  }

  console.log('[SankeyModal] sankeyOption: Generated nodes:', JSON.parse(JSON.stringify(nodes)));
  console.log('[SankeyModal] sankeyOption: Generated links:', JSON.parse(JSON.stringify(links)));

  if (nodes.length === 0 || links.length === 0) {
    console.log('[SankeyModal] sankeyOption: No nodes or links generated. Returning null.');
    return null;
  }
  
  const option = {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove',
      formatter: (params) => {
        if (params.dataType === 'edge') {
          return `${params.data.source} → ${params.data.target}: ${params.data.value.toFixed(2)} ${props.nutrientDetail.unit}`;
        }
        if (params.dataType === 'node') {
          return `${params.name}`; // Could add total value if it's an end node or a component node
        }
        return '';
      }
    },
    series: [
      {
        type: 'sankey',
        data: nodes,
        links: links,
        emphasis: {
          focus: 'adjacency'
        },
        lineStyle: {
          color: 'gradient',
          curveness: 0.5
        },
        label: {
          show: true,
          position: 'right',
          formatter: (params) => {
            if (params.value === undefined || params.value === null) {
                return params.name; // Should not happen for Sankey nodes with values
            }
            // For the main nutrient node, its value is the grand total.
            // For other nodes, params.value is the sum of relevant links.
            return `${params.name}\n${params.value.toFixed(2)} ${props.nutrientDetail.unit}`;
          },
          textStyle: { 
            fontSize: 12,
            color: '#E0E0E0'
          },
          textBorderColor: 'transparent',
          textBorderWidth: 0
        },
        nodeAlign: 'justify', 
        draggable: true, 
        layoutIterations: 64, // Slightly more iterations for potentially complex layouts
        nodeGap: 12, // Increased node gap slightly
        nodeWidth: 20, // Explicitly set node width
        levels: [ // Example: Custom styling for levels
          {
            depth: 0, // Nutrient node
            itemStyle: { color: '#5470c6' }, // Blue
            lineStyle: { color: 'source', opacity: 0.6 }
          },
          {
            depth: 1, // Meal Component nodes
            itemStyle: { color: '#91cc75' }, // Green
            lineStyle: { color: 'source', opacity: 0.5 }
          },
          {
            depth: 2, // Ingredient nodes
            itemStyle: { color: '#fac858' }, // Yellow
            lineStyle: { color: 'source', opacity: 0.4 }
          },
          { // For "Other/Unspecified Sources" if it appears at any level
            label: { position: 'left' }, // Put label on left for terminal nodes like this
            itemStyle: { color: '#ee6666' } // Red
          }
        ]
      }
    ]
  };
  console.log('[SankeyModal] sankeyOption: Final chart option:', JSON.parse(JSON.stringify(option)));
  return option;
});

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
  min-width: 750px; /* Increased min-width */
  max-width: 95%; 
  min-height: 550px; /* Increased min-height */
  max-height: 90vh; 
  overflow-y: auto;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  position: relative;
  color: var(--color-text);
  display: flex; 
  flex-direction: column;
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
  text-align: center;
}

.nutrient-total-summary {
  margin-bottom: 15px; 
  font-size: 1.1em;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
  text-align: center;
}

.sankey-chart-container {
  flex-grow: 1; 
  width: 100%;
  min-height: 500px; /* Increased container min-height */
  /* border: 1px dashed #ccc; Removed diagnostic border */
}

.chart {
  height: 500px; /* Explicit height, matching container's min-height */
  width: 100%;
  /* border: 1px solid red; Removed diagnostic border */
}

.modal-content div[v-else-if] { /* Target for loading/no data message */
  text-align: center;
  padding: 20px;
  color: var(--color-text-secondary);
  flex-grow: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-style: italic;
}
</style> 