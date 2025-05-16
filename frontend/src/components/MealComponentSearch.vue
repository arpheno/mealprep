<template>
  <div class="component-search-section-wrapper">
    <h3>Add Meal Components</h3>
    <div class="component-search-section">
      <div class="form-group">
        <label for="component-filter">Filter Components:</label>
        <input
          type="text"
          id="component-filter"
          v-model="mealComponentSearchTerm"
          placeholder="Type to filter components..."
        />

        <div v-if="allMealComponents.length > 0 && !isLoading" class="component-tiles-container">
          <div
            v-for="component in filteredMealComponents"
            :key="component.id"
            class="component-tile"
            @click="selectComponent(component)"
            role="button"
            tabindex="0"
            @keydown.enter="selectComponent(component)"
            @keydown.space.prevent="selectComponent(component)"
            @mouseenter="showComponentTooltip($event, component)"
            @mouseleave="hideComponentTooltip"
            @mousemove="updateTooltipPosition($event)"
            @wheel="handleTileWheel($event, component)"
          >
            <span class="tile-name">{{ component.name }}</span>
            <span v-if="component.category_tag" class="tile-category">{{ component.category_tag }}</span>
            <span v-if="component.frequency" class="tile-frequency">{{ component.frequency }}</span>
          </div>
        </div>

        <p v-if="isLoading" class="info-message">Loading components...</p>
        <p v-if="searchedAndNoResults && mealComponentSearchTerm.length > 0 && !isLoading" class="no-results-message">
          No meal components match "{{ mealComponentSearchTerm }}".
        </p>
        <p v-if="allMealComponents.length === 0 && !isLoading && !fetchError" class="no-results-message">
          No meal components available. Create some first!
        </p>
        <p v-if="fetchError && !isLoading" class="error-message">
          Error loading components: {{ fetchError }}
        </p>
      </div>
    </div>
  </div>
  <MealComponentTooltip 
    ref="tooltipComponentRef" 
    :component="hoveredComponentDetail"
    v-if="tooltipVisible"
    :style="{ top: tooltipTop, left: tooltipLeft, position: 'fixed' }"
  />
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue';
import MealComponentTooltip from './MealComponentTooltip.vue';

const props = defineProps({
  allMealComponents: {
    type: Array,
    required: true,
    default: () => []
  },
  isLoading: {
    type: Boolean,
    default: false
  },
  fetchError: {
    type: String,
    default: null
  }
});

const emit = defineEmits(['component-selected']);

const mealComponentSearchTerm = ref('');

const filteredMealComponents = computed(() => {
  if (!mealComponentSearchTerm.value) {
    return props.allMealComponents;
  }
  const searchTermLower = mealComponentSearchTerm.value.toLowerCase();
  return props.allMealComponents.filter(component =>
    component.name.toLowerCase().includes(searchTermLower) ||
    (component.category_tag && component.category_tag.toLowerCase().includes(searchTermLower))
  );
});

const searchedAndNoResults = computed(() => {
  return mealComponentSearchTerm.value.length > 0 && filteredMealComponents.value.length === 0;
});

const selectComponent = (component) => {
  emit('component-selected', component);
};

const tooltipComponentRef = ref(null);
const hoveredComponentDetail = ref(null);
const tooltipVisible = ref(false);
const tooltipTop = ref('0px');
const tooltipLeft = ref('0px');
let hoverTimeout = null;

const showComponentTooltip = (event, component) => {
  clearTimeout(hoverTimeout);
  hoveredComponentDetail.value = component;
  updateTooltipPosition(event);
  tooltipVisible.value = true;
};

const hideComponentTooltip = () => {
  hoverTimeout = setTimeout(() => {
    tooltipVisible.value = false;
    hoveredComponentDetail.value = null;
  }, 100);
};

const updateTooltipPosition = (event) => {
  if (!tooltipVisible.value) return;
  const offsetX = 15;
  const offsetY = 15;
  let newLeft = event.clientX + offsetX;
  let newTop = event.clientY + offsetY;
  const tooltipEstimatedWidth = 300;
  const tooltipEstimatedHeight = 250;
  if (newLeft + tooltipEstimatedWidth > window.innerWidth) {
    newLeft = event.clientX - tooltipEstimatedWidth - offsetX;
  }
  if (newTop + tooltipEstimatedHeight > window.innerHeight) {
    newTop = event.clientY - tooltipEstimatedHeight - offsetY;
  }
  if (newLeft < 0) newLeft = 0;
  if (newTop < 0) newTop = 0;
  tooltipLeft.value = `${newLeft}px`;
  tooltipTop.value = `${newTop}px`;
};

const handleTileWheel = (event, componentData) => {
  if (tooltipVisible.value && hoveredComponentDetail.value && hoveredComponentDetail.value.id === componentData.id) {
    if (tooltipComponentRef.value && tooltipComponentRef.value.scrollContent) {
      const scrollHandledByTooltip = tooltipComponentRef.value.scrollContent(event.deltaY);
      if (scrollHandledByTooltip) {
        event.preventDefault();
      }
    }
  }
};
</script>

<style scoped>
/* Styles previously in MealPlanForm.vue for this section */
.component-search-section-wrapper h3 {
  color: var(--color-text);
  margin-top: 10px; /* Or adjust as needed */
  margin-bottom: 10px;
}

.component-search-section {
  border: 1px solid var(--color-border);
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
  background-color: var(--color-background-soft);
}

/* Assuming .form-group styles are available globally or redefine if needed */
.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 5px;
  font-weight: bold;
  color: var(--color-text);
}

.form-group input[type="text"] {
  padding: 10px;
  border: 1px solid var(--color-input-border);
  border-radius: 4px;
  font-size: 1em;
  background-color: var(--color-input-bg);
  color: var(--color-text);
  margin-bottom: 15px; /* Space before tiles */
}

.form-group input[type="text"]:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb, 66, 185, 131), 0.3);
}

.component-tiles-container {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  /* margin-top: 15px; Already handled by input margin-bottom */
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

.component-tile:hover,
.component-tile:focus {
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

.tile-category,
.tile-frequency {
  font-size: 0.8em;
  color: var(--color-text-secondary);
  background-color: var(--color-background-mute);
  padding: 2px 6px;
  border-radius: 3px;
  margin-top: 4px;
}

.no-results-message,
.info-message,
.error-message[data-v-e91b2f44] { /* Ensure specificity if this was from MealPlanForm */
  padding: 10px;
  color: var(--color-text-secondary);
  font-style: italic;
  margin-top: 10px;
  text-align: center;
  width: 100%;
}

.error-message {
    color: var(--color-danger, #e74c3c);
}
</style> 