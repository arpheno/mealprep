<template>
  <div class="macronutrient-pie-chart-container">
    <Pie v-if="chartDataInternal" :data="chartDataInternal" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { Pie } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  ArcElement, // Needed for Pie charts
} from 'chart.js';

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  ArcElement
);

const props = defineProps({
  // chartData prop expects an object with labels and datasets
  // e.g., { labels: ['Protein', 'Fat', 'Carbs'], datasets: [{ data: [10, 20, 70], backgroundColor: ['#FF0000', '#00FF00', '#0000FF'] }] }
  chartData: {
    type: Object,
    required: true,
    validator: (value) => {
      return value && Array.isArray(value.labels) && Array.isArray(value.datasets) &&
             value.datasets.every(dataset => Array.isArray(dataset.data) && Array.isArray(dataset.backgroundColor));
    }
  },
  titleText: {
    type: String,
    default: 'Macronutrient Breakdown'
  }
});

// Use an internal computed property to ensure reactivity if props.chartData itself is rebuilt
const chartDataInternal = computed(() => props.chartData);

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top',
      labels: {
         color: document.documentElement.style.getPropertyValue('--text-color-primary') || '#000000',
      }
    },
    title: {
      display: true,
      text: props.titleText,
      color: document.documentElement.style.getPropertyValue('--text-color-primary') || '#000000',
      font: {
        size: 16
      }
    },
    tooltip: {
      callbacks: {
        label: function(context) {
          let label = context.label || '';
          if (label) {
            label += ': ';
          }
          if (context.parsed !== null) {
            // Assuming data is in grams for the tooltip, like the title suggests
            // If it were percentages, we would calculate the percentage here from the raw data.
            // For now, displaying raw value with 'g'
            label += context.parsed.toFixed(1) + 'g'; 
          }
          return label;
        }
      }
    }
  }
}));
</script>

<style scoped>
.macronutrient-pie-chart-container {
  width: 100%;
  /* height: 300px; You might want a fixed height or let it be determined by aspect ratio */
  /* max-width: 400px; /* Optional: constrain max width */
  /* margin: auto; /* Center if max-width is set */
  padding: 10px;
  box-sizing: border-box;
  background-color: var(--background-color-secondary); 
  border-radius: 4px;
  height: 300px; /* Match bar chart height for consistency in grid */
}
</style> 