/**
 * API service for communicating with the Django backend.
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000, // 60 seconds - route calculation can take time
});

/**
 * Plan a trip with HOS-compliant scheduling.
 *
 * @param {Object} tripData
 * @param {string} tripData.current_location
 * @param {string} tripData.pickup_location
 * @param {string} tripData.dropoff_location
 * @param {number} tripData.current_cycle_used
 * @returns {Promise<Object>} Trip plan result
 */
export async function planTrip(tripData) {
  const response = await apiClient.post('/trip-plan/', tripData);
  return response.data;
}

export async function fetchLocationSuggestions(query) {
  const response = await apiClient.get('/place-suggestions/', {
    params: { q: query },
  });
  return response.data;
}

/**
 * Health check
 */
export async function healthCheck() {
  const response = await apiClient.get('/health/');
  return response.data;
}

export default apiClient;
