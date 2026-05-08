"""
Routing Service - OpenRouteService Integration

Handles:
- Geocoding addresses to coordinates
- Calculating routes between waypoints
- Returning distance, duration, and polyline coordinates
- Interpolating intermediate points for fuel/rest stops
"""
import logging
import math
import requests
from django.conf import settings
from typing import Tuple, List, Dict, Optional


ORS_BASE_URL = "https://api.openrouteservice.org"

logger = logging.getLogger(__name__)
METERS_TO_MILES = 0.000621371
SECONDS_TO_HOURS = 1 / 3600.0


class RoutingError(Exception):
    """Raised when routing service encounters an error."""
    pass


COUNTRY_CODE_MAP = {
    "USA": "United States",
    "US": "United States",
    "UNITED STATES OF AMERICA": "United States",
    "UK": "United Kingdom",
    "GB": "United Kingdom",
    "GREAT BRITAIN": "United Kingdom",
    "IND": "India",
    "IN": "India",
    "UAE": "United Arab Emirates",
    "AE": "United Arab Emirates",
    "JP": "Japan",
    "CAN": "Canada",
    "CA": "Canada",
}


def _expand_country_name(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = value.strip()
    return COUNTRY_CODE_MAP.get(normalized.upper(), normalized)


def _add_unique_component(components: List[str], value: Optional[str]) -> None:
    if not value:
        return
    value = value.strip()
    if not value:
        return
    for existing in components:
        if existing.lower() == value.lower() or value.lower() in existing.lower() or existing.lower() in value.lower():
            return
    components.append(value)


def _build_full_address(props: Dict, original_address: str) -> str:
    street = "".join(
        part for part in [props.get("housenumber"), props.get("street")] if part
    ).strip()
    if not street:
        street = props.get("name") or props.get("label") or props.get("locality")

    locality = props.get("locality") or props.get("city") or props.get("town") or props.get("village") or props.get("district")
    region = props.get("region") or props.get("region_a") or props.get("state")
    postcode = props.get("postal_code") or props.get("postcode") or props.get("postal")
    country = _expand_country_name(props.get("country") or props.get("country_code"))

    components: List[str] = []
    _add_unique_component(components, street)
    _add_unique_component(components, locality)
    _add_unique_component(components, region)
    _add_unique_component(components, postcode)
    _add_unique_component(components, country)

    if len(components) >= 3:
        return ", ".join(components)

    label = props.get("label") or original_address
    if country and country not in label:
        return f"{label}, {country}"
    return label


def resolve_address(address: str) -> Tuple[Tuple[float, float], str]:
    """
    Geocode an input address and return coordinates plus a fully qualified address.
    """
    if "," in address:
        parts = address.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip())
                lng = float(parts[1].strip())
                return (lng, lat), f"{lat:.6f}, {lng:.6f}"
            except ValueError:
                pass

    url = f"{ORS_BASE_URL}/geocode/search"
    params = {
        "api_key": settings.ORS_API_KEY,
        "text": address,
        "size": 1,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data.get("features"):
            raise RoutingError(f"Could not geocode address: {address}")

        feature = data["features"][0]
        coords = feature["geometry"]["coordinates"]
        normalized = _build_full_address(feature.get("properties", {}), address)
        return (coords[0], coords[1]), normalized

    except requests.RequestException as e:
        raise RoutingError(f"Geocoding request failed: {str(e)}")


def suggest_places(query: str, size: int = 6) -> List[Dict]:
    """Return place suggestions from ORS for the given query."""
    if not query or not query.strip():
        return []

    url = f"{ORS_BASE_URL}/geocode/autocomplete"
    params = {
        "api_key": settings.ORS_API_KEY,
        "text": query,
        "size": size,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        features = data.get("features", [])

        if not features:
            # Fallback to general search when autocomplete returns nothing.
            url = f"{ORS_BASE_URL}/geocode/search"
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            features = data.get("features", [])

        results = []
        for feature in features:
            properties = feature.get("properties", {})
            label = properties.get("label") or properties.get("name") or query
            coords = feature.get("geometry", {}).get("coordinates", [])
            if len(coords) == 2:
                results.append({
                    "label": label,
                    "coordinates": coords,
                })
        return results
    except requests.RequestException as e:
        raise RoutingError(f"Place suggestion request failed: {str(e)}")


def geocode(address: str) -> Tuple[float, float]:
    """
    Convert an address string to (longitude, latitude) coordinates.
    Also accepts 'lat,lng' format directly.

    Returns: (longitude, latitude) tuple (ORS uses lng,lat order)
    """
    coords, _ = resolve_address(address)
    return coords


def _haversine_distance_miles(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Return the great-circle distance between two points in miles."""
    radius_miles = 3958.8
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_miles * c


def _validate_route_metrics(distance_meters: float, duration_seconds: float, coordinates: List[List[float]]) -> None:
    if distance_meters <= 0 or duration_seconds <= 0:
        raise RoutingError("Route response returned zero distance or duration.")

    if not coordinates or len(coordinates) < 2:
        raise RoutingError("Route geometry is invalid or incomplete.")

    distance_miles = distance_meters * METERS_TO_MILES
    duration_hours = duration_seconds * SECONDS_TO_HOURS
    if duration_hours <= 0:
        raise RoutingError("Route response returned an invalid duration.")

    average_speed = distance_miles / duration_hours
    if average_speed < 5 or average_speed > 90:
        raise RoutingError(
            f"Route metrics are inconsistent: average speed {average_speed:.1f} mph. "
            "Please verify your input or try a different route."
        )


def _decode_geometry(geometry):
    if isinstance(geometry, str):
        return decode_polyline(geometry)
    if isinstance(geometry, dict):
        return geometry.get("coordinates", [])
    raise RoutingError("Unsupported route geometry format from ORS.")


def _map_route_segments(segments: List[Dict]) -> List[Dict]:
    mapped_segments = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        distance = segment.get("distance", 0.0)
        duration = segment.get("duration", 0.0)
        mapped_segments.append({
            **segment,
            "distance_miles": distance * METERS_TO_MILES,
            "duration_hours": duration * SECONDS_TO_HOURS,
        })
    return mapped_segments


def get_route(waypoints: List[Tuple[float, float]]) -> Dict:
    """
    Get driving route between waypoints using ORS Directions API.

    Args:
        waypoints: List of (longitude, latitude) tuples

    Returns:
        Dict with keys:
        - distance_meters: total distance in meters
        - duration_seconds: total driving duration in seconds
        - distance_miles: total distance in miles
        - duration_hours: total driving duration in hours
        - coordinates: list of [lng, lat] pairs for the route polyline
        - segments: list of segment details between waypoints
    """
    url = f"{ORS_BASE_URL}/v2/directions/driving-hgv"
    params = {
        "api_key": settings.ORS_API_KEY,
    }
    headers = {
        "Content-Type": "application/json",
    }
    body = {
        "coordinates": waypoints,
        "instructions": True,
        "geometry": True,
        "geometry_simplify": False,
        "units": "m",
    }

    try:
        response = requests.post(url, json=body, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        logger.debug("ORS route response: %s", data)

        if not data.get("routes"):
            raise RoutingError("No route returned by OpenRouteService.")

        route = data["routes"][0]
        geometry = route.get("geometry")
        coordinates = _decode_geometry(geometry)

        segments = route.get("segments", [])
        distance_meters = route.get("summary", {}).get("distance") if route.get("summary") else None
        duration_seconds = route.get("summary", {}).get("duration") if route.get("summary") else None

        if distance_meters is None or duration_seconds is None:
            distance_meters = sum(seg.get("distance", 0.0) for seg in segments)
            duration_seconds = sum(seg.get("duration", 0.0) for seg in segments)

        logger.debug(
            "Parsed route metrics: distance_meters=%s duration_seconds=%s segment_count=%s",
            distance_meters,
            duration_seconds,
            len(segments),
        )

        _validate_route_metrics(distance_meters, duration_seconds, coordinates)

        mapped_segments = _map_route_segments(segments)
        if len(mapped_segments) != max(0, len(waypoints) - 1):
            logger.warning(
                "Unexpected ORS segment count: expected %s, got %s",
                max(0, len(waypoints) - 1),
                len(mapped_segments),
            )

        return {
            "distance_meters": distance_meters,
            "duration_seconds": duration_seconds,
            "distance_miles": distance_meters * METERS_TO_MILES,
            "duration_hours": duration_seconds * SECONDS_TO_HOURS,
            "coordinates": coordinates,
            "segments": mapped_segments,
        }

    except requests.RequestException as e:
        logger.exception("ORS route request failed")
        raise RoutingError(f"Route calculation failed: {str(e)}")


def decode_polyline(encoded: str) -> List[List[float]]:
    """Decode an encoded polyline string into a list of [lng, lat] coordinates."""
    coordinates = []
    index = 0
    lat = 0
    lng = 0

    while index < len(encoded):
        # Decode latitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lat += (~(result >> 1) if (result & 1) else (result >> 1))

        # Decode longitude
        shift = 0
        result = 0
        while True:
            b = ord(encoded[index]) - 63
            index += 1
            result |= (b & 0x1F) << shift
            shift += 5
            if b < 0x20:
                break
        lng += (~(result >> 1) if (result & 1) else (result >> 1))

        coordinates.append([lng / 1e5, lat / 1e5])

    return coordinates


def _interpolate_point_on_route(
    coordinates: List[List[float]],
    target_distance_miles: float,
    total_distance_miles: float,
) -> Optional[Dict]:
    """Find the approximate coordinate at a target distance along the route."""
    if not coordinates:
        return None
    if target_distance_miles <= 0:
        return {"lng": coordinates[0][0], "lat": coordinates[0][1]}
    if target_distance_miles >= total_distance_miles:
        return {"lng": coordinates[-1][0], "lat": coordinates[-1][1]}

    cumulative = [0.0]
    for i in range(1, len(coordinates)):
        prev = coordinates[i - 1]
        curr = coordinates[i]
        prev_lat, prev_lng = prev[1], prev[0]
        curr_lat, curr_lng = curr[1], curr[0]
        segment_distance = _haversine_distance_miles(prev_lat, prev_lng, curr_lat, curr_lng)
        cumulative.append(cumulative[-1] + segment_distance)

    if cumulative[-1] <= 0:
        # fallback to simple index-based approach
        fraction = target_distance_miles / max(total_distance_miles, 1.0)
        idx = int(fraction * (len(coordinates) - 1))
        idx = max(0, min(idx, len(coordinates) - 1))
        return {"lng": coordinates[idx][0], "lat": coordinates[idx][1]}

    for i in range(1, len(cumulative)):
        if target_distance_miles <= cumulative[i]:
            segment_start = coordinates[i - 1]
            segment_end = coordinates[i]
            segment_start_distance = cumulative[i - 1]
            segment_length = cumulative[i] - segment_start_distance
            if segment_length <= 0:
                return {"lng": segment_end[0], "lat": segment_end[1]}
            fraction = (target_distance_miles - segment_start_distance) / segment_length
            lng = segment_start[0] + (segment_end[0] - segment_start[0]) * fraction
            lat = segment_start[1] + (segment_end[1] - segment_start[1]) * fraction
            return {"lng": lng, "lat": lat}

    return {"lng": coordinates[-1][0], "lat": coordinates[-1][1]}


def interpolate_point_on_route(
    coordinates: List[List[float]],
    target_distance_miles: float,
    total_distance_miles: float,
) -> Optional[Dict]:
    return _interpolate_point_on_route(coordinates, target_distance_miles, total_distance_miles)


def get_location_name(lng: float, lat: float) -> str:
    """
    Reverse geocode coordinates to get a location name for ELD remarks.

    Returns: Location string like "City, Region, Country"
    """
    url = f"{ORS_BASE_URL}/geocode/reverse"
    params = {
        "api_key": settings.ORS_API_KEY,
        "point.lon": lng,
        "point.lat": lat,
        "size": 1,
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        if data.get("features"):
            props = data["features"][0].get("properties", {})
            city = props.get("locality") or props.get("name") or props.get("district") or "Unknown"
            region = props.get("region_a") or props.get("region") or props.get("state") or ""
            country = props.get("country") or props.get("country_code") or ""
            parts = [city]
            if region:
                parts.append(region)
            if country and country not in region:
                parts.append(country)
            return ", ".join(parts)
    except Exception:
        pass

    return f"{lat:.2f}, {lng:.2f}"
