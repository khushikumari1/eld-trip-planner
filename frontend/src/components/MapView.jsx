import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';

// Fix default marker icons in React-Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

// Custom marker icons by stop type
const stopIcons = {
  pickup: new L.DivIcon({
    className: 'custom-marker',
    html: '<div class="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg border-2 border-white">P</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  }),
  dropoff: new L.DivIcon({
    className: 'custom-marker',
    html: '<div class="w-8 h-8 bg-red-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg border-2 border-white">D</div>',
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  }),
  fuel: new L.DivIcon({
    className: 'custom-marker',
    html: '<div class="w-7 h-7 bg-yellow-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg border-2 border-white">⛽</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  }),
  rest_break: new L.DivIcon({
    className: 'custom-marker',
    html: '<div class="w-7 h-7 bg-orange-500 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg border-2 border-white">☕</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  }),
  sleep: new L.DivIcon({
    className: 'custom-marker',
    html: '<div class="w-7 h-7 bg-purple-600 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-lg border-2 border-white">🛏</div>',
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  }),
};

/** Component to fit map bounds to route */
function FitBounds({ coordinates }) {
  const map = useMap();

  useEffect(() => {
    if (coordinates && coordinates.length > 0) {
      const latLngs = coordinates.map(([lng, lat]) => [lat, lng]);
      const bounds = L.latLngBounds(latLngs);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [coordinates, map]);

  return null;
}

/**
 * Map component showing route polyline and stop markers.
 */
function MapView({ coordinates, stops }) {
  if (!coordinates || coordinates.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 text-center">
        <p className="text-gray-500">No route data available</p>
      </div>
    );
  }

  // Convert [lng, lat] to [lat, lng] for Leaflet
  const routePositions = coordinates.map(([lng, lat]) => [lat, lng]);
  const center = routePositions[Math.floor(routePositions.length / 2)];

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
      <div className="h-[500px]">
        <MapContainer center={center} zoom={6} className="h-full w-full">
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <FitBounds coordinates={coordinates} />

          {/* Route polyline */}
          <Polyline
            positions={routePositions}
            color="#2563eb"
            weight={4}
            opacity={0.8}
          />

          {/* Stop markers */}
          {stops?.map((stop, idx) => (
            <Marker
              key={idx}
              position={[stop.location.lat, stop.location.lng]}
              icon={stopIcons[stop.type] || stopIcons.rest_break}
            >
              <Popup>
                <div className="text-sm">
                  <p className="font-semibold capitalize">{stop.type.replace('_', ' ')}</p>
                  <p className="text-gray-600">{stop.description}</p>
                  <p className="text-gray-500 text-xs mt-1">
                    Mile {stop.mile_marker} • {stop.duration_hours} hrs
                  </p>
                </div>
              </Popup>
            </Marker>
          ))}
        </MapContainer>
      </div>

      {/* Stops Legend */}
      <div className="p-4 border-t border-gray-200">
        <h4 className="text-sm font-medium text-gray-700 mb-2">Stops</h4>
        <div className="flex flex-wrap gap-3 text-xs">
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-green-500 rounded-full"></span> Pickup
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-red-500 rounded-full"></span> Dropoff
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-yellow-500 rounded-full"></span> Fuel
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-orange-500 rounded-full"></span> Break
          </span>
          <span className="flex items-center gap-1">
            <span className="w-3 h-3 bg-purple-600 rounded-full"></span> Sleep
          </span>
        </div>

        {/* Stops list */}
        {stops && stops.length > 0 && (
          <div className="mt-3 max-h-48 overflow-y-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-gray-500 border-b">
                  <th className="text-left py-1">Type</th>
                  <th className="text-left py-1">Mile</th>
                  <th className="text-left py-1">Duration</th>
                  <th className="text-left py-1">Description</th>
                </tr>
              </thead>
              <tbody>
                {stops.map((stop, idx) => (
                  <tr key={idx} className="border-b border-gray-100">
                    <td className="py-1 capitalize">{stop.type.replace('_', ' ')}</td>
                    <td className="py-1">{stop.mile_marker}</td>
                    <td className="py-1">{stop.duration_hours} hr</td>
                    <td className="py-1 text-gray-600 truncate max-w-[150px]">{stop.description}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

export default MapView;
