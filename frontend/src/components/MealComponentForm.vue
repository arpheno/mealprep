<template>
  <form @submit.prevent="saveMealComponent" class="meal-component-form">
    <div class="form-header">
      <h2>{{ isEditMode ? 'Edit Meal Component' : 'Create Meal Component' }}</h2>
    </div>
    <div class="form-group">
      <label for="name">Component Name:</label>
      <input type="text" id="name" v-model="componentData.name" required />
    </div>

    <div class="form-group">
      <label for="category_tag">Category Tag:</label>
      <input type="text" id="category_tag" v-model="componentData.category_tag" />
    </div>

    <div class="form-group">
      <label for="description_recipe">Description/Recipe:</label>
      <textarea id="description_recipe" v-model="componentData.description_recipe"></textarea>
    </div>

    <div class="form-group">
      <label for="frequency">Frequency:</label>
      <select id="frequency" v-model="componentData.frequency">
        <option value="PER_BOX">Per Meal Box</option>
        <option value="WEEKLY">Weekly Total</option>
        <option value="DAILY">Daily Total</option>
      </select>
    </div>

    <hr />

    <h3>Ingredients</h3>
    <div class="ingredient-search-section">
      <div class="form-group">
        <label for="ingredient-search">Search & Add Ingredient:</label>
        <input
          type="text"
          id="ingredient-search"
          v-model="ingredientSearchTerm"
          @input="debouncedSearchIngredients"
          placeholder="Type to search ingredients..."
        />
        <ul v-if="searchResults.length > 0" class="search-results">
          <li
            v-for="ingredient in searchResults"
            :key="ingredient.id"
            @click="selectIngredientForAddition(ingredient)"
          >
            {{ ingredient.name }}
          </li>
        </ul>
        <p v-if="searchedAndNoResults && ingredientSearchTerm.length >= 2" class="no-results-message">
          No ingredients found for "{{ ingredientSearchTerm }}".
        </p>
      </div>
    </div>

    <div v-if="componentData.ingredients_usage.length" class="added-ingredients-list">
      <h4>Added Ingredients:</h4>
      <table>
        <thead>
          <tr>
            <th>Ingredient</th>
            <th>Quantity (g)</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(usage, index) in componentData.ingredients_usage" :key="usage.ingredient_id">
            <td>{{ usage.ingredient_name }}</td>
            <td>
              <input type="number" v-model.number="usage.quantity" min="0" step="any" class="quantity-input" />
            </td>
            <td>
              <button type="button" @click="removeIngredient(index)" class="remove-btn">&times;</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    
    <hr />

    <div class="form-actions">
      <button type="submit" :disabled="isSaving">
        {{ isSaving ? 'Saving...' : (isEditMode ? 'Update Component' : 'Save Meal Component') }}
      </button>
      <button type="button" @click="cancelEdit" class="cancel-btn">
        Cancel
      </button>
    </div>

    <div v-if="nutritionalTotals && Object.keys(nutritionalTotals).length" class="nutritional-totals">
      <h3>Nutritional Totals:</h3>
      <ul>
        <li v-for="(value, key) in nutritionalTotals" :key="key">
          <strong>{{ key }}:</strong> {{ value.amount }} {{ value.unit }}
        </li>
      </ul>
    </div>
     <div v-if="error" class="error-message">
        <p>Error: {{ error }}</p>
    </div>

    <hr v-if="Object.keys(calculatedNutritionalBreakdown).length > 0" />

    <div v-if="Object.keys(calculatedNutritionalBreakdown).length > 0" class="nutritional-breakdown-section">
      <h3>Live Nutritional Breakdown:</h3>
      <table class="nutritional-breakdown-table">
        <thead>
          <tr>
            <th>Nutrient</th>
            <th>Total</th>
            <th>{{ currentRdaLabel }}</th>
            <th>{{ currentUlLabel }}</th>
            <th v-for="ingredientName in getIngredientNamesForBreakdownHeader" :key="ingredientName">
              {{ ingredientName }}
            </th>
          </tr>
        </thead>
        <!-- Iterate over groups first -->
        <template v-for="(nutrientsInGroup, groupName) in calculatedNutritionalBreakdown" :key="groupName">
          <tbody v-if="Object.keys(nutrientsInGroup).length > 0" class="nutrient-group">
            <tr class="nutrient-group-header">
              <th :colspan="4 + getIngredientNamesForBreakdownHeader.length">{{ groupName }}</th>
            </tr>
            <!-- Then iterate over nutrients in this group -->
            <tr v-for="(nutrientData, nutrientKey) in nutrientsInGroup" :key="nutrientKey" :style="getNutrientBarStyle(nutrientData)" class="nutrient-data-row">
              <td>{{ nutrientKey }}</td>
              <td class="nutrient-value-cell">{{ nutrientData.total.toFixed(2) }}</td>
              <td class="nutrient-value-cell">{{ formatDRV(componentData.frequency === 'WEEKLY' && nutrientData.rda ? nutrientData.rda * 7 : nutrientData.rda) }}</td>
              <td class="nutrient-value-cell">{{ formatDRV(componentData.frequency === 'WEEKLY' && nutrientData.ul ? nutrientData.ul * 7 : nutrientData.ul) }}</td>
              <td v-for="ingredientName in getIngredientNamesForBreakdownHeader" :key="ingredientName" class="nutrient-value-cell">
                {{ nutrientData.ingredients[ingredientName] ? nutrientData.ingredients[ingredientName].toFixed(2) : '-' }}
              </td>
            </tr>
          </tbody>
        </template>
      </table>
    </div>

  </form>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import axios from 'axios'; // We'll need axios for API calls

