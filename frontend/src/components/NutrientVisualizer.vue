<!-- NutrientVisualizer.vue -->
<template>
  <div ref="visualizerContainer" class="nutrient-visualizer-container"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import * as THREE from 'three';

const props = defineProps({
  nutritionalData: { // Expects data from calculatedNutritionalBreakdown
    type: Object,
    required: true,
  },
  nutrientsToDisplay: { // e.g., ['Protein (g)', 'Vitamin C (mg)', 'Iron (mg)']
    type: Array,
    default: () => ['Protein (g)', 'Carbohydrate, by difference (g)', 'Total lipid (fat) (g)', 'Iron (mg)', 'Vitamin C, total ascorbic acid (mg)', 'Calcium (mg)']
  },
  barHeightScale: {
    type: Number,
    default: 5 // Adjust to make bars reasonably sized relative to RDA
  }
});

const visualizerContainer = ref(null);
let scene, camera, renderer, animationFrameId;

const MAX_BAR_HEIGHT = 10; // Max visual height for a bar if it meets/exceeds 100% RDA or a scaled value

function initThreeScene() {
  if (!visualizerContainer.value) return;

  scene = new THREE.Scene();
  scene.background = new THREE.Color(0x282c34); // Match dark theme background

  const width = visualizerContainer.value.clientWidth;
  const height = Math.min(width * 0.6, 400); // Keep a reasonable aspect ratio, max height 400px
  visualizerContainer.value.style.height = `${height}px`;

  camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
  camera.position.set(5, 5, 15); // Adjusted camera position
  camera.lookAt(5, 0, 0); // Look at the center of where bars will be

  renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  visualizerContainer.value.appendChild(renderer.domElement);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
  scene.add(ambientLight);
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
  directionalLight.position.set(5, 10, 7.5);
  scene.add(directionalLight);
  
  // Add a simple ground plane
  const planeGeometry = new THREE.PlaneGeometry(20, 20);
  const planeMaterial = new THREE.MeshStandardMaterial({ color: 0x444444, side: THREE.DoubleSide });
  const plane = new THREE.Mesh(planeGeometry, planeMaterial);
  plane.rotation.x = -Math.PI / 2;
  plane.position.y = -0.05; // Slightly below bars
  scene.add(plane);

  updateVisualization();
  animate();
}

function updateVisualization() {
  if (!scene) return;

  // Clear previous bars
  scene.children.forEach(child => {
    if (child.userData.isNutrientBar || child.userData.isRdaLine) {
      scene.remove(child);
      if (child.geometry) child.geometry.dispose();
      if (child.material) child.material.dispose();
    }
  });

  let barPositionX = 0;
  const barWidth = 0.8;
  const barDepth = 0.8;
  const spacing = 1.2;

  props.nutrientsToDisplay.forEach((nutrientKeyWithUnit) => {
    let nutrientData = null;
    // Find nutrient data in the grouped structure
    for (const group in props.nutritionalData) {
      if (props.nutritionalData[group][nutrientKeyWithUnit]) {
        nutrientData = props.nutritionalData[group][nutrientKeyWithUnit];
        break;
      }
    }

    if (nutrientData && typeof nutrientData.total === 'number') {
      const totalAmount = nutrientData.total;
      const rda = nutrientData.rda; // Assuming rda is 'nutrient_default_rda_female'

      let barHeight = 0;
      let percentageOfRDA = 0;

      if (rda && rda > 0) {
        percentageOfRDA = (totalAmount / rda);
        barHeight = Math.min(percentageOfRDA * props.barHeightScale, MAX_BAR_HEIGHT); 
      } else {
        barHeight = Math.min(totalAmount * 0.1, MAX_BAR_HEIGHT * 0.5); 
      }
      barHeight = Math.max(barHeight, 0.01); // Ensure a minimum visible height

      let barColor = 0x007bff; // Default blue
      if (rda && rda > 0) {
        if (percentageOfRDA < 0.8) barColor = 0xffc107; // Yellow (low)
        else if (percentageOfRDA >= 0.8 && percentageOfRDA <= 1.2) barColor = 0x28a745; // Green (good)
        else barColor = 0xdc3545; // Red (high)
        
        if (nutrientData.ul && nutrientData.ul > 0 && totalAmount > nutrientData.ul) {
            barColor = 0x6f0000; // Darker red if exceeding UL
        }
      }

      const geometry = new THREE.BoxGeometry(barWidth, barHeight, barDepth);
      const material = new THREE.MeshStandardMaterial({ color: barColor });
      const bar = new THREE.Mesh(geometry, material);
      bar.position.set(barPositionX, barHeight / 2, 0);
      bar.userData.isNutrientBar = true;
      scene.add(bar);

      if (rda && rda > 0) {
        const rdaLineHeight = Math.min(props.barHeightScale, MAX_BAR_HEIGHT); 
        const lineMaterial = new THREE.LineBasicMaterial({ color: 0xffffff, linewidth: 2 });
        const points = [];
        points.push(new THREE.Vector3(barPositionX - barWidth / 2 - 0.1, rdaLineHeight, barDepth / 2 + 0.1));
        points.push(new THREE.Vector3(barPositionX + barWidth / 2 + 0.1, rdaLineHeight, barDepth / 2 + 0.1));
        const lineGeometry = new THREE.BufferGeometry().setFromPoints(points);
        const rdaLine = new THREE.Line(lineGeometry, lineMaterial);
        rdaLine.userData.isRdaLine = true;
        scene.add(rdaLine);
      }
      barPositionX += spacing;
    }
  });
   if(renderer) renderer.render(scene, camera);
}

function animate() {
  animationFrameId = requestAnimationFrame(animate);
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
}

function handleResize() {
    if (!visualizerContainer.value || !camera || !renderer) return;
    const width = visualizerContainer.value.clientWidth;
    const height = Math.min(width * 0.6, 400);
    visualizerContainer.value.style.height = `${height}px`;

    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height);
    updateVisualization(); 
}

onMounted(() => {
  nextTick(() => { 
    initThreeScene();
    window.addEventListener('resize', handleResize);
  });
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
  if (scene) {
    scene.traverse(object => {
      if (object.geometry) object.geometry.dispose();
      if (object.material) {
        if (Array.isArray(object.material)) {
          object.material.forEach(material => material.dispose());
        } else {
          object.material.dispose();
        }
      }
    });
  }
  if (renderer) {
    renderer.dispose();
    if (renderer.domElement && visualizerContainer.value && visualizerContainer.value.contains(renderer.domElement)) {
         visualizerContainer.value.removeChild(renderer.domElement);
    }
  }
});

watch(() => props.nutritionalData, () => {
  if (scene) { 
      updateVisualization();
  }
}, { deep: true });

watch(() => props.nutrientsToDisplay, () => {
    if (scene) {
        updateVisualization();
    }
}, { deep: true });

</script>

<style scoped>
.nutrient-visualizer-container {
  width: 100%;
  margin-top: 20px;
  border: 1px solid var(--border-color);
  border-radius: 4px;
  background-color: var(--background-color-tertiary); 
  position: relative; 
  overflow: hidden; 
}
</style> 