import axios from 'axios';

const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    // You can add other common headers here, like Authorization tokens
  },
});

// Optional: Add a request interceptor for things like adding auth tokens
// apiClient.interceptors.request.use(config => {
//   const token = localStorage.getItem('user-token'); // Example: Get token from local storage
//   if (token) {
//     config.headers.Authorization = `Bearer ${token}`;
//   }
//   return config;
// }, error => {
//   return Promise.reject(error);
// });

// Optional: Add a response interceptor for global error handling
// apiClient.interceptors.response.use(response => {
//   return response;
// }, error => {
//   // Handle common errors globally (e.g., 401 Unauthorized, redirect to login)
//   if (error.response && error.response.status === 401) {
//     // router.push('/login'); // Assuming you have access to your Vue router instance
//     console.error('Unauthorized, redirecting to login...');
//   }
//   return Promise.reject(error);
// });

export default apiClient; 