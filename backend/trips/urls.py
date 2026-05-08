"""URL patterns for the trips API."""
from django.urls import path
from .views import TripPlanView, TripPlanHealthView, PlaceSuggestionView

urlpatterns = [
    path("trip-plan/", TripPlanView.as_view(), name="trip-plan"),
    path("health/", TripPlanHealthView.as_view(), name="health"),
    path("place-suggestions/", PlaceSuggestionView.as_view(), name="place-suggestions"),
]
