# System Design Document - ELD Trip Planner

## 1. Architecture Overview

### High-Level Architecture
```
User Browser (React SPA)
    │
    ├── TripForm → POST /api/trip-plan/
    │                    │
    │                    ▼
    │              Django REST API
    │                    │
    │         ┌──────────┼──────────┐
    │         ▼          ▼          ▼
    │    Routing Svc  HOS Engine  Log Generator
    │    (ORS API)   (Simulation) (ELD Format)
    │         │          │          │
    │         └──────────┼──────────┘
    │                    │
    │                    ▼
    │              JSON Response
    │                    │
    ├── MapView ◄────────┤ (route_coordinates, stops)
    └── ELDLogSheet ◄────┘ (daily_logs)
```

### Data Flow
1. User enters: current_location, pickup_location, dropoff_location, current_cycle_used
2. Backend geocodes addresses → coordinates
3. Backend calls ORS Directions API → route polyline + distance + duration
4. HOS Engine simulates the trip step-by-step → timeline of events
5. Log Generator converts timeline → daily ELD logs (24-hr grids)
6. Response includes: route coords, stops, daily logs, summary
7. Frontend renders: map with route/stops, ELD log grids with canvas

### Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| TripForm | Collect and validate user input |
| Routing Service | Geocoding + route calculation via ORS |
| HOS Engine | Time-based simulation of FMCSA rules |
| Log Generator | Convert timeline → 24-hour ELD log format |
| MapView | Render route polyline + stop markers |
| ELDLogSheet | Draw FMCSA-compliant log grid on canvas |

## 2. Critical Thinking

### Hardest Parts
1. **HOS Engine State Machine**: Tracking multiple overlapping limits (11hr, 14hr, 8hr break, 70hr cycle) simultaneously
2. **Midnight Boundary Splitting**: Events that span midnight must be split across daily logs
3. **Fuel Stop Interaction with Breaks**: A 30-min fuel stop can satisfy the break requirement
4. **Cycle Exhaustion**: When 70-hour limit is hit mid-trip, need 34-hour restart

### Common Mistakes
- Dividing total hours by limits instead of simulating step-by-step
- Forgetting that off-duty time does NOT extend the 14-hour window
- Not resetting the 30-min break clock after a qualifying break
- Counting off-duty time toward the 70-hour cycle (it shouldn't)
- Not handling the case where pickup/dropoff on-duty time pushes into limits

### Edge Cases
- Trip starts with only 2 hours left in cycle → immediate 34-hr restart needed
- Very short trip (< 1 hour) → single day, minimal log
- Very long trip (3000+ miles) → multiple sleep stops, multiple days
- Pickup/dropoff activity pushes past 14-hour window → must sleep before continuing
- Fuel stop coincides with break requirement → satisfies both

### State Variables (HOS Engine)
```python
current_time          # Simulation clock
driving_hours_today   # 0-11 (resets after 10hr off)
window_elapsed        # 0-14 (resets after 10hr off)
driving_since_break   # 0-8 (resets after 30min break)
cycle_hours_used      # 0-70 (rolling 8-day, resets after 34hr)
miles_since_fuel      # 0-1000 (resets at fuel stop)
miles_driven_total    # Cumulative trip miles
duty_status           # Current: OFF, SB, D, ON
```

## 3. API Design

### POST /api/trip-plan/

**Request:**
```json
{
  "current_location": "Dallas, TX",
  "pickup_location": "Houston, TX",
  "dropoff_location": "Los Angeles, CA",
  "current_cycle_used": 20.0
}
```

**Response:**
```json
{
  "total_distance_miles": 1547.3,
  "total_duration_hours": 22.8,
  "route_coordinates": [[lng, lat], ...],
  "stops": [
    {
      "type": "pickup|dropoff|fuel|rest_break|sleep",
      "location": {"lat": 29.76, "lng": -95.37},
      "mile_marker": 245.0,
      "arrival_time": "2025-01-15T09:30:00",
      "departure_time": "2025-01-15T10:30:00",
      "duration_hours": 1.0,
      "description": "Loading/pickup operations"
    }
  ],
  "daily_logs": [
    {
      "date": "2025-01-15",
      "day_number": 1,
      "segments": [
        {
          "status": "OFF|SB|D|ON",
          "start_hour": 0.0,
          "end_hour": 8.0,
          "duration_hours": 8.0,
          "location": "Dallas, TX",
          "remark": "Off duty"
        }
      ],
      "total_off_duty": 10.5,
      "total_sleeper": 0.0,
      "total_driving": 9.5,
      "total_on_duty": 4.0,
      "total_miles": 522.5,
      "remarks": ["08:00 - ON - Pre-trip inspection", ...]
    }
  ],
  "summary": {
    "total_distance_miles": 1547.3,
    "total_driving_hours": 22.8,
    "total_trip_hours": 48.5,
    "number_of_stops": 7,
    "number_of_days": 3,
    "fuel_stops": 1,
    "rest_breaks": 2,
    "sleep_stops": 2
  }
}
```

### GET /api/health/
Returns `{"status": "ok", "service": "eld-trip-planner"}`
