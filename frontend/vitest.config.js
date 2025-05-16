import { defineConfig } from 'vitest/config';
import vue from '@vitejs/plugin-vue'; // Required for Vue SFC support in Vitest

export default defineConfig({
  plugins: [
    vue(), // Use vue plugin
  ],
  test: {
    globals: true, // Allows using describe, it, expect etc. without importing
    environment: 'jsdom', // Or 'happy-dom' for a faster alternative
    deps: {
      // Ensure that an inlined dependency is transformed with specific loaders.
      // This might be needed if you encounter issues with untranspiled packages.
      // inline: [/^(?!.*vitest).*$/], 
    },
    // Optional: Setup file for global mocks or configurations
    // setupFiles: './tests/unit/setup.js',
    coverage: {
      provider: 'v8', // or 'istanbul'
      reporter: ['text', 'json', 'html'],
      reportsDirectory: './tests/unit/coverage',
      all: true, // Include all files in coverage, not just tested ones
      include: ['src/**'],
      exclude: [
        'src/main.js', 
        'src/router/index.js', 
        'src/services/api.js', // Exclude if it's just API calls
        'src/**/index.js', // Or other specific index files
        '**/*.config.js', 
        '**/*.d.ts',
        'src/App.vue', // Usually App.vue has minimal logic for unit tests
      ]
    },
  },
  // Resolve aliases if you use them (e.g., @ pointing to src)
  resolve: {
    alias: {
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
}); 