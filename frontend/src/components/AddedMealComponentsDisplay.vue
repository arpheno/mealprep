<template>
  <div v-if="addedMealComponents && addedMealComponents.length > 0" class="added-components-section">
    <h4>Added Meal Components:</h4>
    <div class="added-components-tiles-container">
      <div 
        v-for="itemInPlan in addedMealComponents" 
        :key="itemInPlan.id" 
        class="added-component-tile"
        @mouseenter="showComponentTooltip($event, itemInPlan.component)"
        @mouseleave="hideComponentTooltip"
        @mousemove="updateTooltipPosition($event)"
        @wheel="handleTileWheel($event, itemInPlan.component)"
      >
        <button 
          type="button" 
          @click="$emit('remove-component', itemInPlan.component.id)" 
          class="remove-component-btn" 
          title="Remove component from plan"
        >
          &times;
        </button>
        <button 
          type="button" 
          @click="$emit('edit-component', itemInPlan.component)" 
          class="edit-component-btn" 
          title="Edit component"
        >
          Edit
        </button>
        <div class="component-tile-header">
          <span class="tile-name">{{ itemInPlan.component.name }}</span>
        </div>
        <div class="component-tile-details">
          <span v-if="itemInPlan.component.category_tag" class="tile-category">{{ itemInPlan.component.category_tag }}</span>
          <span v-if="itemInPlan.component.frequency" class="tile-frequency">{{ itemInPlan.component.frequency }}</span>
        </div>
        
        <div class="person-assignment-section">
          <h5>Assign to:</h5>
          <div v-if="selectedPeopleInPlan.length > 0" class="person-assignment-checkboxes">
            <label v-for="person in selectedPeopleInPlan" :key="person.id" class="person-checkbox-label">
              <input 
                type="checkbox" 
                :value="person.id" 
                :checked="itemInPlan.assigned_people_ids.includes(person.id)"
                @change="togglePersonAssignment(itemInPlan, person.id)"
              />
              {{ person.name }}
            </label>
          </div>
          <p v-else class="no-people-in-plan-message">Add people to the plan to assign components.</p>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="empty-added-components-section">
      <p>No meal components added to the plan yet. Select components from the list above.</p>
  </div>

  <MealComponentTooltip 
    ref="tooltipComponentRef" 
    :component="hoveredComponentDetail"
    v-if="tooltipVisible"
    :style="{ top: tooltipTop, left: tooltipLeft, position: 'fixed' }"
  />
</template>

<script setup>
import { defineProps, defineEmits, ref } from 'vue';
import MealComponentTooltip from './MealComponentTooltip.vue';

// eslint-disable-next-line no-unused-vars
const props = defineProps({
  addedMealComponents: {
    type: Array,
    required: true,
    default: () => []
  },
  selectedPeopleInPlan: {
    type: Array,
    required: true,
    default: () => []
  }
});

const emit = defineEmits(['remove-component', 'update:assignment', 'edit-component']);

const togglePersonAssignment = (itemInPlan, personId) => {
  const currentAssignments = [...itemInPlan.assigned_people_ids];
  const personIndex = currentAssignments.indexOf(personId);
  
  if (personIndex > -1) {
    currentAssignments.splice(personIndex, 1); // Remove if already assigned
  } else {
    currentAssignments.push(personId); // Add if not assigned
  }
  emit('update:assignment', { itemInPlanId: itemInPlan.id, newAssignedIds: currentAssignments });
};

// Tooltip related refs
const tooltipComponentRef = ref(null); // Ref for the tooltip component instance
const hoveredComponentDetail = ref(null);
const tooltipVisible = ref(false);
const tooltipTop = ref('0px');
const tooltipLeft = ref('0px');
let hoverTimeout = null;

const showComponentTooltip = (event, component) => {
  clearTimeout(hoverTimeout); // Clear any existing timeout to hide
  hoveredComponentDetail.value = component;
  updateTooltipPosition(event);
  tooltipVisible.value = true;
};

