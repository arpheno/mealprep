<template>
  <div id="app-container" :class="{ 'dark-theme': isDarkMode }">
    <nav>
      <router-link to="/create-meal-component">Create Meal Component</router-link>
      <router-link to="/create-meal-plan">Create Meal Plan</router-link>
      <button @click="toggleDarkMode" class="theme-toggle">
        {{ isDarkMode ? '☀️ Light Mode' : '🌙 Dark Mode' }}
      </button>
    </nav>
    <router-view/>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';

const isDarkMode = ref(false);

const toggleDarkMode = () => {
  isDarkMode.value = !isDarkMode.value;
  localStorage.setItem('darkMode', isDarkMode.value.toString());
};

onMounted(() => {
  const storedDarkMode = localStorage.getItem('darkMode');
  if (storedDarkMode) {
    isDarkMode.value = storedDarkMode === 'true';
  } else {
    // Optional: Check for system preference if no explicit preference is stored
    // isDarkMode.value = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }
});

// Watch for changes in isDarkMode to apply/remove class from body or html if needed for global styles
// For now, applying to #app-container is sufficient if all styles are scoped or within it.
/*
watch(isDarkMode, (newVal) => {
  // Example: If you wanted to set it on the body for truly global modal styles etc.
  // if (newVal) {
  //   document.body.classList.add('dark-theme-body');
  // } else {
  //   document.body.classList.remove('dark-theme-body');
  // }
});
*/
</script>

<style>
/* Basic Color Scheme using CSS Variables */
:root {
  --color-background: #ffffff;
  --color-text: #2c3e50;
  --color-heading: var(--color-text); /* Default heading color */
  --color-primary: #42b983;
  --color-nav-bg: #f8f9fa;
  --color-border: #eee;
  --color-border-hover: #ddd; /* Slightly darker for hover */
  --color-border-hover-light: #f5f5f5; /* Lighter for subtle lines */
  --color-input-bg: #fff;
  --color-input-border: #ccc;
  --color-background-soft: #f9f9f9; /* Default soft background */
  --color-button-bg: #4CAF50;
  --color-button-text: #ffffff;
  --shadow-color: rgba(0,0,0,0.1);
  --color-text-secondary: #555;

  /* Nutrient Bar Colors */
  --color-nutrient-bar-safe: #4CAF50;    /* Green */
  --color-nutrient-bar-warning: #FFC107; /* Amber/Yellow */
  --color-nutrient-bar-danger: #F44336;   /* Red */
  --color-nutrient-bar-default: #E0E0E0; /* Light grey for track or default bar */
}

.dark-theme {
  --color-background: #1a1a1a; /* Darker background */
  --color-text: #e0e0e0;       /* Lighter text */
  --color-heading: var(--color-text); /* Heading color in dark */
  --color-primary: #42b983;    /* Keep primary or adjust if needed */
  --color-nav-bg: #2c3e50;     /* Darker nav */
  --color-border: #3a3a3a;       /* Darker borders */
  --color-border-hover: #4a4a4a; /* Darker hover border */
  --color-border-hover-light: #2c2c2c; /* Darker subtle line for dark */
  --color-input-bg: #252525;
  --color-input-border: #454545;
  --color-background-soft: #2c3e50; /* Soft background for dark - e.g., tooltip bg */
  --color-button-bg: #42b983;
  --color-button-text: #1a1a1a;
  --shadow-color: rgba(255,255,255,0.05);
  --color-text-secondary: #aaa;

  /* Nutrient Bar Colors - Dark Theme (can be same or adjusted) */
  --color-nutrient-bar-safe: #4CAF50;
  --color-nutrient-bar-warning: #FFC107;
  --color-nutrient-bar-danger: #F44336;
  --color-nutrient-bar-default: #424242; /* Darker grey for track in dark mode */
}

/* Global Resets and Theming moved to global.css */

/* Apply variables */
#app-container {
  /* font-family and smoothing moved to html, body for broader application */
  color: var(--color-text); /* This can be inherited from body now */
  background-color: var(--color-background); /* This can also be inherited if body covers all */
  min-height: 100%; /* Ensure background covers full viewport height/app container fills body */
  display: flex; /* Added to make footer (if any) easier to manage */
  flex-direction: column; /* Added */
}

nav {
  padding: 15px;
  text-align: center;
  background-color: var(--color-nav-bg);
  margin-bottom: 20px;
  box-shadow: 0 2px 4px var(--shadow-color);
  display: flex; /* For aligning toggle button */
  justify-content: center;
  align-items: center;
  gap: 20px;
}

nav a {
  font-weight: bold;
  color: var(--color-text);
  margin: 0 10px;
  text-decoration: none;
}

nav a.router-link-exact-active {
  color: var(--color-primary);
}

.theme-toggle {
  padding: 8px 12px;
  background-color: var(--color-input-bg);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  cursor: pointer;
}

/* Ensure other components use these variables */
/* Example for MealComponentForm.vue inputs (can be added there or globally) */
/*
input[type="text"],
input[type="number"],
textarea,
select {
  background-color: var(--color-input-bg);
  color: var(--color-text);
  border: 1px solid var(--color-input-border);
}

button {
  background-color: var(--color-button-bg);
  color: var(--color-button-text);
}
*/
</style>
