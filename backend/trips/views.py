"""
API Views for ELD Trip Planner.

Main endpoint: POST /api/trip-plan/
Takes trip inputs, returns route + stops + ELD logs.
"""
import logging
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import TripInputSerializer, TripResultSerializer
from .services.routing import (
    geocode,
    resolve_address,
    suggest_places,
    get_route,
    interpolate_point_on_route,
    get_location_name,
    RoutingError,
)
from .services.hos_engine import run_hos_simulation, TimelineEvent, DutyStatus
from .services.log_generator import generate_daily_logs

logger = logging.getLogger(__name__)


class TripPlanView(APIView):
    """
    Plan a trip with HOS-compliant schedule.

    POST /api/trip-plan/
    Body: {
        "current_location": "Dallas, TX",
        "pickup_location": "Houston, TX",
        "dropoff_location": "Los Angeles, CA",
        "current_cycle_used": 20
    }
    """

    def post(self, request):
        serializer = TripInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data

        try:
            result = self._plan_trip(data)
            return Response(result, status=status.HTTP_200_OK)
        except RoutingError as e:
            logger.warning("Routing failure in TripPlanView: %s", str(e), exc_info=True)
            return Response(
                {"error": f"Routing error: {str(e)}"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            logger.exception("Unexpected planning error in TripPlanView")
            return Response(
                {"error": "An unexpected error occurred while planning the trip."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _plan_trip(self, data: dict) -> dict:
        """Execute the full trip planning pipeline."""
        current_coords, current_location_full = resolve_address(data["current_location"])
        pickup_coords, pickup_location_full = resolve_address(data["pickup_location"])
        dropoff_coords, dropoff_location_full = resolve_address(data["dropoff_location"])

        waypoints = [current_coords, pickup_coords, dropoff_coords]
        route = get_route(waypoints)

        total_distance = route["distance_miles"]
        total_duration = route["duration_hours"]
        coordinates = route["coordinates"]

        if total_distance <= 0 or total_duration <= 0:
            raise RoutingError("Invalid route metrics returned from the routing service.")

        segments = route.get("segments", [])
        if len(segments) >= 2:
            seg1_distance = segments[0].get("distance_miles", 0.0)
            seg1_duration = segments[0].get("duration_hours", 0.0)
            seg2_distance = segments[1].get("distance_miles", 0.0)
            seg2_duration = segments[1].get("duration_hours", 0.0)
        elif len(segments) == 1:
            seg1_distance = segments[0].get("distance_miles", total_distance)
            seg1_duration = segments[0].get("duration_hours", total_duration)
            seg2_distance = 0.0
            seg2_duration = 0.0
        else:
            seg1_distance = total_distance * 0.3
            seg1_duration = total_duration * 0.3
            seg2_distance = total_distance * 0.7
            seg2_duration = total_duration * 0.7

        pickup_name = get_location_name(pickup_coords[0], pickup_coords[1])
        dropoff_name = get_location_name(dropoff_coords[0], dropoff_coords[1])

        start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

        timeline = run_hos_simulation(
            total_distance_miles=total_distance,
            total_duration_hours=total_duration,
            current_cycle_used=data["current_cycle_used"],
            start_time=start_time,
            pickup_location_name=pickup_name,
            dropoff_location_name=dropoff_name,
            pickup_distance_miles=seg1_distance,
            pickup_duration_hours=seg1_duration,
        )

        daily_logs = generate_daily_logs(timeline, start_time)

        stops = self._build_stops(timeline, coordinates, total_distance)

        summary = {
            "total_distance_miles": round(total_distance, 1),
            "total_driving_hours": round(total_duration, 1),
            "total_trip_hours": round(
                (timeline[-1].end_time - timeline[0].start_time).total_seconds() / 3600, 1
            ) if timeline else 0,
            "number_of_stops": len(stops),
            "number_of_days": len(daily_logs),
            "fuel_stops": sum(1 for s in stops if s["type"] == "fuel"),
            "rest_breaks": sum(1 for s in stops if s["type"] == "rest_break"),
            "sleep_stops": sum(1 for s in stops if s["type"] == "sleep"),
        }

        return {
            "current_location": current_location_full,
            "pickup_location": pickup_location_full,
            "dropoff_location": dropoff_location_full,
            "total_distance_miles": round(total_distance, 1),
            "total_duration_hours": round(total_duration, 1),
            "route_coordinates": coordinates,
            "stops": stops,
            "daily_logs": daily_logs,
            "summary": summary,
        }

    def _build_stops(
        self, timeline: list, coordinates: list, total_distance: float
    ) -> list:
        """Convert timeline events into map-displayable stops."""
        stops = []

        for event in timeline:
            if event.event_type in ("driving", "off_duty"):
                continue

            stop_type_map = {
                "pickup": "pickup",
                "dropoff": "dropoff",
                "fuel": "fuel",
                "break": "rest_break",
                "sleep": "sleep",
                "cycle_rest": "sleep",
            }
            stop_type = stop_type_map.get(event.event_type, "rest_break")

            location = interpolate_point_on_route(
                coordinates, event.miles_at_start, total_distance
            )

            if location:
                stops.append({
                    "type": stop_type,
                    "location": location,
                    "mile_marker": round(event.miles_at_start, 1),
                    "arrival_time": event.start_time.isoformat(),
                    "departure_time": event.end_time.isoformat(),
                    "duration_hours": round(
                        (event.end_time - event.start_time).total_seconds() / 3600, 2
                    ),
                    "description": event.notes or event.event_type,
                })

        return stops


class PlaceSuggestionView(APIView):
    """Proxy place suggestion requests to OpenRouteService."""

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response([], status=status.HTTP_200_OK)

        try:
            suggestions = suggest_places(query)
            return Response(suggestions, status=status.HTTP_200_OK)
        except RoutingError as e:
            return Response({"error": str(e)}, status=status.HTTP_502_BAD_GATEWAY)
        except Exception:
            return Response({"error": "Suggestion service unavailable"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TripPlanHealthView(APIView):
    """Health check endpoint."""

    def get(self, request):
        return Response({"status": "ok", "service": "eld-trip-planner"})