const props = defineProps({
  componentDataToEdit: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['form-closed', 'component-saved']);

// console.log('Vite Env Variables:', import.meta.env); // Log all env vars
// const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5001/api'; // Old way
const API_BASE_URL = process.env.VUE_APP_API_BASE_URL; // New way
console.log('API_BASE_URL (from DefinePlugin):', API_BASE_URL);

const initialComponentData = () => ({
  name: '',
  category_tag: '',
  description_recipe: '',
  frequency: 'PER_BOX',
  ingredients_usage: [],
});

const componentData = reactive(initialComponentData());

const ingredientSearchTerm = ref('');
const searchResults = ref([]);
const searchedAndNoResults = ref(false);

const nutritionalTotals = ref({});
const isSaving = ref(false);
const error = ref(null);

const isEditMode = computed(() => !!props.componentDataToEdit);

const populateFormForEdit = () => {
  if (props.componentDataToEdit) {
    console.log("Populating form for edit with:", JSON.parse(JSON.stringify(props.componentDataToEdit)));
    Object.assign(componentData, {
      name: props.componentDataToEdit.name || '',
      category_tag: props.componentDataToEdit.category_tag || '',
      description_recipe: props.componentDataToEdit.description_recipe || '',
      frequency: props.componentDataToEdit.frequency || 'PER_BOX',
      // Deep copy and map ingredients_usage if structure differs or needs processing
      // Assuming componentDataToEdit.ingredientusage_set (from Django serializer)
      // needs to be mapped to componentData.ingredients_usage
      ingredients_usage: (props.componentDataToEdit.ingredientusage_set || []).map(usage => ({
        ingredient_id: usage.ingredient_detail?.id || usage.ingredient, // Prefer detail if available
        ingredient_name: usage.ingredient_detail?.name || usage.ingredient_name || 'Unknown Ingredient', // Prefer detail
        quantity: usage.quantity,
        // nutrient_links and base_unit_for_nutrition might need to be fetched again or ensured they exist on ingredient_detail
        // For now, initialize and they can be enriched if selectIngredientForAddition is re-triggered somehow, or assume they are present
        nutrient_links: usage.ingredient_detail?.nutrient_links || [],
        base_unit_for_nutrition: usage.ingredient_detail?.base_unit_for_nutrition || 'g'
      })),
    });
    // Fetch full ingredient details for nutrient_links if not present
    // This is crucial for the live nutritional breakdown to work correctly in edit mode
    componentData.ingredients_usage.forEach(async (usage) => {
        if (usage.ingredient_id && (!usage.nutrient_links || usage.nutrient_links.length === 0)) {
            try {
                const response = await axios.get(`${API_BASE_URL}/ingredients/${usage.ingredient_id}/`);
                const fullIngredientData = response.data;
                usage.nutrient_links = fullIngredientData.nutrient_links || [];
                usage.base_unit_for_nutrition = fullIngredientData.base_unit_for_nutrition || 'g';
                if (!usage.ingredient_name || usage.ingredient_name === 'Unknown Ingredient') {
                    usage.ingredient_name = fullIngredientData.name;
                }
            } catch (err) {
                console.error(`Failed to fetch details for ingredient ID ${usage.ingredient_id} during edit mode population:`, err);
                // Potentially set an error message or handle missing data
            }
        }
    });


  } else {
    // Reset form if not in edit mode (e.g., if form was used for edit then switched to create)
    Object.assign(componentData, initialComponentData());
  }
};

onMounted(() => {
  populateFormForEdit();
});

watch(() => props.componentDataToEdit, () => {
  populateFormForEdit();
}, { deep: true });

// Helper to format DRV values for display
const formatDRV = (value) => {
  if (value === null || value === undefined) {
    return '-';
  }
  if (typeof value === 'number') {
      return Number.isInteger(value) ? value : value.toFixed(2);
  }
  return value;
};

const currentRdaLabel = computed(() => {
  return componentData.frequency === 'WEEKLY' ? 'RWA' : 'RDA';
});

const currentUlLabel = computed(() => {
  return componentData.frequency === 'WEEKLY' ? 'UWL' : 'UL';
});

const calculatedNutritionalBreakdown = computed(() => {
  const getHardcodedNutrientGroup = (nutrientName, fdcNumber) => {
    const nameLower = nutrientName.toLowerCase();
    // Order: Macronutrients, Minerals, Vitamins, General

    // Macronutrients (by FDC number or name)
    if (["203", "204", "205", "291"].includes(fdcNumber)) return 'Macronutrients';
    if (nameLower.includes('protein') || nameLower.includes('fat') || nameLower.includes('lipid') || 
        nameLower.includes('carbohydrate') || nameLower.includes('fiber')) {
      return 'Macronutrients';
    }

    // Minerals (by name)
    if (nameLower.includes('calcium') || nameLower.includes('iron') || nameLower.includes('magnesium') ||
        nameLower.includes('phosphorus') || nameLower.includes('potassium') || nameLower.includes('sodium') ||
        nameLower.includes('zinc') || nameLower.includes('copper') || nameLower.includes('manganese') ||
        nameLower.includes('selenium') || nameLower.includes('fluoride') || nameLower.includes('iodine') || 
        nameLower.includes('chloride') || nameLower.includes('chromium') || nameLower.includes('molybdenum')) {
      return 'Minerals';
    }

    // Vitamins (by name)
    if (nameLower.includes('vitamin') || nameLower.includes('thiamin') || nameLower.includes('riboflavin') ||
        nameLower.includes('niacin') || nameLower.includes('folate') || nameLower.includes('choline') ||
        nameLower.includes('pantothenic') || nameLower.includes('biotin') || nameLower.includes('retinol') ||
        nameLower.includes('carotene') || nameLower.includes('cryptoxanthin') || nameLower.includes('lycopene') || 
        nameLower.includes('lutein') || nameLower.includes('tocopherol') || nameLower.includes('phylloquinone') || 
        nameLower.includes('menaquinone') || nameLower.includes('calciferol') || nameLower.includes('ergocalciferol') || 
        nameLower.includes('cholecalciferol') || nameLower.includes('cobalamin')) {
      return 'Vitamins';
    }
    
    // General (includes Energy, Water, Caffeine, Alcohol, Cholesterol etc.)
    if (fdcNumber === "208" || nameLower.includes('energy') || nameLower.includes('water') || 
        nameLower.includes('caffeine') || nameLower.includes('alcohol') || nameLower.includes('cholesterol') ||
        nameLower.includes('ash') || nameLower.includes('theobromine')) {
      return 'General & Other';
    }

    console.warn(`Nutrient '${nutrientName}' (FDC# ${fdcNumber}) not explicitly categorized, falling back to 'General & Other'.`);
    return 'General & Other'; // Fallback for anything not caught
  };

  const groupedBreakdown = {
    'Macronutrients': {},
    'Minerals': {},
    'Vitamins': {},
    'General & Other': {}
  };

  componentData.ingredients_usage.forEach(usage => {
    if (!usage.nutrient_links || usage.quantity <= 0) return;
    const quantityMultiplier = usage.quantity / 100.0;

    usage.nutrient_links.forEach(link => {
      if (!link) {
        console.warn('Skipping undefined nutrient link object.');
        return;
      }
      const categoryGroup = getHardcodedNutrientGroup(link.nutrient_name, link.fdc_nutrient_number);
      const nutrientKey = `${link.nutrient_name} (${link.nutrient_unit})`;
      const amountFromThisIngredient = link.amount_per_100_units * quantityMultiplier;

      if (!groupedBreakdown[categoryGroup][nutrientKey]) {
        groupedBreakdown[categoryGroup][nutrientKey] = {
          total: 0,
          unit: link.nutrient_unit,
          rda: link.default_rda,
          ul: link.upper_limit,
          ingredients: {}
        };
      }

      groupedBreakdown[categoryGroup][nutrientKey].total += amountFromThisIngredient;
      groupedBreakdown[categoryGroup][nutrientKey].ingredients[usage.ingredient_name] = 
        (groupedBreakdown[categoryGroup][nutrientKey].ingredients[usage.ingredient_name] || 0) + amountFromThisIngredient;
    });
  });

  const finalBreakdown = {};
  for (const groupName in groupedBreakdown) {
    const group = groupedBreakdown[groupName];
    const filteredGroupNutrients = {};
    let groupHasNutrients = false;

    for (const nutrientKey in group) {
      if (group[nutrientKey].total > 0) { 
        filteredGroupNutrients[nutrientKey] = {
          ...group[nutrientKey],
        };
        groupHasNutrients = true;
      }
    }
    if (groupHasNutrients) {
      finalBreakdown[groupName] = filteredGroupNutrients;
    }
  }
  return finalBreakdown;
});

const getIngredientNamesForBreakdownHeader = computed(() => {
  const names = new Set();
  componentData.ingredients_usage.forEach(usage => {
    if (usage.quantity > 0) { 
      names.add(usage.ingredient_name);
    }
  });
  return Array.from(names);
});

let debounceTimer = null;

const debouncedSearchIngredients = () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    if (ingredientSearchTerm.value.length < 2) { 
        searchResults.value = [];
        searchedAndNoResults.value = false; 
        return;
    }
    searchIngredients();
  }, 300); 
};

