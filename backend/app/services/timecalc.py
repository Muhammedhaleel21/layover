"""Time calculation utilities."""

from datetime import datetime, timedelta
from typing import Optional


def calculate_usable_minutes(
    total_minutes: int,
    delay_minutes: Optional[int] = None,
    scheduled_departure: Optional[datetime] = None
) -> int:
    """
    Calculate usable minutes from the available parameters.
    
    If delay_minutes is provided, use that.
    If scheduled_departure is provided, calculate from now until departure.
    Otherwise, use total_minutes as-is.
    """
    if delay_minutes is not None:
        return delay_minutes
    
    if scheduled_departure is not None:
        now = datetime.now()
        if scheduled_departure > now:
            # Calculate minutes until departure
            delta = scheduled_departure - now
            return int(delta.total_seconds() / 60)
        else:
            # Departure was in the past, no time available
            return 0
    
    return total_minutes


def time_fits_with_buffer(
    current_time: int,
    travel_min: int,
    visit_min: int,
    return_min: int,
    buffer_min: int,
    total_available: int
) -> bool:
    """
    Check if a mission fits within available time with buffer protection.
    
    Args:
        current_time: Time already used
        travel_min: Travel time to destination
        visit_min: Visit time at destination
        return_min: Return time to start
        buffer_min: Required buffer time
        total_available: Total available time
    """
    required_time = current_time + travel_min + visit_min + return_min + buffer_min
    return required_time <= total_available