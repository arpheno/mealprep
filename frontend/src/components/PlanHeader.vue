<template>
  <div class="plan-header-container">
    <div class="main-title-area">
      <h2>Create/Edit Meal Plan</h2>
    </div>
    <div class="plan-target-people">
      <span
        v-for="person in selectedPeople"
        :key="person.id"
        class="person-circle"
        :title="person.name"
      >
        {{ getProfileInitials(person.name) }}
        <button 
          type="button" 
          @click="requestRemovePerson(person)" 
          class="remove-person-from-plan-btn" 
          title="Remove person from plan"
        >
          &times;
        </button>
      </span>
      <button
        type="button"
        @click="showPersonProfileSelector = !showPersonProfileSelector"
        class="add-person-btn"
        title="Add person to plan"
      >
        +
      </button>
      <div v-if="showPersonProfileSelector" class="person-profile-selector">
        <ul v-if="availablePeopleToAdd.length > 0">
          <li
            v-for="person in availablePeopleToAdd"
            :key="person.id"
            @click="requestAddPerson(person)"
          >
            {{ person.name }}
          </li>
        </ul>
        <p v-else>No other person profiles available to add.</p>
        <router-link to="/create-person-profile" class="create-profile-link">Create New Profile</router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, defineProps, defineEmits } from 'vue';

const props = defineProps({
  allPersonProfiles: {
    type: Array,
    required: true,
    default: () => []
  },
  selectedPeople: {
    type: Array,
    required: true,
    default: () => []
  }
});

const emit = defineEmits(['add-person', 'remove-person']);

const showPersonProfileSelector = ref(false);

const availablePeopleToAdd = computed(() => {
  const selectedIds = new Set(props.selectedPeople.map(p => p.id));
  return props.allPersonProfiles.filter(p => !selectedIds.has(p.id));
});

const getProfileInitials = (name) => {
  if (!name) return '?';
  const parts = name.split(' ');
  if (parts.length > 1 && parts[0] && parts[parts.length - 1]) {
    return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
  }
  return name.substring(0, 2).toUpperCase();
};

const requestAddPerson = (person) => {
  emit('add-person', person);
  showPersonProfileSelector.value = false; // Close selector after adding
};

const requestRemovePerson = (person) => {
  emit('remove-person', person);
};
</script>

<style scoped>
.plan-header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  /*border-bottom: 1px solid var(--color-border);
  padding-bottom: 15px; */
}

.main-title-area h2 {
  margin: 0; /* Remove default margin from h2 */
  color: var(--color-text);
}

.plan-target-people {
  display: flex;
  align-items: center;
  gap: 8px;
  position: relative; /* For positioning the selector */
}

.person-circle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px; /* Slightly larger for the remove button */
  height: 36px;
  border-radius: 50%;
  background-color: var(--color-primary-light);
  color: var(--color-primary-dark);
  font-weight: bold;
  font-size: 0.8em;
  border: 1px solid var(--color-primary);
  box-shadow: 0 1px 2px rgba(0,0,0,0.1);
  cursor: default;
  position: relative; /* For positioning the remove button */
}

.remove-person-from-plan-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background-color: var(--color-danger, #e74c3c);
  color: white;
  border: none;
  font-size: 12px;
  font-weight: bold;
  line-height: 16px;
  text-align: center;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 1px 2px rgba(0,0,0,0.2);
  opacity: 0; /* Hidden by default */
  transition: opacity 0.2s ease, background-color 0.2s ease;
}

.person-circle:hover .remove-person-from-plan-btn {
  opacity: 1; /* Show on hover */
}

.remove-person-from-plan-btn:hover {
  background-color: var(--color-danger-dark, #c0392b);
}


.add-person-btn {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background-color: var(--color-button-bg);
  color: var(--color-button-text);
  border: none;
  font-size: 1.2em;
  font-weight: bold;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s;
}

.add-person-btn:hover {
  background-color: var(--color-primary-dark);
}

.person-profile-selector {
  position: absolute;
  top: 100%; /* Position below the add button */
  right: 0;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  padding: 10px;
  margin-top: 5px;
  min-width: 200px;
  z-index: 100; /* Ensure it's above other elements */
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.person-profile-selector ul {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 150px;
  overflow-y: auto;
}

.person-profile-selector li {
  padding: 8px 10px;
  cursor: pointer;
  color: var(--color-text);
  border-bottom: 1px solid var(--color-border-hover);
}

.person-profile-selector li:last-child {
  border-bottom: none;
}

.person-profile-selector li:hover {
  background-color: var(--color-primary-light);
  color: var(--color-primary-dark);
}

.person-profile-selector p {
  font-size: 0.9em;
  color: var(--color-text-secondary);
  padding: 5px 0;
  text-align: center;
}

.create-profile-link {
  display: block;
  text-align: center;
  margin-top: 10px;
  padding: 8px;
  background-color: var(--color-primary);
  color: var(--color-button-text);
  border-radius: 4px;
  text-decoration: none;
  font-size: 0.9em;
}

.create-profile-link:hover {
  background-color: var(--color-primary-dark);
}
</style> 