const hideComponentTooltip = () => {
  // Delay hiding to allow mouse to move into the tooltip if needed, though for this simple case, direct hide is fine.
  hoverTimeout = setTimeout(() => {
      tooltipVisible.value = false;
      hoveredComponentDetail.value = null;
  }, 100); // Small delay before hiding
};

const updateTooltipPosition = (event) => {
  if (!tooltipVisible.value) return; // Don't update if not visible or about to become visible
  // Position tooltip slightly offset from the mouse pointer
  // Consider viewport boundaries to prevent tooltip from going off-screen
  const offsetX = 15; // Offset from mouse pointer X
  const offsetY = 15; // Offset from mouse pointer Y
  
  let newLeft = event.clientX + offsetX;
  let newTop = event.clientY + offsetY;

  // Basic boundary check (assumes tooltip width around 300px, height around 200-300px)
  // This needs to be more robust if the tooltip size varies greatly.
  const tooltipEstimatedWidth = 300; 
  const tooltipEstimatedHeight = 250; 

  if (newLeft + tooltipEstimatedWidth > window.innerWidth) {
    newLeft = event.clientX - tooltipEstimatedWidth - offsetX;
  }
  if (newTop + tooltipEstimatedHeight > window.innerHeight) {
    newTop = event.clientY - tooltipEstimatedHeight - offsetY;
  }
  
  // Ensure it doesn't go off the top/left of the screen either
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
        event.preventDefault(); // Prevent window scroll only if tooltip handled it
      }
    }
  }
};

</script>

<style scoped>
.added-components-section {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background-color: var(--color-background-soft);
}

.added-components-section h4 {
    color: var(--color-text);
    margin-top: 0; /* Adjust as it's the first element now */
    margin-bottom: 15px;
}

.added-components-tiles-container {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  padding: 10px;
  border: 1px solid var(--color-border-hover);
  border-radius: 4px;
  background-color: var(--color-background-mute);
  min-height: 120px; /* Or adjust as needed */
}

.added-component-tile {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 15px;
  width: calc(50% - 10px); /* Adjust gap calculation if gap is 15px: calc(50% - 7.5px) */
  box-shadow: 0 2px 5px rgba(0,0,0,0.07);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

@media (max-width: 768px) {
  .added-component-tile {
    width: calc(100% - 10px); /* Or simply width: 100% if gap is handled by parent */
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

.edit-component-btn {
  position: absolute;
  top: 8px;
  right: 38px; /* Position next to the remove button */
  width: auto; /* Auto width based on content */
  padding: 0 8px; /* Add some padding */
  height: 24px;
  border-radius: 12px; /* Pill shape */
  background-color: var(--color-button-bg, #4CAF50);
  color: var(--color-button-text, white);
  border: none;
  font-size: 12px; /* Adjusted font size */
  font-weight: bold;
  line-height: 24px; /* Center text vertically */
  text-align: center;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: background-color 0.2s ease;
}

.edit-component-btn:hover {
  background-color: var(--color-primary-dark, #45a049);
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
  padding-right: 5px; /* For scrollbar */
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
  /* Consider accent-color for modern browsers if you want themed checkboxes */
  /* accent-color: var(--color-primary); */
}

/* Basic styling for checked state, can be enhanced */
.person-checkbox-label input[type="checkbox"]:checked {
  /* background-color: var(--color-primary); No standard way to style checkbox bg easily */
  /* border-color: var(--color-primary); */
}

.no-people-in-plan-message {
  font-size: 0.85em;
  color: var(--color-text-secondary);
  font-style: italic;
}

.empty-added-components-section p {
  padding: 10px;
  color: var(--color-text-secondary);
  font-style: italic;
  margin-top: 10px;
  text-align: center;
  width: 100%;
  /* Consider adding a border or background like other sections if it looks too plain */
  /* border: 1px dashed var(--color-border); */
  /* background-color: var(--color-background-soft); */
  /* border-radius: 4px; */
}
</style> 