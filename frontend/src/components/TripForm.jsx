import React, { useState, useEffect, useRef } from 'react';
import { fetchLocationSuggestions } from '../services/api';

const MAX_CYCLE_HOURS = 70;
const MIN_CYCLE_HOURS = 0;

const escapeRegExp = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const highlightMatch = (label, query) => {
  if (!query) return label;
  const regex = new RegExp(`(${escapeRegExp(query)})`, 'gi');
  return label.split(regex).map((part, index) =>
    regex.test(part) ? (
      <span key={index} className="font-semibold text-blue-600">
        {part}
      </span>
    ) : (
      part
    )
  );
};

function LocationInput({
  label,
  name,
  value,
  placeholder,
  onTextChange,
  onSuggestionSelect,
  required,
}) {
  const [suggestions, setSuggestions] = useState([]);
  const [activeIndex, setActiveIndex] = useState(-1);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState('');
  const containerRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    const listener = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener('mousedown', listener);
    return () => document.removeEventListener('mousedown', listener);
  }, []);

  useEffect(() => {
    if (!value || value.length < 2) {
      setSuggestions([]);
      setFetchError('');
      setLoading(false);
      return;
    }

    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setFetchError('');
      try {
        const data = await fetchLocationSuggestions(value);
        if (Array.isArray(data)) {
          setSuggestions(data.slice(0, 6));
          setShowSuggestions(true);
          setActiveIndex(-1);
        } else {
          setSuggestions([]);
          setShowSuggestions(false);
        }
      } catch (error) {
        setFetchError('Unable to fetch suggestions');
        setSuggestions([]);
        setShowSuggestions(false);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => clearTimeout(debounceRef.current);
  }, [value]);

  const handleInputChange = (event) => {
    onTextChange(name, event.target.value);
    setShowSuggestions(true);
  };

  const handleSelect = (suggestion) => {
    onSuggestionSelect(name, suggestion.label, suggestion.coordinates);
    setShowSuggestions(false);
    setActiveIndex(-1);
  };

  const handleKeyDown = (event) => {
    if (!showSuggestions || !suggestions.length) return;

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveIndex((prev) => (prev + 1) % suggestions.length);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveIndex((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1));
    } else if (event.key === 'Enter') {
      if (activeIndex >= 0 && activeIndex < suggestions.length) {
        event.preventDefault();
        handleSelect(suggestions[activeIndex]);
      }
    } else if (event.key === 'Escape') {
      setShowSuggestions(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      <label htmlFor={name} className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type="text"
        value={value}
        placeholder={placeholder}
        required={required}
        onChange={handleInputChange}
        onFocus={() => value.length >= 2 && setShowSuggestions(true)}
        onKeyDown={handleKeyDown}
        aria-autocomplete="list"
        aria-controls={`${name}-suggestions`}
        aria-expanded={showSuggestions}
        aria-activedescendant={activeIndex >= 0 ? `${name}-suggestion-${activeIndex}` : undefined}
        className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm placeholder-gray-400"
      />
      {loading && (
        <div className="absolute right-3 top-3">
          <svg className="animate-spin h-4 w-4 text-blue-500" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )}
      {showSuggestions && suggestions.length > 0 && (
        <ul
          id={`${name}-suggestions`}
          role="listbox"
          className="absolute z-10 mt-1 w-full bg-white shadow-lg max-h-60 overflow-y-auto border border-gray-200 rounded-md"
        >
          {suggestions.map((suggestion, index) => (
            <li
              key={`${name}-suggestion-${index}`}
              id={`${name}-suggestion-${index}`}
              role="option"
              aria-selected={activeIndex === index}
              className={`cursor-pointer px-3 py-2 text-sm text-gray-700 flex items-center justify-between ${activeIndex === index ? 'bg-blue-50 text-blue-900' : 'hover:bg-gray-50'
                }`}
              onMouseDown={(event) => {
                event.preventDefault();
                handleSelect(suggestion);
              }}
              onMouseEnter={() => setActiveIndex(index)}
            >
              <span>{highlightMatch(suggestion.label, value)}</span>
            </li>
          ))}
        </ul>
      )}
      {fetchError && <p className="mt-1 text-xs text-red-600">{fetchError}</p>}
    </div>
  );
}

/**
 * Trip input form component.
 * Collects: current location, pickup, dropoff, cycle hours used.
 */
function TripForm({ onSubmit, loading }) {
  const [formData, setFormData] = useState({
    current_location: '',
    pickup_location: '',
    dropoff_location: '',
    current_cycle_used: '',
  });
  const [locationCoordinates, setLocationCoordinates] = useState({
    current_location: null,
    pickup_location: null,
    dropoff_location: null,
  });
  const [cycleError, setCycleError] = useState('');
  const [cycleFocused, setCycleFocused] = useState(false);

  const validateCycle = (value) => {
    if (value === '' || value === null) return 'Please enter hours used in the current cycle.';
    const numeric = Number(value);
    if (Number.isNaN(numeric)) return 'Enter a valid number.';
    if (numeric < MIN_CYCLE_HOURS) return 'Value cannot be negative.';
    if (numeric > MAX_CYCLE_HOURS) return `Value cannot exceed ${MAX_CYCLE_HOURS} hours.`;
    return '';
  };

  const handleTextChange = (name, value) => {
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
    if (name !== 'current_cycle_used') {
      setLocationCoordinates((prev) => ({ ...prev, [name]: null }));
    }
    if (name === 'current_cycle_used') {
      setCycleError(validateCycle(value));
    }
  };

  const handleSuggestionSelect = (name, label, coordinates) => {
    setFormData((prev) => ({
      ...prev,
      [name]: label,
    }));
    setLocationCoordinates((prev) => ({
      ...prev,
      [name]: coordinates,
    }));
    if (name === 'current_cycle_used') {
      setCycleError(validateCycle(label));
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const errorMessage = validateCycle(formData.current_cycle_used);
    if (errorMessage) {
      setCycleError(errorMessage);
      return;
    }

    const payload = {
      current_location: formData.current_location,
      pickup_location: formData.pickup_location,
      dropoff_location: formData.dropoff_location,
      current_cycle_used: Number(formData.current_cycle_used),
    };

    if (locationCoordinates.current_location) {
      payload.current_location = `${locationCoordinates.current_location[1]}, ${locationCoordinates.current_location[0]}`;
    }
    if (locationCoordinates.pickup_location) {
      payload.pickup_location = `${locationCoordinates.pickup_location[1]}, ${locationCoordinates.pickup_location[0]}`;
    }
    if (locationCoordinates.dropoff_location) {
      payload.dropoff_location = `${locationCoordinates.dropoff_location[1]}, ${locationCoordinates.dropoff_location[0]}`;
    }

    onSubmit(payload);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Trip Details</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <LocationInput
          label="Current Location"
          name="current_location"
          value={formData.current_location}
          placeholder="e.g., Bangalore, India or 12.9716, 77.5946"
          required
          onTextChange={handleTextChange}
          onSuggestionSelect={handleSuggestionSelect}
        />

        <LocationInput
          label="Pickup Location"
          name="pickup_location"
          value={formData.pickup_location}
          placeholder="e.g., Berlin, Germany or Midtown Toronto, Canada"
          required
          onTextChange={handleTextChange}
          onSuggestionSelect={handleSuggestionSelect}
        />

        <LocationInput
          label="Dropoff Location"
          name="dropoff_location"
          value={formData.dropoff_location}
          placeholder="e.g., Sydney Opera House, Australia or São Paulo, Brazil"
          required
          onTextChange={handleTextChange}
          onSuggestionSelect={handleSuggestionSelect}
        />

        <div>
          <label htmlFor="current_cycle_used" className="block text-sm font-medium text-gray-700 mb-1">
            Current Cycle Used (hours)
          </label>
          <input
            type="number"
            id="current_cycle_used"
            name="current_cycle_used"
            value={formData.current_cycle_used}
            onChange={(event) => handleTextChange('current_cycle_used', event.target.value)}
            onFocus={() => setCycleFocused(true)}
            onBlur={() => setCycleFocused(false)}
            min={MIN_CYCLE_HOURS}
            max={MAX_CYCLE_HOURS}
            step="0.25"
            inputMode="decimal"
            aria-describedby="cycle-helper cycle-error"
            className={`w-full px-3 py-2 border rounded-md shadow-sm text-sm focus:outline-none focus:ring-2 focus:border-blue-500 ${cycleError ? 'border-red-300 focus:ring-red-200' : 'border-gray-300 focus:ring-blue-200'
              }`}
          />
          <p
            id="cycle-helper"
            className={`mt-1 text-xs ${cycleError ? 'text-red-600' : 'text-gray-500'}`}
          >
            {cycleFocused
              ? 'Manually enter hours used in the current 70-hour/8-day cycle. Decimal values are allowed.'
              : 'Hours used in 70-hour/8-day cycle (0-70)'}
          </p>
          {cycleError && (
            <p id="cycle-error" className="mt-1 text-xs text-red-600">
              {cycleError}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 px-4 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Planning Route...
            </span>
          ) : (
            'Plan Trip'
          )}
        </button>
      </form>

      <div className="mt-4 p-3 bg-blue-50 rounded-md">
        <p className="text-xs text-blue-700 font-medium mb-1">FMCSA HOS Rules Applied:</p>
        <ul className="text-xs text-blue-600 space-y-0.5">
          <li>• 11-hour driving limit</li>
          <li>• 14-hour driving window</li>
          <li>• 30-min break after 8 hrs driving</li>
          <li>• 10-hour off-duty reset</li>
          <li>• 70-hour/8-day cycle limit</li>
        </ul>
      </div>
    </div>
  );
}

export default TripForm;
