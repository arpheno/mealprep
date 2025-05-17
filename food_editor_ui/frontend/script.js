document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://localhost:8008/api';

    // --- DOM Elements ---
    const dataSourceSelect = document.getElementById('dataSourceSelect');
    const searchInput = document.getElementById('searchFoodInput');
    const searchButton = document.getElementById('searchButton');
    const foodResultsSelect = document.getElementById('foodResultsSelect');
    const foodSearchError = document.getElementById('foodSearchError');
    
    const foodEditFormSection = document.getElementById('foodEditFormSection');
    const foodEditForm = document.getElementById('foodEditForm');
    const fdcIdOriginalInput = document.getElementById('fdcIdOriginal');
    const descriptionInput = document.getElementById('description');
    const foodClassInput = document.getElementById('foodClass');
    const foodCategoryIdOriginalInput = document.getElementById('foodCategoryIdOriginal');
    const foodCategoryDescriptionInput = document.getElementById('foodCategoryDescription');
    const foodCategoryCodeInput = document.getElementById('foodCategoryCode');
    const nutrientsContainer = document.getElementById('nutrientsContainer');
    const addNutrientButton = document.getElementById('addNutrientButton');
    const portionsContainer = document.getElementById('portionsContainer');
    const addPortionButton = document.getElementById('addPortionButton');
    const saveToMyFoodsButton = document.getElementById('saveToMyFoodsButton');
    const saveSuccessMessage = document.getElementById('saveSuccessMessage');
    const saveErrorMessage = document.getElementById('saveErrorMessage');

    const loadMyFoodsButton = document.getElementById('loadMyFoodsButton');
    const myFoodsListUl = document.getElementById('myFoodsList');
    const myFoodsError = document.getElementById('myFoodsError');

    let currentFoodDataForEditing = null; // Stores the full data of the food being edited

    // --- Helper Functions ---
    function displayError(element, message) {
        element.textContent = message;
        element.style.display = 'block';
    }

    function clearError(element) {
        element.textContent = '';
        element.style.display = 'none';
    }

    function displaySuccess(element, message) {
        element.textContent = message;
        element.style.display = 'block';
        setTimeout(() => element.style.display = 'none', 3000);
    }

    // --- API Calls ---
    async function searchFoods(query, dataSource) {
        clearError(foodSearchError);
        let searchUrl = '';
        if (dataSource === 'foundational') {
            searchUrl = `${API_BASE_URL}/foundational_foods/search?query=${encodeURIComponent(query)}&limit=50`;
        } else if (dataSource === 'survey') {
            searchUrl = `${API_BASE_URL}/survey_foods/search?query=${encodeURIComponent(query)}&limit=50`;
        } else {
            displayError(foodSearchError, 'Invalid data source selected.');
            return;
        }

        try {
            const response = await fetch(searchUrl);
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Error: ${response.status}`);
            }
            const foods = await response.json();
            populateFoodResultsSelect(foods);
        } catch (error) {
            console.error(`Error searching ${dataSource} foods:`, error);
            displayError(foodSearchError, `Failed to search: ${error.message}`);
        }
    }

    async function getFoodById(fdcId, dataSource) {
        clearError(foodSearchError);
        let fetchUrl = '';
        if (dataSource === 'foundational') {
            fetchUrl = `${API_BASE_URL}/foundational_foods/${fdcId}`;
        } else if (dataSource === 'survey') {
            fetchUrl = `${API_BASE_URL}/survey_foods/${fdcId}`;
        } else {
            displayError(foodSearchError, 'Invalid data source for fetching details.');
            return;
        }

        try {
            const response = await fetch(fetchUrl);
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Error: ${response.status}`);
            }
            const food = await response.json();
            populateEditForm(food);
        } catch (error) {
            console.error(`Error fetching ${dataSource} food by ID:`, error);
            displayError(foodSearchError, `Failed to load details: ${error.message}`);
        }
    }

    async function saveFoodToMyFoods(foodData) {
        clearError(saveErrorMessage);
        saveSuccessMessage.style.display = 'none';
        try {
            const response = await fetch(`${API_BASE_URL}/my_foods`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(foodData),
            });
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Error: ${response.status}`);
            }
            const savedFood = await response.json();
            displaySuccess(saveSuccessMessage, `Food "${savedFood.description}" saved successfully with ID ${savedFood.fdcId}!`);
            foodEditForm.reset();
            foodEditFormSection.style.display = 'none';
            currentFoodDataForEditing = null;
            nutrientsContainer.innerHTML = '';
            portionsContainer.innerHTML = '';
            fetchMyFoods(); // Refresh the list
        } catch (error) {
            console.error('Error saving food:', error);
            displayError(saveErrorMessage, `Failed to save food: ${error.message}`);
        }
    }
    
    async function fetchMyFoods() {
        clearError(myFoodsError);
        myFoodsListUl.innerHTML = ''; // Clear previous list
        try {
            const response = await fetch(`${API_BASE_URL}/my_foods`);
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || `Error: ${response.status}`);
            }
            const foods = await response.json();
            populateMyFoodsList(foods);
        } catch (error) {
            console.error('Error fetching my foods:', error);
            displayError(myFoodsError, `Failed to load your foods: ${error.message}`);
        }
    }

    // --- UI Population ---
    function populateFoodResultsSelect(foods) {
        foodResultsSelect.innerHTML = '<option value="">-- Select a food to use as template --</option>';
        if (foods.length === 0) {
            foodResultsSelect.innerHTML += '<option value="" disabled>No foods found for your query.</option>';
            return;
        }
        foods.forEach(food => {
            const option = document.createElement('option');
            option.value = food.fdcId;
            option.textContent = `${food.description} (ID: ${food.fdcId})`;
            foodResultsSelect.appendChild(option);
        });
    }

    function populateEditForm(food) {
        currentFoodDataForEditing = JSON.parse(JSON.stringify(food)); // Deep copy for editing
        
        fdcIdOriginalInput.value = food.fdcId; 
        descriptionInput.value = food.description || '';
        foodClassInput.value = 'Custom'; 

        const foodCategory = food.foodCategory || {};
        foodCategoryIdOriginalInput.value = foodCategory.id || '';
        foodCategoryDescriptionInput.value = foodCategory.description || 'Custom Foods';
        foodCategoryCodeInput.value = foodCategory.code || '9999';

        nutrientsContainer.innerHTML = '';
        if (food.foodNutrients) {
            let nutrientDisplayIndex = 0;
            food.foodNutrients.forEach((fn) => {
                // Only add nutrient to form if amount is present and not zero
                if (fn.amount !== null && fn.amount !== undefined && parseFloat(fn.amount) !== 0) {
                    addNutrientToForm(fn, nutrientDisplayIndex);
                    nutrientDisplayIndex++;
                }
            });
        }

        portionsContainer.innerHTML = '';
        if (food.foodPortions) {
            food.foodPortions.forEach((fp, index) => addPortionToForm(fp, index));
        }

        foodEditFormSection.style.display = 'block';
        saveErrorMessage.style.display = 'none';
        saveSuccessMessage.style.display = 'none';
    }

    function addNutrientToForm(foodNutrient, index) {
        const nutrient = foodNutrient.nutrient || {};
        const amount = foodNutrient.amount !== undefined ? foodNutrient.amount : '';

        const itemDiv = document.createElement('div');
        itemDiv.classList.add('nutrient-item'); // Keep existing class for general styling, add new for specific
        itemDiv.classList.add('nutrient-item-inline'); // New class for inline styling

        itemDiv.innerHTML = `
            <div class="nutrient-header">
                <strong>Nutrient ${index + 1}</strong> (ID: ${nutrient.id || 'New'})
            </div>
            <input type="hidden" name="nutrient_${index}_id" value="${nutrient.id || ''}">
            <input type="hidden" name="nutrient_${index}_rank" value="${nutrient.rank || '0'}">
            
            <input type="text" class="nutrient-name" name="nutrient_${index}_name" value="${nutrient.name || ''}" placeholder="Name" required title="Nutrient Name">
            <input type="text" class="nutrient-number" name="nutrient_${index}_number" value="${nutrient.number || ''}" placeholder="No." title="Nutrient Number">
            <input type="text" class="nutrient-unit" name="nutrient_${index}_unitName" value="${nutrient.unitName || ''}" placeholder="Unit" required title="Nutrient Unit">
            <input type="number" step="any" class="nutrient-amount" name="nutrient_${index}_amount" value="${amount}" placeholder="Amount" title="Nutrient Amount">
            <button type="button" class="remove-button" data-index="${index}" data-type="nutrient">Remove</button>
        `;
        nutrientsContainer.appendChild(itemDiv);
        itemDiv.querySelector('.remove-button').addEventListener('click', (e) => removeItemFromForm(e, nutrientsContainer));
    }

    function addPortionToForm(foodPortion, index) {
        const measureUnit = foodPortion.measureUnit || {};
        const portionDescription = foodPortion.portionDescription || '';
        const portionAmount = foodPortion.amount !== null && foodPortion.amount !== undefined ? foodPortion.amount : ''; // Default to empty string
        const portionGramWeight = foodPortion.gramWeight !== null && foodPortion.gramWeight !== undefined ? foodPortion.gramWeight : ''; // Default to empty string

        const itemDiv = document.createElement('div');
        itemDiv.classList.add('portion-item');
        itemDiv.innerHTML = `
            <h4>Portion ${index + 1} (ID: ${foodPortion.id || 'New'}) <button type="button" class="remove-button" data-index="${index}" data-type="portion">Remove</button></h4>
            <input type="hidden" name="portion_${index}_id" value="${foodPortion.id || ''}">
            <input type="hidden" name="portion_${index}_measureUnit_id" value="${measureUnit.id || ''}">
            <div class="portion-field">
                <label for="portion_${index}_description">Description (e.g., 1 cup):</label>
                <input type="text" id="portion_${index}_description" name="portion_${index}_description" value="${portionDescription}" required>
            </div>
            <div class="portion-field">
                <label for="portion_${index}_amount">Portion Amount (e.g., 1):</label>
                <input type="number" step="any" id="portion_${index}_amount" name="portion_${index}_amount" value="${portionAmount}" required>
            </div>
            <div class="portion-field">
                <label for="portion_${index}_gramWeight">Gram Weight:</label>
                <input type="number" step="any" id="portion_${index}_gramWeight" name="portion_${index}_gramWeight" value="${portionGramWeight}" required>
            </div>
            <div class="portion-field">
                <label for="portion_${index}_modifier">Modifier (e.g., slice):</label>
                <input type="text" id="portion_${index}_modifier" name="portion_${index}_modifier" value="${foodPortion.modifier || ''}">
            </div>
            <div class="portion-field">
                <label for="portion_${index}_measureUnit_name">Measure Unit Name (e.g., cup):</label>
                <input type="text" id="portion_${index}_measureUnit_name" name="portion_${index}_measureUnit_name" value="${measureUnit.name || ''}" required>
            </div>
             <div class="portion-field">
                <label for="portion_${index}_measureUnit_abbreviation">Measure Unit Abbreviation (e.g., c):</label>
                <input type="text" id="portion_${index}_measureUnit_abbreviation" name="portion_${index}_measureUnit_abbreviation" value="${measureUnit.abbreviation || ''}" required>
            </div>
        `;
        portionsContainer.appendChild(itemDiv);
        itemDiv.querySelector('.remove-button').addEventListener('click', (e) => removeItemFromForm(e, portionsContainer));
    }

    function removeItemFromForm(event, container) {
        const itemDiv = event.target.closest('.nutrient-item, .portion-item');
        if (itemDiv) {
            container.removeChild(itemDiv);
            // Re-index remaining items if necessary, or handle during form submission
        }
    }

    function populateMyFoodsList(foods) {
        myFoodsListUl.innerHTML = ''; // Clear previous list
        if (foods.length === 0) {
            myFoodsListUl.innerHTML = '<li>Your custom food list is empty.</li>';
            return;
        }
        foods.forEach(food => {
            const li = document.createElement('li');
            li.textContent = `${food.description} (ID: ${food.fdcId}, Nutrients: ${food.foodNutrients.length}, Portions: ${food.foodPortions.length})`;
            myFoodsListUl.appendChild(li);
        });
    }

    // --- Event Listeners ---
    searchButton.addEventListener('click', () => {
        const query = searchInput.value.trim();
        const selectedDataSource = dataSourceSelect.value;
        if (query.length >= 3) {
            searchFoods(query, selectedDataSource);
        } else {
            displayError(foodSearchError, 'Please enter at least 3 characters to search.');
        }
    });
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            searchButton.click();
        }
    });

    foodResultsSelect.addEventListener('change', (event) => {
        const selectedFdcId = event.target.value;
        const selectedDataSource = dataSourceSelect.value;
        if (selectedFdcId) {
            getFoodById(selectedFdcId, selectedDataSource);
        }
    });

    foodEditForm.addEventListener('submit', (event) => {
        event.preventDefault();
        // const formData = new FormData(foodEditForm); // We are directly accessing input values now
        
        const foodCategoryDesc = foodCategoryDescriptionInput.value || 'Custom Foods';
        const foodCategoryCodeVal = foodCategoryCodeInput.value || '9999';
        // The foodCategory.id from the form is not directly used for submission for new custom item;
        // backend generates a new one. We pass 0 or the original ID if we want to link to existing, which is not the case here.

        const foodData = {
            fdcId: 0, 
            description: descriptionInput.value,
            foodClass: 'Custom',
            foodCategory: {
                id: 0, // Let backend generate a new ID for this custom food's category
                description: foodCategoryDesc,
                code: foodCategoryCodeVal,
            },
            foodNutrients: [],
            foodPortions: [],
        };
        
        // Reconstruct nutrients
        const nutrientItems = nutrientsContainer.querySelectorAll('.nutrient-item');
        nutrientItems.forEach((item, i) => {
            const nutrientId = parseInt(item.querySelector(`input[name^="nutrient_${i}_id"]`).value);
            foodData.foodNutrients.push({
                nutrient: {
                    id: isNaN(nutrientId) ? 0 : nutrientId, // if new, will be 0 or based on template
                    name: item.querySelector(`input[name^="nutrient_${i}_name"]`).value,
                    number: item.querySelector(`input[name^="nutrient_${i}_number"]`).value,
                    rank: parseInt(item.querySelector(`input[name^="nutrient_${i}_rank"]`).value) || 0,
                    unitName: item.querySelector(`input[name^="nutrient_${i}_unitName"]`).value,
                },
                amount: parseFloat(item.querySelector(`input[name^="nutrient_${i}_amount"]`).value) || null,
            });
        });

        // Reconstruct portions
        const portionItems = portionsContainer.querySelectorAll('.portion-item');
        portionItems.forEach((item, i) => {
            const portionId = parseInt(item.querySelector(`input[name^="portion_${i}_id"]`).value);
            const measureUnitId = parseInt(item.querySelector(`input[name^="portion_${i}_measureUnit_id"]`).value);
            const amountValue = parseFloat(item.querySelector(`input[name^="portion_${i}_amount"]`).value);
            const gramWeightValue = parseFloat(item.querySelector(`input[name^="portion_${i}_gramWeight"]`).value);

            foodData.foodPortions.push({
                id: isNaN(portionId) ? 0 : portionId, 
                amount: isNaN(amountValue) ? null : amountValue, // Send null if not a number
                gramWeight: isNaN(gramWeightValue) ? null : gramWeightValue, // Send null if not a number
                modifier: item.querySelector(`input[name^="portion_${i}_modifier"]`).value || null,
                portionDescription: item.querySelector(`input[name^="portion_${i}_description"]`).value,
                sequenceNumber: i + 1, // Ensure sequence number is set
                measureUnit: {
                    id: isNaN(measureUnitId) ? 0 : measureUnitId, // if new, will be 0 or based on template
                    name: item.querySelector(`input[name^="portion_${i}_measureUnit_name"]`).value,
                    abbreviation: item.querySelector(`input[name^="portion_${i}_measureUnit_abbreviation"]`).value,
                },
            });
        });
        
        // If currentFoodDataForEditing exists, it means we are editing something based on a template.
        // We should use its fdcId to signal to backend this is a *new* version of it.
        // The backend logic ensures that a *new* negative ID is created for `my_foods.json`.
        // The `fdcId` in the POST request body is now used to indicate the source/template if positive,
        // or a signal to create a fully new one if 0/negative.
        if (currentFoodDataForEditing && currentFoodDataForEditing.fdcId > 0) {
            foodData.fdcId = currentFoodDataForEditing.fdcId; // Pass the original foundational fdcId as a reference
        }

        saveFoodToMyFoods(foodData);
    });

    addNutrientButton.addEventListener('click', () => {
        const index = nutrientsContainer.children.length;
        addNutrientToForm({ nutrient: {id: 0, name: '', number: '', rank: 0, unitName: 'g'}, amount: 0 }, index);
    });

    addPortionButton.addEventListener('click', () => {
        const index = portionsContainer.children.length;
        addPortionToForm({ id: 0, amount: 1, gramWeight: 100, portionDescription: '', sequenceNumber: index +1, measureUnit: { id: 0, name: '', abbreviation: ''} }, index);
    });
    
    loadMyFoodsButton.addEventListener('click', fetchMyFoods);

    // --- Initial Load ---
    fetchMyFoods(); // Load existing custom foods on page load

}); 