const searchIngredients = async () => {
  searchResults.value = []; 
  searchedAndNoResults.value = false; 

  if (ingredientSearchTerm.value.length < 2) { 
    return;
  }
  try {
    error.value = null;
    const response = await axios.get(`${API_BASE_URL}/ingredients/search/?name=${ingredientSearchTerm.value}`);
    console.log('API Response for ingredients search:', response.data); 
    
    const results = response.data.results; 

    if (results && results.length > 0) {
      searchResults.value = results;
      searchedAndNoResults.value = false;
    } else {
      searchResults.value = [];
      if (response.data && Object.prototype.hasOwnProperty.call(response.data, 'results')) { 
          searchedAndNoResults.value = true;
      } else {
        searchedAndNoResults.value = true; 
      }
    }
  } catch (err) {
    console.error('Error searching ingredients:', err);
    error.value = 'Failed to search ingredients. ' + (err.response?.data?.detail || err.message);
    searchResults.value = [];
    searchedAndNoResults.value = true; 
  }
};

const selectIngredientForAddition = async (ingredientFromSearch) => { 
  ingredientSearchTerm.value = ''; 
  searchResults.value = []; 
  searchedAndNoResults.value = false;

  if (!ingredientFromSearch || !ingredientFromSearch.id) {
    console.error('Invalid ingredient selected from search', ingredientFromSearch);
    error.value = 'Invalid ingredient data received from search.';
    return;
  }

  const existing = componentData.ingredients_usage.find(iu => iu.ingredient_id === ingredientFromSearch.id);
  if (existing) {
    alert(`${ingredientFromSearch.name} is already in the list. You can adjust its quantity below.`);
    return; 
  }

  try {
    error.value = null;
    const response = await axios.get(`${API_BASE_URL}/ingredients/${ingredientFromSearch.id}/`);
    const fullIngredientData = response.data;

    componentData.ingredients_usage.push({
      ingredient_id: fullIngredientData.id,
      ingredient: fullIngredientData.id,    
      ingredient_name: fullIngredientData.name,
      quantity: 1, 
      nutrient_links: fullIngredientData.nutrient_links || [],
      base_unit_for_nutrition: fullIngredientData.base_unit_for_nutrition || 'g'
    });

  } catch (err) {
    console.error('Error fetching full ingredient details:', err);
    error.value = `Failed to fetch details for ${ingredientFromSearch.name}. ` + (err.response?.data?.detail || err.message);
  }
};

