import { createRouter, createWebHistory } from 'vue-router';
// import HomeView from '../views/HomeView.vue'; // Commented out
import CreateMealComponentPage from '../views/CreateMealComponentPage.vue';
import CreateMealPlanPage from '../views/CreateMealPlanPage.vue';
import MealPlanListPage from '../views/MealPlanListPage.vue';

const routes = [
  // { // Commented out Home route
  //   path: '/',
  //   name: 'home',
  //   component: HomeView
  // },
  // { // Commented out About route
  //   path: '/about',
  //   name: 'about',
  //   component: () => import(/* webpackChunkName: "about" */ '../views/AboutView.vue')
  // },
  {
    path: '/', // Let's make our new page the default for now
    name: 'CreateMealComponentDefault',
    component: CreateMealComponentPage
  },
  {
    path: '/create-meal-component',
    name: 'CreateMealComponent',
    component: CreateMealComponentPage
  },
  {
    path: '/create-meal-plan',
    name: 'CreateMealPlan',
    component: CreateMealPlanPage
  },
  {
    path: '/meal-plans',
    name: 'MealPlanList',
    component: MealPlanListPage
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

export default router; 