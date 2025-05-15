<template>
  <div class="create-meal-component-page">
    <h1>Create New Meal Component</h1>
    <MealComponentForm />
  </div>
</template>

<script setup>
import MealComponentForm from '@/components/MealComponentForm.vue';
// Any page-specific logic can go here
</script>

<style scoped>
.create-meal-component-page {
  max-width: 800px;
  margin: 20px auto;
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}
h1 {
  text-align: center;
  margin-bottom: 20px;
}
</style> 