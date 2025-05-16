import { mount } from '@vue/test-utils';
import MealPlanForm from '@/components/MealPlanForm.vue';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ref, nextTick } from 'vue';

// Mock the api service if it's imported directly and used in onMounted or watchers
vi.mock('@/services/api.js', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    // Add other methods if your component uses them
  },
}));

// Mock axios if it's used directly (it seems to be in MealPlanForm for initial data fetch)
vi.mock('axios', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { results: [] } }) ), // Default mock for get
    post: vi.fn(() => Promise.resolve({ data: {} }) ), // Default mock for post
  }
}));

describe('MealPlanForm.vue', () => {
  let wrapper;

  // Helper function to create default props or initial state for refs
  const createInitialState = () => ({
    planData: ref({
      name: 'Test Plan',
      notes: 'A plan for testing',
      duration_days: 7,
      servings_per_day_per_person: 1,
      target_people_ids: [],
      meal_component_ids: [],
      target_people_profiles: [],
      selected_person_profiles_in_form: [],
    }),
    allMealComponents: ref([]),
    allPersonProfiles: ref([]),
    addedMealComponents: ref([]),
    selectedPeopleObjects: ref([]),
    currentPlanTargets: ref({}),
    // ... any other refs that livePlanNutritionalBreakdown or other parts might need
  });

  beforeEach(async () => {
    // Reset mocks before each test if needed
    const axiosInstance = await import('axios');
    axiosInstance.default.get.mockResolvedValue({ data: { results: [] } }); // Ensure onMounted fetches don't fail

    const apiService = await import('@/services/api.js');
    // Ensure api.post returns a promise that resolves to an object with a data property
    apiService.default.post.mockImplementation((url) => {
      if (url === '/calculate-nutritional-targets/') {
        return Promise.resolve({ data: { /* mock target data if needed, or empty */ } });
      }
      return Promise.resolve({ data: {} }); // Default for other posts
    });

    wrapper = mount(MealPlanForm, {
      global: {
        stubs: ['router-link'], // Stubbing router-link
      }
    });
    await nextTick(); 
  });

  it('renders a form', () => {
    expect(wrapper.find('form.meal-plan-form').exists()).toBe(true);
  });

  describe('livePlanNutritionalBreakdown', () => {
    // Example: Test energy conversion and basic structure
    it('should correctly convert kJ to kcal for Energy and initialize structure', async () => {
      // 1. Set up the reactive dependencies for livePlanNutritionalBreakdown
      wrapper.vm.planData.duration_days = 1; // Simplify duration for easier calcs
      wrapper.vm.allPersonProfiles.value = [
        { id: 1, name: 'Person A', personalized_drvs: { 'Energy (kcal)': { rda: 2000, ul: null, unit: 'kcal', fdc_nutrient_number: '208' } } }
      ];
      wrapper.vm.selectedPeopleObjects.value = wrapper.vm.allPersonProfiles.value;
      wrapper.vm.planData.target_people_ids = [1];

      // Mock currentPlanTargets to provide FDC numbers and units
      wrapper.vm.currentPlanTargets.value = {
        'Energy': { rda: 2000, ul: 3000, unit: 'kcal', fdc_nutrient_number: '208' }, // Backend provides kcal
        'Protein': { rda: 50, ul: null, unit: 'g', fdc_nutrient_number: '203' }
      };
      
      wrapper.vm.addedMealComponents.value = [
        {
          id: 'mc1',
          component: {
            id: 1,
            name: 'Energy Component (kJ)',
            frequency: 'DAILY',
            nutritional_totals: {
              'Energy (kJ)': { amount: 4184, unit: 'kJ' }, // Approx 1000 kcal
            }
          },
          assigned_people_ids: [1]
        }
      ];
      
      await nextTick(); // Allow computed property to update

      // 2. Access the computed property
      const breakdown = wrapper.vm.livePlanNutritionalBreakdown;
      console.log('Test 1: breakdown.overallSummary', JSON.stringify(breakdown.overallSummary, null, 2));
      
      // 3. Assertions
      // Check overall summary
      expect(breakdown.overallSummary['General & Other']).toBeDefined();
      const energyDataOverall = breakdown.overallSummary['General & Other']['Energy (kcal)'];
      expect(energyDataOverall).toBeDefined();
      expect(energyDataOverall.unit).toBe('kcal');
      expect(energyDataOverall.total).toBeCloseTo(1000, 0); // 4184 kJ * 0.239006 approx 1000 kcal
      expect(energyDataOverall.fdc_nutrient_number).toBe('208');

      // Check per-person breakdown
      expect(breakdown.perPersonBreakdown[1]).toBeDefined();
      const energyDataPerson = breakdown.perPersonBreakdown[1].nutrientGroups['General & Other']['Energy (kcal)'];
      expect(energyDataPerson).toBeDefined();
      expect(energyDataPerson.unit).toBe('kcal');
      expect(energyDataPerson.total).toBeCloseTo(1000, 0);
    });

    // Add more tests for %E calculations for macros here
    it('should calculate %E for macronutrients correctly', async () => {
        wrapper.vm.planData.duration_days = 1;
        wrapper.vm.currentPlanTargets.value = {
            'Energy': { rda: 2000, ul: null, unit: 'kcal', fdc_nutrient_number: '208' },
            'Protein': { rda: 50, ul: null, unit: 'g', fdc_nutrient_number: '203' },
            'Carbohydrate, by difference': { rda: 250, ul: null, unit: 'g', fdc_nutrient_number: '205' },
            'Total lipid (fat)': { rda: 60, ul: null, unit: 'g', fdc_nutrient_number: '204' },
        };

        wrapper.vm.addedMealComponents.value = [
            {
                id: 'mc_macros',
                component: {
                    id: 2,
                    name: 'Macro Mix',
                    frequency: 'DAILY',
                    nutritional_totals: {
                        'Energy (kcal)': { amount: 2000, unit: 'kcal' }, // From component
                        'Protein (g)': { amount: 50, unit: 'g' },         // 200 kcal
                        'Carbohydrate, by difference (g)': { amount: 225, unit: 'g' }, // 900 kcal
                        'Total lipid (fat) (g)': { amount: 100, unit: 'g' }    // 900 kcal
                    }
                },
                assigned_people_ids: [1] // Assuming one person for simplicity
            }
        ];
        
        await nextTick();
        const breakdown = wrapper.vm.livePlanNutritionalBreakdown;
        console.log('Test 2: breakdown.overallSummary', JSON.stringify(breakdown.overallSummary, null, 2));

        const macros = breakdown.overallSummary['Macronutrients'];
        expect(macros).toBeDefined();

        const protein = macros['Protein (g)'];
        expect(protein.percent_energy).toBeCloseTo((50 * 4 / 2000) * 100, 1); // 10%

        const carbs = macros['Carbohydrate, by difference (g)'];
        expect(carbs.percent_energy).toBeCloseTo((225 * 4 / 2000) * 100, 1); // 45%

        const fat = macros['Total lipid (fat) (g)'];
        expect(fat.percent_energy).toBeCloseTo((100 * 9 / 2000) * 100, 1); // 45%
    });
  });

  // describe('getMacroStyle', () => { ... });
  // describe('getPlanNutrientBarStyle', () => { ... });

}); 