const removeIngredient = (index) => {
  componentData.ingredients_usage.splice(index, 1);
};

const saveMealComponent = async () => {
  if (componentData.ingredients_usage.length === 0) {
    alert('Please add at least one ingredient.');
    return;
  }
  isSaving.value = true;
  error.value = null;
  nutritionalTotals.value = {};

  const payload = {
    name: componentData.name,
    category_tag: componentData.category_tag,
    description_recipe: componentData.description_recipe,
    frequency: componentData.frequency,
    ingredients_usage_write: componentData.ingredients_usage.map(u => ({
      ingredient: u.ingredient_id, 
      quantity: u.quantity
    }))
  };
  // Do NOT delete payload.ingredients_usage here as it's not part of componentData directly anymore for submission

  try {
    let response;
    if (isEditMode.value) {
      console.log('Updating component with ID:', props.componentDataToEdit.id);
      response = await axios.put(`${API_BASE_URL}/mealcomponents/${props.componentDataToEdit.id}/`, payload);
    } else {
      response = await axios.post(`${API_BASE_URL}/mealcomponents/`, payload);
    }
    
    nutritionalTotals.value = response.data.nutritional_totals || {}; // Update with fresh totals from backend
    console.log(isEditMode.value ? 'Updated component:' : 'Saved new component:', response.data);
    
    // Emit an event with the saved/updated component data so the parent can react
    emit('component-saved', response.data); 
    // emit('form-closed', response.data); // Or form-closed if save always closes

  } catch (err) {
    console.error('Error saving meal component:', err.response ? err.response.data : err.message);
    error.value = 'Failed to save meal component. ' + (err.response?.data ? JSON.stringify(err.response.data) : err.message);
  } finally {
    isSaving.value = false;
  }
};

