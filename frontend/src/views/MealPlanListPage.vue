<template>
  <div class="meal-plan-list-page">
    <div class="page-header">
      <h1>Meal Plans</h1>
      <router-link to="/create-meal-plan" class="create-button">
        + Create New Meal Plan
      </router-link>
    </div>

    <div v-if="loading" class="loading-message">
      Loading meal plans...
    </div>

    <div v-else-if="error" class="error-message">
      <p>Error loading meal plans: {{ error }}</p>
      <button @click="fetchMealPlans" class="retry-button">Retry</button>
    </div>

    <div v-else-if="mealPlans.length === 0" class="empty-state">
      <p>No meal plans found.</p>
      <router-link to="/create-meal-plan" class="create-button">
        Create your first meal plan
      </router-link>
    </div>

    <div v-else class="meal-plans-grid">
      <div
        v-for="plan in mealPlans"
        :key="plan.id"
        class="meal-plan-card"
      >
        <div class="card-header">
          <h3>{{ plan.name }}</h3>
          <div class="card-actions">
            <button @click="viewPlan(plan)" class="action-button view-button">
              👁️ View
            </button>
            <button @click="editPlan(plan)" class="action-button edit-button">
              ✏️ Edit
            </button>
            <button @click="deletePlan(plan)" class="action-button delete-button">
              🗑️ Delete
            </button>
          </div>
        </div>

        <div class="card-content">
          <div class="plan-details">
            <div class="detail-row">
              <span class="label">Duration:</span>
              <span>{{ plan.duration_days }} days</span>
            </div>
            <div class="detail-row">
              <span class="label">Servings per day:</span>
              <span>{{ plan.servings_per_day_per_person }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Target people:</span>
              <span>{{ plan.target_people_profiles?.length || 0 }} people</span>
            </div>
            <div class="detail-row">
              <span class="label">Components:</span>
              <span>{{ plan.plan_items?.length || 0 }} components</span>
            </div>
          </div>

          <div v-if="plan.notes" class="plan-notes">
            <span class="label">Notes:</span>
            <p>{{ plan.notes }}</p>
          </div>

          <div class="plan-meta">
            <div class="created-date">
              Created: {{ formatDate(plan.creation_date) }}
            </div>
            <div v-if="plan.last_modified_date !== plan.creation_date" class="modified-date">
              Modified: {{ formatDate(plan.last_modified_date) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div v-if="planToDelete" class="modal-overlay" @click.self="cancelDelete">
      <div class="modal-content">
        <h3>Delete Meal Plan</h3>
        <p>Are you sure you want to delete "{{ planToDelete.name }}"?</p>
        <p class="warning-text">This action cannot be undone.</p>
        <div class="modal-actions">
          <button @click="cancelDelete" class="cancel-button">Cancel</button>
          <button @click="confirmDelete" class="confirm-delete-button">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

const router = useRouter();
const mealPlans = ref([]);
const loading = ref(false);
const error = ref(null);
const planToDelete = ref(null);

const fetchMealPlans = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await axios.get(`${API_BASE_URL}/mealplans/`);
    mealPlans.value = response.data.results || response.data;
    console.log('Fetched meal plans:', mealPlans.value);
  } catch (err) {
    console.error('Error fetching meal plans:', err);
    error.value = err.response?.data?.detail || err.message || 'Failed to load meal plans';
  } finally {
    loading.value = false;
  }
};

const viewPlan = (plan) => {
  // For now, just log the plan - you can implement a view page later
  console.log('Viewing plan:', plan);
  // Future: router.push({ name: 'ViewMealPlan', params: { id: plan.id } });
  alert(`View functionality for "${plan.name}" would go here.\n\nPlan has ${plan.plan_items?.length || 0} components and targets ${plan.target_people_profiles?.length || 0} people.`);
};

const editPlan = (plan) => {
  // For now, navigate to create plan page with query param
  // Future: Pass the plan data to edit mode
  router.push({ name: 'CreateMealPlan', query: { edit: plan.id } });
};

const deletePlan = (plan) => {
  planToDelete.value = plan;
};

const cancelDelete = () => {
  planToDelete.value = null;
};

const confirmDelete = async () => {
  if (!planToDelete.value) return;
  
  try {
    await axios.delete(`${API_BASE_URL}/mealplans/${planToDelete.value.id}/`);
    mealPlans.value = mealPlans.value.filter(plan => plan.id !== planToDelete.value.id);
    planToDelete.value = null;
    console.log('Meal plan deleted successfully');
  } catch (err) {
    console.error('Error deleting meal plan:', err);
    error.value = err.response?.data?.detail || err.message || 'Failed to delete meal plan';
    planToDelete.value = null;
  }
};

const formatDate = (dateString) => {
  if (!dateString) return 'Unknown';
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

onMounted(() => {
  fetchMealPlans();
});
</script>

<style scoped>
.meal-plan-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  flex-wrap: wrap;
  gap: 15px;
}

.page-header h1 {
  margin: 0;
  color: var(--color-heading);
}

.create-button {
  background-color: var(--color-primary);
  color: var(--color-button-text);
  padding: 12px 20px;
  border-radius: 6px;
  text-decoration: none;
  font-weight: bold;
  transition: opacity 0.2s;
  border: none;
  cursor: pointer;
  display: inline-block;
}

.create-button:hover {
  opacity: 0.9;
}

.loading-message,
.error-message,
.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: var(--color-text-secondary);
}

