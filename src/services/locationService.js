/**
 * Service for location-related operations
 */
export const LocationService = {
  /**
   * Search for locations based on a search term
   * @param {string} searchTerm - The text to search for
   * @param {number} limit - Maximum number of results to return
   * @returns {Promise<Array>} - Array of location objects
   */
  searchLocations: async (searchTerm, limit = 10) => {
    try {
      const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';
      const response = await fetch(`${API_URL}/locations/search?query=${encodeURIComponent(searchTerm)}&limit=${limit}`);
      
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Search results:', data.results); // Debug log
      return data.results;
    } catch (error) {
      console.error('Error searching locations:', error);
      return [];
    }
  }
};

// Mock data for development without backend
const mockLocations = [
  { id: '1', name: 'Central Park', latitude: 40.785091, longitude: -73.968285 },
  { id: '2', name: 'Times Square', latitude: 40.758896, longitude: -73.985130 },
  { id: '3', name: 'Brooklyn Bridge', latitude: 40.705778, longitude: -73.996111 },
  { id: '4', name: 'Empire State Building', latitude: 40.748817, longitude: -73.985428 },
  { id: '5', name: 'Statue of Liberty', latitude: 40.689247, longitude: -74.044502 },
  { id: '6', name: 'Main Street', latitude: 40.7128, longitude: -74.0060 },
  { id: '7', name: 'Broadway', latitude: 40.7590, longitude: -73.9845 },
  { id: '8', name: 'North Avenue', latitude: 40.7308, longitude: -74.0027 },
  { id: '9', name: 'Bank Street', latitude: 40.7359, longitude: -74.0151 },
  { id: '10', name: 'Madison Avenue', latitude: 40.7539, longitude: -73.9810 }
];

/**
 * Mock search function for development without backend
 */
function mockSearch(searchTerm, limit) {
  const normalizedTerm = searchTerm.toLowerCase();
  const results = mockLocations.filter(location => 
    location.name.toLowerCase().includes(normalizedTerm)
  );
  return results.slice(0, limit);
} 