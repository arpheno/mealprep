const { defineConfig } = require('@vue/cli-service')
const webpack = require('webpack')

// Attempt to read from process.env (for build time) or default
const apiBaseUrl = process.env.VITE_API_BASE_URL || 'http://localhost:5001/api'

module.exports = defineConfig({
  transpileDependencies: true,
  configureWebpack: {
    plugins: [
      new webpack.DefinePlugin({
        // Define a global constant that will be available in your Vue code
        // It's common practice to stringify string values
        'process.env.VUE_APP_API_BASE_URL': JSON.stringify(apiBaseUrl)
      })
    ]
  }
})
