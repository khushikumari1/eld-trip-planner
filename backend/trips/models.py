"""
Data models for ELD Trip Planner.

These models represent the core domain objects:
- TripRequest: The input from the user (locations + cycle hours)
- TripResult: The computed route, stops, and ELD logs
- DailyLog: A single day's ELD log with duty status segments
- LogSegment: A time segment within a daily log (one duty status period)
"""
from django.db import models
import json


class TripRequest(models.Model):
    """Stores a trip planning request."""

    current_location = models.CharField(max_length=500, help_text="Starting location address or coords")
    pickup_location = models.CharField(max_length=500, help_text="Pickup location address or coords")
    dropoff_location = models.CharField(max_length=500, help_text="Dropoff location address or coords")
    current_cycle_used = models.FloatField(
        default=0.0,
        help_text="Hours already used in the 70-hour/8-day cycle"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip: {self.current_location} → {self.pickup_location} → {self.dropoff_location}"


class TripResult(models.Model):
    """Stores the computed result for a trip request."""

    trip_request = models.OneToOneField(TripRequest, on_delete=models.CASCADE, related_name="result")
    total_distance_miles = models.FloatField(help_text="Total route distance in miles")
    total_duration_hours = models.FloatField(help_text="Total driving duration in hours (no stops)")
    route_polyline = models.TextField(help_text="Encoded polyline or JSON coordinates for map")
    stops_json = models.TextField(help_text="JSON array of all stops (fuel, rest, pickup, dropoff)")
    logs_json = models.TextField(help_text="JSON array of daily ELD logs")
    created_at = models.DateTimeField(auto_now_add=True)

    def get_stops(self):
        return json.loads(self.stops_json)

    def get_logs(self):
        return json.loads(self.logs_json)

    def __str__(self):
        return f"Result for Trip #{self.trip_request_id}: {self.total_distance_miles:.0f} mi"
