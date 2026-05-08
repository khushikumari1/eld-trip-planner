"""
Hours of Service (HOS) Simulation Engine

FMCSA Rules Implemented (Property-Carrying CMV, 70hr/8day):
============================================================

From FMCSA Interstate Truck Driver's Guide to HOS (April 2022):

1. 11-HOUR DRIVING LIMIT (§395.3(a)(3)(i)):
   May drive a maximum of 11 hours after 10 consecutive hours off duty.

2. 14-HOUR DRIVING WINDOW (§395.3(a)(2)):
   May not drive beyond the 14th consecutive hour after coming on duty,
   following 10 consecutive hours off duty. Off-duty time does NOT extend
   the 14-hour window.

3. 30-MINUTE BREAK (§395.3(a)(3)(ii)):
   Must take a 30-minute consecutive break from driving after 8 cumulative
   hours of driving. The break can be off-duty, sleeper berth, or on-duty
   not driving. Resets the 8-hour driving clock.

4. 10-HOUR OFF-DUTY RESET (§395.3(a)(1)):
   Must have 10 consecutive hours off duty (or sleeper berth) before
   driving. This resets both the 11-hour driving limit and 14-hour window.

5. 70-HOUR/8-DAY CYCLE LIMIT (§395.3(b)):
   May not drive after having been on duty 70 hours in any 8 consecutive
   days. This is TOTAL on-duty time (driving + on-duty not driving).
   Rolling calculation - oldest day drops off.

6. 34-HOUR RESTART (§395.3(c)):
   Taking 34+ consecutive hours off duty resets the 70-hour clock to zero.
   (Optional - not mandatory)

ASSUMPTIONS (from assessment):
- Property-carrying driver
- 70-hour/8-day cycle
- No adverse driving conditions
- Fueling every 1000 miles
- 1 hour for pickup, 1 hour for dropoff
- Average speed derived from route calculation

ENGINE DESIGN:
- Time-based step simulation (NOT simple division)
- Tracks all state variables minute-by-minute
- Inserts mandatory breaks/stops at correct times
- Produces a timeline of events that maps to ELD log segments
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Dict, Optional, Tuple


class DutyStatus(Enum):
    """FMCSA duty status categories matching ELD grid lines."""
    OFF_DUTY = "OFF"
    SLEEPER_BERTH = "SB"
    DRIVING = "D"
    ON_DUTY_NOT_DRIVING = "ON"


@dataclass
class HOSState:
    """
    Tracks all HOS compliance state variables.

    This is the core state machine that determines what the driver
    can and cannot do at any point in time.
    """
    # Current time in the simulation
    current_time: datetime

    # 11-hour driving limit tracking
    driving_hours_today: float = 0.0  # Hours driven since last 10-hr reset

    # 14-hour window tracking
    window_start_time: Optional[datetime] = None  # When the 14-hr window started
    window_elapsed: float = 0.0  # Hours elapsed in current 14-hr window

    # 30-minute break tracking
    driving_since_break: float = 0.0  # Cumulative driving since last 30-min break

    # 70-hour/8-day cycle tracking
    cycle_hours_used: float = 0.0  # Total on-duty hours in rolling 8-day period
    daily_on_duty_log: List[float] = field(default_factory=list)  # On-duty hours per day (last 8 days)

    # Current duty status
    duty_status: DutyStatus = DutyStatus.OFF_DUTY

    # Trip progress tracking
    miles_driven_total: float = 0.0
    miles_since_fuel: float = 0.0
    miles_driven_today: float = 0.0

    # Off-duty accumulation for reset detection
    consecutive_off_duty_hours: float = 0.0

    # Whether the driver has started their duty day
    on_duty_today: bool = False

    def can_drive(self) -> Tuple[bool, str]:
        """Check if the driver is legally allowed to drive right now."""
        # Check 11-hour driving limit
        if self.driving_hours_today >= 11.0:
            return False, "11-hour driving limit reached"

        # Check 14-hour window
        if self.on_duty_today and self.window_elapsed >= 14.0:
            return False, "14-hour driving window expired"

        # Check 30-minute break requirement
        if self.driving_since_break >= 8.0:
            return False, "30-minute break required (8 hours driving)"

        # Check 70-hour cycle
        if self.cycle_hours_used >= 70.0:
            return False, "70-hour/8-day cycle limit reached"

        return True, "OK"

    def hours_until_next_limit(self) -> float:
        """Calculate hours of driving available before hitting any limit."""
        limits = []

        # 11-hour limit
        limits.append(11.0 - self.driving_hours_today)

        # 14-hour window (remaining window minus non-driving time doesn't help)
        if self.on_duty_today:
            limits.append(14.0 - self.window_elapsed)

        # 30-minute break at 8 hours
        limits.append(8.0 - self.driving_since_break)

        # 70-hour cycle
        limits.append(70.0 - self.cycle_hours_used)

        return max(0.0, min(limits))


@dataclass
class TimelineEvent:
    """A single event in the trip timeline."""
    start_time: datetime
    end_time: datetime
    duty_status: DutyStatus
    event_type: str  # "driving", "pickup", "dropoff", "fuel", "break", "sleep", "cycle_rest"
    location_description: str = ""
    miles_at_start: float = 0.0
    miles_at_end: float = 0.0
    notes: str = ""


@dataclass
class TripSegment:
    """A segment of the trip between two waypoints."""
    start_coords: Tuple[float, float]  # (lng, lat)
    end_coords: Tuple[float, float]
    distance_miles: float
    duration_hours: float  # Pure driving time for this segment
    segment_type: str  # "to_pickup", "to_dropoff"


class HOSEngine:
    """
    Time-based HOS simulation engine.

    Simulates a driver's trip step-by-step, tracking all HOS state
    and inserting mandatory breaks, rest periods, and fuel stops
    at the correct times.

    Algorithm:
    1. Start with initial state (current time, cycle hours used)
    2. For each trip segment (to pickup, pickup activity, to dropoff, dropoff activity):
       a. If driving segment: simulate driving in chunks
          - Check if any limit will be hit before segment completes
          - If yes: drive until limit, insert required break/rest, continue
          - If no: drive the full segment
       b. If activity (pickup/dropoff): log as on-duty not driving
    3. During driving simulation:
       - Every step, check fuel (1000 mile intervals)
       - Check 30-min break requirement (8 hr cumulative driving)
       - Check 11-hour driving limit
       - Check 14-hour window
       - Check 70-hour cycle
    4. Output: ordered list of TimelineEvents
    """

    # Constants from FMCSA regulations
    MAX_DRIVING_HOURS = 11.0
    MAX_WINDOW_HOURS = 14.0
    BREAK_AFTER_DRIVING_HOURS = 8.0
    BREAK_DURATION_HOURS = 0.5  # 30 minutes
    RESET_DURATION_HOURS = 10.0  # 10 consecutive hours off
    CYCLE_LIMIT_HOURS = 70.0
    CYCLE_DAYS = 8
    RESTART_HOURS = 34.0  # Optional 34-hour restart

    # Trip assumptions
    FUEL_INTERVAL_MILES = 1000.0
    FUEL_STOP_DURATION_HOURS = 0.5  # 30 min for fueling
    PICKUP_DURATION_HOURS = 1.0
    DROPOFF_DURATION_HOURS = 1.0

    def __init__(
        self,
        start_time: datetime,
        current_cycle_used: float = 0.0,
        average_speed_mph: float = 55.0,
    ):
        """
        Initialize the HOS engine.

        Args:
            start_time: When the trip begins
            current_cycle_used: Hours already used in 70-hr/8-day cycle
            average_speed_mph: Average driving speed (from route calculation)
        """
        self.state = HOSState(
            current_time=start_time,
            cycle_hours_used=current_cycle_used,
            daily_on_duty_log=[],
        )
        self.average_speed = average_speed_mph
        self.timeline: List[TimelineEvent] = []
        self.start_time = start_time

    def simulate_trip(
        self,
        segments: List[TripSegment],
        pickup_location_name: str = "Pickup",
        dropoff_location_name: str = "Dropoff",
    ) -> List[TimelineEvent]:
        """
        Run the full trip simulation.

        Args:
            segments: List of TripSegments (to_pickup, to_dropoff)
            pickup_location_name: Name of pickup location for remarks
            dropoff_location_name: Name of dropoff location for remarks

        Returns:
            Ordered list of TimelineEvents representing the complete trip
        """
        # Start the duty day
        self._start_duty_day()

        for i, segment in enumerate(segments):
            # Drive to waypoint
            self._simulate_driving_segment(segment)

            # Perform activity at waypoint
            if segment.segment_type == "to_pickup":
                self._perform_activity(
                    duration_hours=self.PICKUP_DURATION_HOURS,
                    event_type="pickup",
                    location=pickup_location_name,
                    notes="Loading/pickup operations"
                )
            elif segment.segment_type == "to_dropoff":
                self._perform_activity(
                    duration_hours=self.DROPOFF_DURATION_HOURS,
                    event_type="dropoff",
                    location=dropoff_location_name,
                    notes="Unloading/dropoff operations"
                )

        # End of trip - go off duty
        self._go_off_duty("Trip complete", "Destination")

        return self.timeline

    def _start_duty_day(self):
        """Mark the beginning of a new duty day (14-hour window starts)."""
        self.state.on_duty_today = True
        self.state.window_start_time = self.state.current_time
        self.state.window_elapsed = 0.0

    def _simulate_driving_segment(self, segment: TripSegment):
        """
        Simulate driving a segment, inserting breaks/stops as needed.

        This is the core simulation loop. It drives in chunks,
        checking limits before each chunk and inserting mandatory
        stops when limits are reached.
        """
        remaining_miles = segment.distance_miles
        segment_start_miles = self.state.miles_driven_total

        while remaining_miles > 0.01:  # Small epsilon for float comparison
            # Check if we can drive
            can_drive, reason = self.state.can_drive()

            if not can_drive:
                self._handle_driving_limit(reason)
                # After handling, re-check
                can_drive, reason = self.state.can_drive()
                if not can_drive:
                    # This shouldn't happen after proper handling
                    raise RuntimeError(f"Cannot resume driving after handling: {reason}")

            # Calculate how far we can drive before hitting any limit
            hours_available = self.state.hours_until_next_limit()

            # Also check fuel stop
            miles_until_fuel = self.FUEL_INTERVAL_MILES - self.state.miles_since_fuel
            hours_until_fuel = miles_until_fuel / self.average_speed

            # Determine the limiting factor
            drive_hours = min(hours_available, hours_until_fuel)
            drive_miles = drive_hours * self.average_speed

            # Don't drive more than remaining
            if drive_miles >= remaining_miles:
                drive_miles = remaining_miles
                drive_hours = drive_miles / self.average_speed

            # Execute the driving chunk
            if drive_hours > 0:
                self._execute_driving(drive_hours, drive_miles, segment.segment_type)
                remaining_miles -= drive_miles

            # Check if fuel stop needed
            if self.state.miles_since_fuel >= self.FUEL_INTERVAL_MILES - 0.1:
                if remaining_miles > 0.01:  # Don't fuel at destination
                    self._perform_fuel_stop()

    def _execute_driving(self, hours: float, miles: float, context: str = ""):
        """Record a chunk of driving time."""
        start = self.state.current_time
        end = start + timedelta(hours=hours)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.DRIVING,
            event_type="driving",
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total + miles,
            location_description=f"En route ({context})",
            notes=f"Driving {miles:.1f} mi in {hours:.2f} hrs",
        )
        self.timeline.append(event)

        # Update state
        self.state.current_time = end
        self.state.driving_hours_today += hours
        self.state.driving_since_break += hours
        self.state.window_elapsed += hours
        self.state.cycle_hours_used += hours
        self.state.miles_driven_total += miles
        self.state.miles_since_fuel += miles
        self.state.miles_driven_today += miles
        self.state.consecutive_off_duty_hours = 0.0
        self.state.duty_status = DutyStatus.DRIVING

    def _handle_driving_limit(self, reason: str):
        """Handle a driving limit by inserting the appropriate break/rest."""
        if "30-minute break" in reason:
            self._take_30_min_break()
        elif "11-hour" in reason or "14-hour" in reason:
            self._take_10_hour_reset()
        elif "70-hour" in reason:
            self._take_34_hour_restart()
        else:
            # Fallback: take a 10-hour reset
            self._take_10_hour_reset()

    def _take_30_min_break(self):
        """
        Insert a mandatory 30-minute break.

        Per FMCSA §395.3(a)(3)(ii): After 8 cumulative hours of driving,
        must take 30 consecutive minutes not driving (can be off-duty,
        sleeper berth, or on-duty not driving).
        """
        start = self.state.current_time
        end = start + timedelta(hours=self.BREAK_DURATION_HOURS)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.OFF_DUTY,
            event_type="break",
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total,
            location_description="Rest area",
            notes="30-minute break (8-hr driving rule)",
        )
        self.timeline.append(event)

        # Update state - break resets the 8-hour driving clock
        self.state.current_time = end
        self.state.driving_since_break = 0.0  # Reset!
        self.state.window_elapsed += self.BREAK_DURATION_HOURS  # Window keeps ticking
        # Off-duty break does NOT count toward cycle hours
        self.state.consecutive_off_duty_hours = self.BREAK_DURATION_HOURS
        self.state.duty_status = DutyStatus.OFF_DUTY

    def _take_10_hour_reset(self):
        """
        Insert a mandatory 10-hour off-duty reset.

        Per FMCSA §395.3(a)(1): 10 consecutive hours off duty resets
        both the 11-hour driving limit and 14-hour driving window.
        """
        start = self.state.current_time
        end = start + timedelta(hours=self.RESET_DURATION_HOURS)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.SLEEPER_BERTH,
            event_type="sleep",
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total,
            location_description="Rest stop / Truck stop",
            notes="10-hour off-duty reset (sleeper berth)",
        )
        self.timeline.append(event)

        # Update state - FULL RESET of daily limits
        self.state.current_time = end
        self.state.driving_hours_today = 0.0  # Reset 11-hour clock
        self.state.window_elapsed = 0.0  # Reset 14-hour window
        self.state.driving_since_break = 0.0  # Reset 30-min break clock
        self.state.window_start_time = end  # New window starts after reset
        self.state.consecutive_off_duty_hours = self.RESET_DURATION_HOURS
        self.state.miles_driven_today = 0.0
        self.state.on_duty_today = True  # Ready for new duty day
        self.state.duty_status = DutyStatus.SLEEPER_BERTH

        # Track daily on-duty for cycle calculation
        # The 10 hours off does NOT count toward cycle

    def _take_34_hour_restart(self):
        """
        Insert a 34-hour restart to reset the 70-hour cycle.

        Per FMCSA §395.3(c): 34+ consecutive hours off duty resets
        the 60/70-hour clock to zero. This also resets daily limits.
        """
        start = self.state.current_time
        end = start + timedelta(hours=self.RESTART_HOURS)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.SLEEPER_BERTH,
            event_type="cycle_rest",
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total,
            location_description="Truck stop / Rest area",
            notes="34-hour restart (70-hour cycle reset)",
        )
        self.timeline.append(event)

        # FULL RESET - everything goes back to zero
        self.state.current_time = end
        self.state.driving_hours_today = 0.0
        self.state.window_elapsed = 0.0
        self.state.driving_since_break = 0.0
        self.state.cycle_hours_used = 0.0  # Cycle resets to zero!
        self.state.window_start_time = end
        self.state.consecutive_off_duty_hours = self.RESTART_HOURS
        self.state.miles_driven_today = 0.0
        self.state.daily_on_duty_log = []  # Clear the 8-day log
        self.state.on_duty_today = True
        self.state.duty_status = DutyStatus.SLEEPER_BERTH

    def _perform_activity(
        self, duration_hours: float, event_type: str, location: str, notes: str
    ):
        """
        Record an on-duty not driving activity (pickup, dropoff, etc.).

        On-duty time counts toward:
        - 14-hour window (keeps ticking)
        - 70-hour cycle (adds to total)
        Does NOT count toward:
        - 11-hour driving limit
        - 30-minute break clock (but doesn't reset it either per FMCSA rules)
        """
        start = self.state.current_time
        end = start + timedelta(hours=duration_hours)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            event_type=event_type,
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total,
            location_description=location,
            notes=notes,
        )
        self.timeline.append(event)

        # Update state
        self.state.current_time = end
        self.state.window_elapsed += duration_hours  # Window keeps ticking
        self.state.cycle_hours_used += duration_hours  # Counts toward 70-hr cycle
        self.state.consecutive_off_duty_hours = 0.0
        self.state.duty_status = DutyStatus.ON_DUTY_NOT_DRIVING

    def _perform_fuel_stop(self):
        """
        Insert a fuel stop. Logged as on-duty not driving.
        Fueling counts as on-duty time per FMCSA definition.
        """
        start = self.state.current_time
        end = start + timedelta(hours=self.FUEL_STOP_DURATION_HOURS)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.ON_DUTY_NOT_DRIVING,
            event_type="fuel",
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total,
            location_description="Fuel stop",
            notes="Fueling (every 1000 miles)",
        )
        self.timeline.append(event)

        # Update state
        self.state.current_time = end
        self.state.window_elapsed += self.FUEL_STOP_DURATION_HOURS
        self.state.cycle_hours_used += self.FUEL_STOP_DURATION_HOURS
        self.state.miles_since_fuel = 0.0  # Reset fuel counter
        self.state.consecutive_off_duty_hours = 0.0
        self.state.duty_status = DutyStatus.ON_DUTY_NOT_DRIVING

        # A fuel stop of 30+ minutes can satisfy the break requirement
        # Per FMCSA: "These interruptions can be used to satisfy the 30-minute
        # break from driving, if consecutive."
        if self.FUEL_STOP_DURATION_HOURS >= 0.5:
            self.state.driving_since_break = 0.0

    def _go_off_duty(self, notes: str, location: str):
        """Mark the driver as going off duty at end of trip."""
        # We just record a small off-duty event to close out the timeline
        start = self.state.current_time
        end = start + timedelta(minutes=1)

        event = TimelineEvent(
            start_time=start,
            end_time=end,
            duty_status=DutyStatus.OFF_DUTY,
            event_type="off_duty",
            miles_at_start=self.state.miles_driven_total,
            miles_at_end=self.state.miles_driven_total,
            location_description=location,
            notes=notes,
        )
        self.timeline.append(event)
        self.state.duty_status = DutyStatus.OFF_DUTY


def run_hos_simulation(
    total_distance_miles: float,
    total_duration_hours: float,
    current_cycle_used: float,
    start_time: Optional[datetime] = None,
    pickup_location_name: str = "Pickup Location",
    dropoff_location_name: str = "Dropoff Location",
    pickup_distance_miles: float = 0.0,
    pickup_duration_hours: float = 0.0,
) -> List[TimelineEvent]:
    """
    High-level function to run the HOS simulation for a trip.

    Args:
        total_distance_miles: Total route distance (pickup to dropoff)
        total_duration_hours: Total driving time (no stops)
        current_cycle_used: Hours already used in 70-hr cycle
        start_time: When the trip starts (defaults to now)
        pickup_location_name: Name for pickup location
        dropoff_location_name: Name for dropoff location
        pickup_distance_miles: Distance from current location to pickup
        pickup_duration_hours: Driving time from current to pickup

    Returns:
        List of TimelineEvents representing the complete trip
    """
    if start_time is None:
        start_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)

    # Calculate average speed from route data
    if total_duration_hours > 0:
        avg_speed = total_distance_miles / total_duration_hours
    else:
        avg_speed = 55.0  # Default

    # Clamp average speed to reasonable range
    avg_speed = max(35.0, min(avg_speed, 65.0))

    engine = HOSEngine(
        start_time=start_time,
        current_cycle_used=current_cycle_used,
        average_speed_mph=avg_speed,
    )

    # Build trip segments
    segments = []

    # Segment 1: Current location to Pickup
    if pickup_distance_miles > 0:
        segments.append(TripSegment(
            start_coords=(0, 0),  # Coords handled separately
            end_coords=(0, 0),
            distance_miles=pickup_distance_miles,
            duration_hours=pickup_duration_hours,
            segment_type="to_pickup",
        ))
    else:
        # If no distance to pickup, still need a minimal segment for the pickup activity
        segments.append(TripSegment(
            start_coords=(0, 0),
            end_coords=(0, 0),
            distance_miles=0.01,
            duration_hours=0.001,
            segment_type="to_pickup",
        ))

    # Segment 2: Pickup to Dropoff
    dropoff_distance = total_distance_miles - pickup_distance_miles
    dropoff_duration = total_duration_hours - pickup_duration_hours
    if dropoff_distance > 0:
        segments.append(TripSegment(
            start_coords=(0, 0),
            end_coords=(0, 0),
            distance_miles=max(dropoff_distance, 0.01),
            duration_hours=max(dropoff_duration, 0.001),
            segment_type="to_dropoff",
        ))

    # Run simulation
    timeline = engine.simulate_trip(
        segments=segments,
        pickup_location_name=pickup_location_name,
        dropoff_location_name=dropoff_location_name,
    )

    return timeline
