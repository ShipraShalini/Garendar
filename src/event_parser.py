from datetime import datetime

from src.constants import DATE_FORMAT, DURATION_DELIMITER, EVENT_DELIMITER, INPUT_DELIMITER, MINUTES_IN_9_HOURS
from src.exceptions import ValidationError
from src.utils import calculate_duration_minutes


def _get_event_duration(start_time: datetime, end_time: datetime) -> float:
    """Return event duration in multiples of 5."""
    duration = calculate_duration_minutes(start_time, end_time)
    # Each event is multiple of 5 minutes.
    remainder = duration % 5
    increment = 5 - remainder if remainder else 0
    return duration + increment


def validate_event(start_time: datetime, end_time: datetime, duration: float, event_details: str) -> None:
    if duration > MINUTES_IN_9_HOURS:
        raise ValidationError(f"Event can't be longer than 9 hours: {event_details}")

    if start_time > end_time:
        raise ValidationError(f"Event Start can't be after event end: {event_details}")


def parse_event_details(event_details: str) -> dict:
    """Parse event string into dict of python datatypes."""
    start_time, _, end_time_n_event = event_details.partition(DURATION_DELIMITER)
    end_time, _, event = end_time_n_event.partition(EVENT_DELIMITER)
    if not (start_time and end_time and event):
        raise ValidationError(f"Invalid event string: {event_details}")
    try:
        start_time = datetime.strptime(start_time.strip(), DATE_FORMAT)
        end_time = datetime.strptime(end_time.strip(), DATE_FORMAT)
    except ValueError:
        raise ValidationError(f"Dates should be in the format YYYY/MM/DD HH:mm: {event_details}") from None

    duration = _get_event_duration(start_time, end_time)

    validate_event(start_time, end_time, duration, event_details)
    return {"start": start_time, "end": end_time, "duration": duration, "description": event.strip()}


def parse_input_events(event_list: str) -> list[dict]:
    """Parse all events provided through stdin."""
    return [parse_event_details(event.strip()) for event in event_list.split(INPUT_DELIMITER)]
