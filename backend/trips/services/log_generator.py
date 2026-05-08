"""
ELD Log Generator

Converts the HOS engine timeline into FMCSA-compliant Daily Log Sheets.

From FMCSA Guide (Page 15-18):
- Each log covers ONE calendar day (24 hours)
- 24-hour graph grid with 4 duty status lines:
  1. Off Duty
  2. Sleeper Berth
  3. Driving
  4. On Duty (Not Driving)
- Must include:
  - Date (month, day, year)
  - Total miles driving today
  - Remarks (location at each duty status change)
  - Total hours per status (must sum to 24)
  - Truck/trailer numbers
  - Carrier name and address
  - Driver signature

Grid Format:
- X-axis: 24 hours (midnight to midnight), marked every hour
- Y-axis: 4 duty status rows
- Horizontal lines show duration in each status
- Vertical lines show transitions between statuses

This module generates the data structure that the frontend renders
as the visual ELD log grid.
"""
from datetime import datetime, timedelta
from typing import List, Dict
from .hos_engine import TimelineEvent, DutyStatus


def generate_daily_logs(
    timeline: List[TimelineEvent],
    start_date: datetime,
) -> List[Dict]:
    """
    Convert a timeline of events into daily ELD log sheets.

    Each daily log covers midnight-to-midnight (24 hours).
    Events that span midnight are split across days.
    Remaining time in each day is filled with off-duty.
    Total hours per day MUST equal 24.
    """
    if not timeline:
        return []

    # Determine the date range
    first_event_start = timeline[0].start_time
    last_event_end = timeline[-1].end_time

    # Start from midnight of the first day
    first_day = first_event_start.replace(hour=0, minute=0, second=0, microsecond=0)
    last_day = last_event_end.replace(hour=0, minute=0, second=0, microsecond=0)

    # Calculate number of days needed
    num_days = (last_day - first_day).days + 1

    daily_logs = []

    for day_offset in range(num_days):
        day_start = first_day + timedelta(days=day_offset)
        day_end = day_start + timedelta(days=1)

        day_log = _build_day_log(
            timeline=timeline,
            day_start=day_start,
            day_end=day_end,
            day_number=day_offset + 1,
        )
        daily_logs.append(day_log)

    return daily_logs


def _build_day_log(
    timeline: List[TimelineEvent],
    day_start: datetime,
    day_end: datetime,
    day_number: int,
) -> Dict:
    """
    Build a single day's ELD log from the timeline.

    Clips events to the day boundary and fills gaps with off-duty.
    Ensures total hours = 24.
    """
    segments = []
    remarks = []
    total_miles = 0.0

    for event in timeline:
        # Skip events entirely outside this day
        if event.end_time <= day_start or event.start_time >= day_end:
            continue

        # Clip event to day boundaries
        seg_start = max(event.start_time, day_start)
        seg_end = min(event.end_time, day_end)

        if seg_end <= seg_start:
            continue

        start_hour = _time_to_hour_of_day(seg_start, day_start)
        end_hour = _time_to_hour_of_day(seg_end, day_start)
        duration = end_hour - start_hour

        if duration < 0.001:
            continue

        status_code = _duty_status_to_code(event.duty_status)

        segments.append({
            "status": status_code,
            "start_hour": round(start_hour, 4),
            "end_hour": round(end_hour, 4),
            "duration_hours": round(duration, 4),
            "location": event.location_description,
            "remark": event.notes,
        })

        # Add remark for duty status changes
        if event.location_description:
            time_str = seg_start.strftime("%H:%M")
            remarks.append(
                f"{time_str} - {status_code} - {event.location_description}"
                + (f" ({event.notes})" if event.notes else "")
            )

        # Track miles for driving segments
        if event.duty_status == DutyStatus.DRIVING:
            # Proportional miles for clipped segment
            event_duration = (event.end_time - event.start_time).total_seconds() / 3600
            if event_duration > 0:
                fraction = duration / event_duration
                event_miles = event.miles_at_end - event.miles_at_start
                total_miles += event_miles * fraction

    # Fill gaps with off-duty to ensure 24-hour total
    segments = _fill_gaps_with_off_duty(segments)

    # Calculate totals
    total_off = sum(s["duration_hours"] for s in segments if s["status"] == "OFF")
    total_sb = sum(s["duration_hours"] for s in segments if s["status"] == "SB")
    total_driving = sum(s["duration_hours"] for s in segments if s["status"] == "D")
    total_on = sum(s["duration_hours"] for s in segments if s["status"] == "ON")

    # Verify total = 24 (with small tolerance for floating point)
    total = total_off + total_sb + total_driving + total_on
    if abs(total - 24.0) > 0.01:
        # Adjust off-duty to make it exactly 24
        diff = 24.0 - total
        total_off += diff
        # Find the largest off-duty segment and adjust it
        for seg in segments:
            if seg["status"] == "OFF":
                seg["duration_hours"] += diff
                seg["end_hour"] += diff
                break

    return {
        "date": day_start.strftime("%Y-%m-%d"),
        "day_number": day_number,
        "segments": segments,
        "total_off_duty": round(total_off, 2),
        "total_sleeper": round(total_sb, 2),
        "total_driving": round(total_driving, 2),
        "total_on_duty": round(total_on, 2),
        "total_miles": round(total_miles, 1),
        "remarks": remarks,
    }


def _fill_gaps_with_off_duty(segments: List[Dict]) -> List[Dict]:
    """
    Fill any gaps in the 24-hour period with off-duty status.
    Also fills time before first segment and after last segment.
    """
    if not segments:
        return [{"status": "OFF", "start_hour": 0, "end_hour": 24, "duration_hours": 24, "location": "", "remark": ""}]

    # Sort by start time
    segments.sort(key=lambda s: s["start_hour"])

    filled = []

    # Fill gap before first segment
    if segments[0]["start_hour"] > 0.001:
        filled.append({
            "status": "OFF",
            "start_hour": 0.0,
            "end_hour": segments[0]["start_hour"],
            "duration_hours": segments[0]["start_hour"],
            "location": "",
            "remark": "Off duty",
        })

    # Process segments and fill gaps between them
    for i, seg in enumerate(segments):
        filled.append(seg)

        # Check for gap after this segment
        if i < len(segments) - 1:
            gap_start = seg["end_hour"]
            gap_end = segments[i + 1]["start_hour"]
            if gap_end - gap_start > 0.001:
                filled.append({
                    "status": "OFF",
                    "start_hour": gap_start,
                    "end_hour": gap_end,
                    "duration_hours": gap_end - gap_start,
                    "location": "",
                    "remark": "Off duty",
                })

    # Fill gap after last segment
    last_end = segments[-1]["end_hour"]
    if last_end < 23.999:
        filled.append({
            "status": "OFF",
            "start_hour": last_end,
            "end_hour": 24.0,
            "duration_hours": 24.0 - last_end,
            "location": "",
            "remark": "Off duty",
        })

    return filled


def _time_to_hour_of_day(dt: datetime, day_start: datetime) -> float:
    """Convert a datetime to hour-of-day (0.0 to 24.0) relative to day_start."""
    delta = dt - day_start
    hours = delta.total_seconds() / 3600.0
    return max(0.0, min(24.0, hours))


def _duty_status_to_code(status: DutyStatus) -> str:
    """Convert DutyStatus enum to ELD log code."""
    return status.value
