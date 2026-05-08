"""Serializers for the trips API."""
from rest_framework import serializers


class TripInputSerializer(serializers.Serializer):
    """Validates trip planning input."""

    current_location = serializers.CharField(
        max_length=500,
        help_text="Current location (address or 'lat,lng')"
    )
    pickup_location = serializers.CharField(
        max_length=500,
        help_text="Pickup location (address or 'lat,lng')"
    )
    dropoff_location = serializers.CharField(
        max_length=500,
        help_text="Dropoff location (address or 'lat,lng')"
    )
    current_cycle_used = serializers.FloatField(
        min_value=0,
        max_value=70,
        default=0,
        help_text="Hours already used in 70-hour/8-day cycle"
    )


class StopSerializer(serializers.Serializer):
    """A stop along the route."""

    type = serializers.ChoiceField(
        choices=["pickup", "dropoff", "fuel", "rest_break", "sleep", "cycle_rest"]
    )
    location = serializers.DictField(help_text="{'lat': float, 'lng': float}")
    mile_marker = serializers.FloatField()
    arrival_time = serializers.CharField()
    departure_time = serializers.CharField()
    duration_hours = serializers.FloatField()
    description = serializers.CharField()


class LogSegmentSerializer(serializers.Serializer):
    """A single duty status segment within a daily log."""

    status = serializers.ChoiceField(
        choices=["OFF", "SB", "D", "ON"],
        help_text="OFF=Off Duty, SB=Sleeper Berth, D=Driving, ON=On Duty Not Driving"
    )
    start_hour = serializers.FloatField(help_text="Start time as hour of day (0-24)")
    end_hour = serializers.FloatField(help_text="End time as hour of day (0-24)")
    duration_hours = serializers.FloatField()
    location = serializers.CharField(required=False, allow_blank=True)
    remark = serializers.CharField(required=False, allow_blank=True)


class DailyLogSerializer(serializers.Serializer):
    """A single day's ELD log (24-hour period)."""

    date = serializers.CharField(help_text="Date string YYYY-MM-DD")
    day_number = serializers.IntegerField(help_text="Day number in the trip (1-based)")
    segments = LogSegmentSerializer(many=True)
    total_off_duty = serializers.FloatField()
    total_sleeper = serializers.FloatField()
    total_driving = serializers.FloatField()
    total_on_duty = serializers.FloatField()
    total_miles = serializers.FloatField()
    remarks = serializers.ListField(child=serializers.CharField())


class TripResultSerializer(serializers.Serializer):
    """The complete trip planning result."""

    total_distance_miles = serializers.FloatField()
    total_duration_hours = serializers.FloatField()
    route_coordinates = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text="Array of [lng, lat] coordinate pairs for the route polyline"
    )
    stops = StopSerializer(many=True)
    daily_logs = DailyLogSerializer(many=True)
    summary = serializers.DictField()
