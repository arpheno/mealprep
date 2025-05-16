<template>
  <div class="meal-component-tooltip" v-if="component">
    <h4>{{ component.name }} - Details</h4>
    
    <div class="tooltip-section">
      <h5>Ingredients:</h5>
      <ul ref="ingredientsListEl" v-if="component.ingredient_links && component.ingredient_links.length">
        <li v-for="link in component.ingredient_links" :key="link.ingredient_id">
          {{ link.ingredient_name }}: {{ formatQuantity(link.quantity) }} {{ link.measurement_unit_name }}
        </li>
      </ul>
      <p v-else>No ingredients listed.</p>
    </div>

    <div class="tooltip-section">
      <h5>Nutritional Contribution (per serving of component):</h5>
      <ul ref="nutrientsListEl" v-if="component.nutritional_totals && Object.keys(component.nutritional_totals).length">
        <li v-for="(nutrientData, nutrientKey) in component.nutritional_totals" :key="nutrientKey">
          {{ formatNutrientKey(nutrientKey) }}: {{ formatNutrientAmount(nutrientData.amount) }} {{ nutrientData.unit }}
        </li>
      </ul>
      <p v-else>No nutritional data available.</p>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineExpose, ref } from 'vue';

// eslint-disable-next-line no-unused-vars
const props = defineProps({
  component: {
    type: Object,
    default: null
  }
});

const ingredientsListEl = ref(null);
const nutrientsListEl = ref(null);

const scrollContent = (deltaY) => {
  // Prioritize scrolling the nutrients list if it's scrollable, then ingredients.
  // A list is scrollable if its scrollHeight is greater than its clientHeight.
  if (nutrientsListEl.value && (nutrientsListEl.value.scrollHeight > nutrientsListEl.value.clientHeight)) {
    nutrientsListEl.value.scrollTop += deltaY;
    return true; // Indicate that scroll was handled
  } else if (ingredientsListEl.value && (ingredientsListEl.value.scrollHeight > ingredientsListEl.value.clientHeight)) {
    ingredientsListEl.value.scrollTop += deltaY;
    return true; // Indicate that scroll was handled
  }
  return false; // Indicate no scrollable content in tooltip handled this
};

defineExpose({ scrollContent });

const formatQuantity = (value) => {
  if (value === null || value === undefined) return 'N/A';
  const num = parseFloat(value);
  if (isNaN(num)) return value; // Return original if not a number after all
  // Show up to 2 decimal places, but only if necessary
  return Number(num.toFixed(2)); 
};

const formatNutrientAmount = (value) => {
  if (value === null || value === undefined) return 'N/A';
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return Number(num.toFixed(2)); 
};

const formatNutrientKey = (key) => {
  // Extracts the nutrient name if it's in "Name (unit)" format
  const match = key.match(/^(.*?)(?:\s*\([^)]*\))?$/);
  return match && match[1] ? match[1].trim() : key;
};

</script>

<style scoped>
.meal-component-tooltip {
  position: absolute;
  background-color: var(--color-background-soft, #f9f9f9);
  border: 1px solid var(--color-border, #ccc);
  border-radius: 8px;
  padding: 15px;
  width: 300px; /* Adjust as needed */
  max-width: 90vw;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000; /* Ensure it's on top */
  font-size: 0.9em;
  color: var(--color-text);
}

.meal-component-tooltip h4 {
  margin-top: 0;
  margin-bottom: 10px;
  color: var(--color-heading);
  font-size: 1.1em;
  border-bottom: 1px solid var(--color-border-hover);
  padding-bottom: 5px;
}

.meal-component-tooltip h5 {
  margin-top: 10px;
  margin-bottom: 5px;
  color: var(--color-text-secondary);
  font-size: 1em;
}

.tooltip-section {
  margin-bottom: 10px;
}

.tooltip-section ul {
  list-style-type: none;
  padding-left: 0;
  margin: 0;
  max-height: 220px; /* Increased from 150px */
  overflow-y: auto;
}

.tooltip-section li {
  padding: 3px 0;
  border-bottom: 1px solid var(--color-border-hover-light, #eee);
}

.tooltip-section li:last-child {
  border-bottom: none;
}

.tooltip-section p {
  font-style: italic;
  color: var(--color-text-secondary);
}
</style> 