const cancelEdit = () => {
  emit('form-closed', null); // Signal that the form was closed without saving
};

const getNutrientBarStyle = (nutrient) => {
  const { total } = nutrient;
  let { rda, ul } = nutrient; // Make them mutable for weekly adjustment

  const isWeekly = componentData.frequency === 'WEEKLY';

  if (isWeekly) {
    if (rda !== null && rda !== undefined) rda *= 7;
    if (ul !== null && ul !== undefined) ul *= 7;
  }

  let percentage = 0; // Percentage of RDA
  if (rda && rda > 0) {
    percentage = (total / rda) * 100;
  }

  // Color definitions from CSS variables (assuming they are HSL or hex)
  const dangerColor = 'var(--color-nutrient-bar-danger)'; // e.g., hsl(0, 100%, 50%)
  // Define base green (less saturated) and target full green (more saturated)
  // These could also be CSS variables if you prefer to define them in <style>
  const baseGreenH = 120; // Hue for green
  const baseGreenS = 50;  // Base saturation
  const baseGreenL = 60;  // Base lightness
  
  const targetGreenS = 70; // Target saturation for 100% RDA
  const targetGreenL = 50; // Target lightness for 100% RDA

  let currentBackgroundColor = 'transparent';

  if (ul && ul > 0 && total > ul) {
    currentBackgroundColor = dangerColor; // Exceeded UL - DANGER
  } else if (rda && rda > 0) {
    // We have an RDA to compare against
    if (total >= 0) {
      const saturationRatio = Math.min(percentage / 100, 1); // Cap at 100% for saturation calculation
      const currentS = baseGreenS + (targetGreenS - baseGreenS) * saturationRatio;
      const currentL = baseGreenL - (baseGreenL - targetGreenL) * saturationRatio; // Lightness decreases as saturation increases
      
      // If total > RDA but still under UL (or no UL), it's a more saturated green.
      // If total <= RDA, it's a graduated green.
      currentBackgroundColor = `hsl(${baseGreenH}, ${currentS.toFixed(0)}%, ${currentL.toFixed(0)}%)`;
    }
  } else if (total > 0) { // Has a total, but no RDA (or RDA is 0)
    if (ul && ul > 0 && total > ul) {
      currentBackgroundColor = dangerColor; // Exceeds UL
    } else {
      // No RDA, but has value and not over UL. Use a neutral or very light green.
      currentBackgroundColor = `hsl(${baseGreenH}, ${baseGreenS * 0.5}%, ${baseGreenL * 1.1}%)`; // Example: very desaturated light green
    }
  }

  // Handle no-bar cases
  if (total === 0 && (!rda || rda === 0)) {
    return { background: 'transparent' };
  }
  if ((!rda || rda <= 0) && total > 0 ) { // Has total, no RDA
      if (ul && ul > 0 && total > ul) {
          return { background: dangerColor }; // Full red bar indicating danger vs UL
      }
      // A small sliver or neutral background for items with no RDA but some value
      // Using the calculated currentBackgroundColor which would be a light green or neutral
      return { background: `linear-gradient(to right, ${currentBackgroundColor} 15px, var(--color-input-bg) 15px)` };
  }
  
  // For the gradient, the bar's main color will be currentBackgroundColor
  // The gradient stop percentage reflects how "full" the bar is relative to RDA.
  // We can cap visualPercentage for the gradient stop if we don't want it to exceed 100% of the cell width.
  const visualProgressPercentage = Math.max(0, Math.min(percentage, 100)); 

  return {
    background: `linear-gradient(to right, ${currentBackgroundColor} ${visualProgressPercentage}%, color-mix(in srgb, ${currentBackgroundColor} 20%, transparent) ${Math.min(100, visualProgressPercentage + 5)}%, transparent ${Math.min(100, visualProgressPercentage + 10)}%)`,
    transition: 'background 0.5s ease',
  };
};

