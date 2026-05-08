# Loom Video Script (3-5 minutes)

## Intro (30 seconds)
"Hi, I'm going to walk you through my ELD Trip Planner application. This is a full-stack app built with Django and React that takes trip details as input and generates FMCSA-compliant route plans with ELD daily logs."

## Problem Statement (30 seconds)
"The problem: Commercial truck drivers must comply with FMCSA Hours of Service regulations. These include an 11-hour driving limit, a 14-hour duty window, mandatory 30-minute breaks after 8 hours of driving, 10-hour off-duty resets, and a 70-hour rolling 8-day cycle limit. Planning a multi-day trip while staying compliant is complex. This app automates that planning."

## Architecture (45 seconds)
"The architecture: React frontend with Tailwind CSS communicates with a Django REST Framework backend. The backend has three core services:

1. A Routing Service that uses OpenRouteService for geocoding and route calculation
2. An HOS Simulation Engine - this is the heart of the app - it simulates the trip step-by-step, tracking all HOS state variables and inserting mandatory breaks at the correct times
3. A Log Generator that converts the simulation timeline into FMCSA-format daily logs

The key design decision was building a time-based simulation engine rather than simply dividing hours. This ensures accurate compliance with overlapping rules."

## HOS Logic Deep Dive (60 seconds)
"Let me show you the HOS engine. It maintains state for: driving hours today, the 14-hour window elapsed time, cumulative driving since last break, and cycle hours used. 

When simulating driving, it calculates the minimum time until ANY limit is hit, drives that amount, then handles the limit - whether that's a 30-minute break, a 10-hour sleep reset, or a 34-hour cycle restart.

For example, if a driver has driven 7.5 hours, the engine knows a 30-minute break is needed in 30 minutes. If the 14-hour window expires first, it triggers a 10-hour reset instead. The engine handles all these interactions correctly."

## Demo Walkthrough (90 seconds)
"Let me demo the app. I'll enter:
- Current location: Dallas, TX
- Pickup: Houston, TX  
- Dropoff: Los Angeles, CA
- Cycle used: 20 hours

[Click Plan Trip]

The map shows the route with color-coded markers for pickup, dropoff, fuel stops, rest breaks, and sleep stops. You can see the route polyline and click markers for details.

Switching to the ELD Logs tab - here are the daily log sheets. Each one is a 24-hour grid matching the FMCSA format exactly. You can see:
- Off-duty time in gray
- Sleeper berth in purple  
- Driving time in blue
- On-duty not driving in red

The vertical lines show transitions between statuses. The totals on the right add up to 24 hours per day. The remarks section shows location at each status change.

For this trip, we get 3 days of logs with proper breaks and resets inserted automatically."

## Closing (15 seconds)
"The code is clean, well-documented, and follows real FMCSA regulations from the official driver's guide. Thanks for watching."