.error-message {
  color: var(--color-text);
}

.retry-button {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: var(--color-primary);
  color: var(--color-button-text);
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.meal-plans-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.meal-plan-card {
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px var(--shadow-color);
  transition: transform 0.2s, box-shadow 0.2s;
}

.meal-plan-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px var(--shadow-color);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  gap: 10px;
}

.card-header h3 {
  margin: 0;
  color: var(--color-heading);
  flex: 1;
  word-break: break-word;
}

.card-actions {
  display: flex;
  gap: 5px;
  flex-shrink: 0;
}

.action-button {
  padding: 6px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
  transition: opacity 0.2s;
}

.action-button:hover {
  opacity: 0.8;
}

.view-button {
  background-color: #2196F3;
  color: white;
}

.edit-button {
  background-color: #FF9800;
  color: white;
}

.delete-button {
  background-color: #F44336;
  color: white;
}

.card-content {
  color: var(--color-text);
}

.plan-details {
  margin-bottom: 15px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 4px 0;
}

.label {
  font-weight: bold;
  color: var(--color-text-secondary);
  margin-right: 10px;
}

.plan-notes {
  margin-bottom: 15px;
  padding: 10px;
  background-color: var(--color-input-bg);
  border-radius: 4px;
  border: 1px solid var(--color-border);
}

.plan-notes p {
  margin: 5px 0 0 0;
  font-style: italic;
  color: var(--color-text-secondary);
}

.plan-meta {
  font-size: 0.85em;
  color: var(--color-text-secondary);
  border-top: 1px solid var(--color-border);
  padding-top: 10px;
}

.modified-date {
  margin-top: 4px;
}

/* Modal Styles */
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
  background-color: var(--color-background);
  padding: 25px;
  border-radius: 8px;
  max-width: 400px;
  width: 90%;
  box-shadow: 0 5px 15px rgba(0,0,0,0.3);
  color: var(--color-text);
}

.modal-content h3 {
  margin-top: 0;
  margin-bottom: 15px;
  color: var(--color-heading);
}

.warning-text {
  color: #F44336;
  font-weight: bold;
  margin-bottom: 20px;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.cancel-button {
  padding: 10px 20px;
  background-color: var(--color-border);
  color: var(--color-text);
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.confirm-delete-button {
  padding: 10px 20px;
  background-color: #F44336;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

/* Responsive Design */
@media (max-width: 768px) {
  .meal-plans-grid {
    grid-template-columns: 1fr;
  }
  
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .card-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .card-actions {
    justify-content: flex-start;
    margin-top: 10px;
  }
  
  .detail-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style> 