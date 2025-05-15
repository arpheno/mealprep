<!-- frontend/src/components/NutrientBarChart.vue -->
<template>
  <div class="nutrient-bar-chart-container">
    <Bar v-if="chartData" :data="chartData" :options="chartOptions" />
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { Bar } from 'vue-chartjs';
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement, // Needed for Line in combined charts
  LineElement,   // Needed for Line in combined charts
  LineController // Explicitly import LineController
} from 'chart.js';

ChartJS.register(
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale,
  PointElement, 
  LineElement,   
  LineController // Explicitly register LineController
);

const props = defineProps({
  nutrientName: { // e.g., "Protein (g)"
    type: String,
    required: true,
  },
  currentAmount: {
    type: Number,
    required: true,
  },
  rdaValue: {
    type: Number,
    default: null,
  },
  ulValue: { // Tolerable Upper Limit
    type: Number,
    default: null,
  },
  unit: { // e.g., "g", "mg"
    type: String,
    default: '',
  },
  barColor: {
    type: String,
    default: '#2196F3', // Default Material Blue
  },
  rdaLineColor: {
    type: String,
    default: '#4CAF50', // Material Green
  },
  ulLineColor: {
      type: String,
      default: '#F44336' // Material Red
  }
});

const chartData = computed(() => {
  if (props.currentAmount === null || props.currentAmount === undefined) return null;

  const datasets = [{
    label: `Current (${props.unit})`,
    data: [props.currentAmount],
    backgroundColor: [props.barColor],
    borderColor: [props.barColor.substring(0,7) + 'CC'], 
    borderWidth: 1,
    barPercentage: 0.6,
    categoryPercentage: 0.8,
  }];

  if (props.rdaValue !== null && props.rdaValue > 0) {
    datasets.push({
      type: 'line',
      label: `RDA (${props.unit})`,
      data: [props.rdaValue], 
      borderColor: props.rdaLineColor,
      backgroundColor: props.rdaLineColor, 
      borderWidth: 2,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: false,
      tension: 0, 
      yAxisID: 'y',
    });
  }
  
  if (props.ulValue !== null && props.ulValue > 0) {
    datasets.push({
      type: 'line',
      label: `UL (${props.unit})`,
      data: [props.ulValue],
      borderColor: props.ulLineColor,
      backgroundColor: props.ulLineColor,
      borderWidth: 2,
      pointRadius: 5,
      pointHoverRadius: 7,
      fill: false,
      tension: 0,
      yAxisID: 'y',
    });
  }

  return {
    labels: [props.nutrientName.split(' (')[0]],
    datasets: datasets,
  };
});

const chartOptions = computed(() => {
  let maxY = Math.max(props.currentAmount || 0, props.rdaValue || 0, props.ulValue || 0);
  if (maxY > 0) {
      maxY = maxY * 1.2; // Add 20% padding to the top
  } else {
      maxY = 10; // Default max if all values are 0 or null
  }

  return {
    responsive: true,
    maintainAspectRatio: false, 
    indexAxis: 'x', 
    plugins: {
      legend: {
        position: 'top',
        labels: {
          color: document.documentElement.style.getPropertyValue('--text-color-primary') || '#000000', 
        }
      },
      title: {
        display: false, 
        text: props.nutrientName,
        color: document.documentElement.style.getPropertyValue('--text-color-primary') || '#000000',
      },
      tooltip: {
        callbacks: {
          label: function(context) {
            let label = context.dataset.label || '';
            if (label) {
              label += ': ';
            }
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(2) + ` ${props.unit}`;
            }
            return label;
          }
        }
      }
    },
    scales: {
      x: {
        ticks: {
          color: document.documentElement.style.getPropertyValue('--text-color-secondary') || '#000000',
        },
        grid: {
          display: false, 
          color: document.documentElement.style.getPropertyValue('--border-color') || '#DDDDDD',
        }
      },
      y: {
        beginAtZero: true,
        max: maxY, 
        ticks: {
          color: document.documentElement.style.getPropertyValue('--text-color-secondary') || '#000000',
        },
         grid: {
          color: document.documentElement.style.getPropertyValue('--border-color') || '#DDDDDD',
        }
      },
    },
  };
});

</script>

<style scoped>
.nutrient-bar-chart-container {
  width: 100%; 
  height: 250px; 
  padding: 10px;
  box-sizing: border-box;
  background-color: var(--background-color-secondary); 
  border-radius: 4px; 
}
</style> 