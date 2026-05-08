import React, { useState } from 'react';
import TripForm from './components/TripForm';
import MapView from './components/MapView';
import ELDLogSheet from './components/ELDLogSheet';
import { planTrip } from './services/api';

function App() {
  const [tripResult, setTripResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('map');

  const handleSubmit = async (formData) => {
    setLoading(true);
    setError(null);
    try {
      const result = await planTrip(formData);
      setTripResult(result);
      setActiveTab('map');
    } catch (err) {
      const message = err.response?.data?.error || err.message || 'Failed to plan trip';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600 rounded-lg flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900">ELD Trip Planner</h1>
              <p className="text-sm text-gray-500">FMCSA HOS-Compliant Route Planning</p>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-6 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Form */}
          <div className="lg:col-span-1">
            <TripForm onSubmit={handleSubmit} loading={loading} />

            {/* Error Display */}
            {error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Summary Card */}
            {tripResult?.summary && (
              <div className="mt-4 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Trip Summary</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Distance</span>
                    <span className="font-medium">{tripResult.summary.total_distance_miles} mi</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Driving Time</span>
                    <span className="font-medium">{tripResult.summary.total_driving_hours} hrs</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Total Trip Time</span>
                    <span className="font-medium">{tripResult.summary.total_trip_hours} hrs</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Days</span>
                    <span className="font-medium">{tripResult.summary.number_of_days}</span>
                  </div>
                  <hr className="my-2" />
                  <div className="flex justify-between">
                    <span className="text-gray-600">Fuel Stops</span>
                    <span className="font-medium">{tripResult.summary.fuel_stops}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Rest Breaks</span>
                    <span className="font-medium">{tripResult.summary.rest_breaks}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Sleep Stops</span>
                    <span className="font-medium">{tripResult.summary.sleep_stops}</span>
                  </div>
                </div>
              </div>
            )}

            {tripResult?.current_location && tripResult?.pickup_location && tripResult?.dropoff_location && (
              <div className="mt-4 bg-white rounded-lg shadow-sm border border-gray-200 p-4">
                <h3 className="font-semibold text-gray-900 mb-3">Resolved Addresses</h3>
                <div className="space-y-2 text-sm text-gray-700">
                  <div>
                    <span className="font-medium">Current:</span> {tripResult.current_location}
                  </div>
                  <div>
                    <span className="font-medium">Pickup:</span> {tripResult.pickup_location}
                  </div>
                  <div>
                    <span className="font-medium">Dropoff:</span> {tripResult.dropoff_location}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Right Panel - Results */}
          <div className="lg:col-span-2">
            {tripResult ? (
              <div>
                {/* Tabs */}
                <div className="flex border-b border-gray-200 mb-4">
                  <button
                    onClick={() => setActiveTab('map')}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'map'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                  >
                    Route Map
                  </button>
                  <button
                    onClick={() => setActiveTab('logs')}
                    className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${activeTab === 'logs'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                      }`}
                  >
                    ELD Logs ({tripResult.daily_logs?.length || 0} days)
                  </button>
                </div>

                {/* Tab Content */}
                {activeTab === 'map' && (
                  <MapView
                    coordinates={tripResult.route_coordinates}
                    stops={tripResult.stops}
                  />
                )}
                {activeTab === 'logs' && (
                  <div className="space-y-6">
                    {tripResult.daily_logs?.map((log, idx) => (
                      <ELDLogSheet key={idx} log={log} />
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
                <svg className="w-16 h-16 text-gray-300 mx-auto mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1}
                    d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                </svg>
                <h3 className="text-lg font-medium text-gray-500">Enter trip details to get started</h3>
                <p className="text-sm text-gray-400 mt-2">
                  Plan your route with FMCSA-compliant HOS scheduling
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