</script>

<style scoped>
.meal-component-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
  padding: 20px; /* Added padding to the form itself */
  border: 1px solid var(--color-border); /* Use CSS var */
  border-radius: 8px; /* Added for consistency */
  background-color: var(--color-background); /* Use CSS var */
}
.form-group {
  display: flex;
  flex-direction: column;
}
.form-group label {
  margin-bottom: 5px;
  font-weight: bold;
  color: var(--color-text); /* Use CSS var */
}
.form-group input[type="text"],
.form-group input[type="number"],
.form-group textarea,
.form-group select {
  padding: 10px; /* Increased padding */
  border: 1px solid var(--color-input-border); /* Use CSS var */
  border-radius: 4px;
  font-size: 1em;
  background-color: var(--color-input-bg); /* Use CSS var */
  color: var(--color-text); /* Use CSS var */
}
.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--color-primary); /* Highlight focus with primary color */
  box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb, 66, 185, 131), 0.3); /* Assuming primary is #42b983 */
}
.form-group textarea {
  min-height: 80px;
  resize: vertical;
}

hr { /* Style for hr */
  border: none;
  border-top: 1px solid var(--color-border);
  margin-top: 15px;
  margin-bottom: 15px;
}

h3, h4 { /* Style for headings */
  color: var(--color-text);
  margin-top: 10px;
  margin-bottom: 10px;
}

