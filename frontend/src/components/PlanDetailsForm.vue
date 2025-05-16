<template>
  <div class="plan-details-form-container">
    <div class="form-group">
      <label for="plan-name">Plan Name:</label>
      <input 
        type="text" 
        id="plan-name" 
        :value="name" 
        @input="$emit('update:name', $event.target.value)" 
        required 
      />
    </div>

    <div class="form-group">
      <label for="plan-description">Description:</label>
      <textarea 
        id="plan-description" 
        :value="notes" 
        @input="$emit('update:notes', $event.target.value)"
      ></textarea>
    </div>
    
    <div class="form-group">
      <label for="duration-days">Duration (days):</label>
      <input 
        type="number" 
        id="duration-days" 
        :value="durationDays" 
        @input="$emit('update:durationDays', parseInt($event.target.value, 10) || 0)" 
        min="1" 
      />
    </div>
    
    <div class="form-group">
      <label for="servings-per-day">Servings per Day (per person):</label>
      <input 
        type="number" 
        id="servings-per-day" 
        :value="servingsPerDayPerPerson" 
        @input="$emit('update:servingsPerDayPerPerson', parseInt($event.target.value, 10) || 0)" 
        min="1" 
      />
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  name: {
    type: String,
    required: true
  },
  notes: {
    type: String,
    default: ''
  },
  durationDays: {
    type: Number,
    required: true
  },
  servingsPerDayPerPerson: {
    type: Number,
    required: true
  }
});

defineEmits([
  'update:name',
  'update:notes',
  'update:durationDays',
  'update:servingsPerDayPerPerson'
]);

// No local state needed as we are directly binding to props and emitting updates.
// Input parsing for numbers is handled directly in the @input event.
</script>

<style scoped>
.plan-details-form-container {
  display: flex;
  flex-direction: column;
  gap: 15px; /* Matches original gap in MealPlanForm */
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 5px;
  font-weight: bold;
  color: var(--color-text);
}

.form-group input[type="text"],
.form-group input[type="number"],
.form-group textarea {
  padding: 10px;
  border: 1px solid var(--color-input-border);
  border-radius: 4px;
  font-size: 1em;
  background-color: var(--color-input-bg);
  color: var(--color-text);
}

.form-group input[type="text"]:focus,
.form-group input[type="number"]:focus,
.form-group textarea:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb, 66, 185, 131), 0.3);
}

.form-group textarea {
  min-height: 80px;
  resize: vertical;
}
</style> 