.ingredient-search-section {
  border: 1px solid var(--color-border); /* Use CSS var */
  padding: 15px;
  border-radius: 4px;
  margin-bottom:10px;
  background-color: var(--color-background); /* Slight distinction if needed, or keep same as form bg */
}
.search-results {
  list-style: none;
  padding: 0;
  margin: 5px 0 0 0;
  border: 1px solid var(--color-border); /* Use CSS var */
  background-color: var(--color-input-bg); /* Use CSS var */
  max-height: 150px;
  overflow-y: auto;
  border-radius: 4px; /* Added */
}
.search-results li {
  padding: 8px 12px; /* Adjusted padding */
  cursor: pointer;
  color: var(--color-text); /* Use CSS var */
}
.search-results li:hover {
  background-color: var(--color-primary); /* Use CSS var or a hover-specific var */
  color: var(--color-button-text); /* Ensure text is readable on hover */
}
.ingredient-addition-controls {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-top: 10px;
}
.ingredient-addition-controls span { /* Style for the selected ingredient name */
    color: var(--color-text);
}
.ingredient-addition-controls input[type="number"] {
  width: 100px;
}
/* Style for the "Add to Component" button specifically if needed, or rely on global button styles */
.ingredient-addition-controls button {
  padding: 8px 12px;
  background-color: var(--color-primary); /* Use CSS var */
  color: var(--color-button-text); /* Use CSS var */
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.ingredient-addition-controls button:hover {
  opacity: 0.9;
}


.added-ingredients-list {
  margin-top: 10px;
}
.added-ingredients-list h4 {
  margin-bottom: 10px;
}
.added-ingredients-list table {
  width: 100%;
  border-collapse: collapse;
}
.added-ingredients-list th,
.added-ingredients-list td {
  border: 1px solid var(--color-border);
  padding: 8px;
  text-align: left;
  color: var(--color-text);
}
.added-ingredients-list th {
  background-color: var(--color-input-bg); /* Or a slightly different shade */
}
.quantity-input {
  width: 80px; /* Adjust as needed */
  padding: 6px;
  border: 1px solid var(--color-input-border);
  border-radius: 4px;
  background-color: var(--color-input-bg);
  color: var(--color-text);
}
.remove-btn {
  background: transparent;
  border: none;
  color: #e74c3c; /* A common 'danger' red, consider making it a CSS var if used elsewhere */
  font-size: 1.2em;
  cursor: pointer;
  padding: 0 5px; /* Added padding */
}
.remove-btn:hover {
    color: #c0392b; /* Darker red on hover */
}

.form-actions {
  margin-top: 20px;
}
.form-actions button {
  padding: 12px 25px; /* Increased padding */
  background-color: var(--color-button-bg); /* Use CSS var */
  color: var(--color-button-text); /* Use CSS var */
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 1em;
  font-weight: bold; /* Added */
}
.form-actions button:disabled {
  background-color: var(--color-border); /* Use CSS var */
  color: var(--color-text);
  opacity: 0.7; /* Added */
  cursor: not-allowed; /* Added */
}
.nutritional-totals {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid var(--color-border); /* Use CSS var */
  background-color: var(--color-background); /* Use CSS var, maybe slightly different if desired */
  border-radius: 8px; /* Added */
}
.nutritional-totals h3 {
  margin-top:0;
  color: var(--color-text); /* Use CSS var */
}
.nutritional-totals ul {
    list-style: none;
    padding: 0;
}
.nutritional-totals li {
    padding: 5px 0;
    color: var(--color-text); /* Use CSS var */
}
.error-message {
  color: #e74c3c; /* Consider making this a CSS var: --color-error-text */
  margin-top: 15px;
  padding: 10px;
  border: 1px solid #e74c3c; /* Consider --color-error-border */
  background-color: rgba(231, 76, 60, 0.1); /* Consider --color-error-bg */
  border-radius: 4px; /* Added */
}
.no-results-message {
  padding: 8px 12px;
  color: var(--color-text);
  font-style: italic;
  margin-top: 5px;
  background-color: var(--color-input-bg); /* Match input bg for subtle message */
  border: 1px solid var(--color-border);
  border-radius: 4px;
}

/* Styles for Nutritional Breakdown Table */
.nutritional-breakdown-section {
  margin-top: 20px;
  overflow-x: auto; /* Add horizontal scroll if content overflows */
}
.nutritional-breakdown-table {
  width: 100%;
  border-collapse: collapse; /* Changed from separate to collapse for better row bg effect */
  margin-top: 10px;
  font-size: 0.9em; 
}

.nutritional-breakdown-table th,
.nutritional-breakdown-table td {
  border: 1px solid var(--color-border);
  padding: 10px 12px; /* Increased padding for relaxed feel */
  text-align: left;
  color: var(--color-text);
  position: relative; /* For z-indexing text over row background */
  z-index: 1;
  background-color: transparent; /* Ensure cell has no bg, to show row background */
}

.nutritional-breakdown-table th {
  background-color: var(--color-input-bg); /* Keep header bg distinct */
  white-space: nowrap; 
  z-index: 2; /* Headers above row backgrounds */
}

/* Specific styling for nutrient name and value cells if needed for text overlay */
.nutritional-breakdown-table td.nutrient-value-cell {
  text-align: right; /* Align numbers to the right */
  /* Potentially add text-shadow for contrast if needed later */
  /* text-shadow: 0 0 3px var(--color-background); */ 
}
.nutritional-breakdown-table td:first-child { /* Nutrient Name cell */
  text-align: left; 
  font-weight: bold;
}

.nutrient-data-row {
  /* The :style binding will apply the gradient background here */
  /* Add a subtle border between rows if border-collapse is used */
  border-bottom: 1px solid var(--color-border); 
}
.nutrient-data-row:last-child {
  border-bottom: none;
}

/* Styles for Nutrient Group Header */
.nutrient-group-header th {
  background-color: var(--color-nav-bg); /* A slightly different background for group headers */
  color: var(--color-text);
  text-align: left;
  padding: 8px;
  font-weight: bold;
  border-top: 2px solid var(--color-border); /* Extra separator for groups */
}
.nutrient-group:first-of-type .nutrient-group-header th {
  border-top: 1px solid var(--color-border); /* Regular border for the first group header */
}

/* Styles for visualization section REMOVED or will be repurposed for table cells */

/* .charts-grid, .macronutrient-pie-chart-wrapper styles REMOVED */

/* Remove old bar styles as they are no longer used */
/*
.nutrient-total-cell {
  position: relative; 
}
.nutrient-bar-container {
  position: relative;
  width: 100%;
  height: 20px; 
  background-color: var(--color-input-bg); 
  border-radius: 3px;
  overflow: hidden; 
}
.nutrient-bar {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  height: 100%;
  border-radius: 3px; 
  transition: width 0.3s ease, background-color 0.3s ease;
  min-width: 2px; 
}
.nutrient-total-text {
  position: absolute;
  left: 5px; 
  right: 5px; 
  top: 50%;
  transform: translateY(-50%);
  color: var(--color-text); 
  font-size: 0.9em;
  font-weight: bold;
  white-space: nowrap;
}
.nutritional-breakdown-table td.nutrient-total-cell {
    overflow: visible; 
}
.nutrient-bar-container {
    overflow: visible; 
}
*/

</style> 