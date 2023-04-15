from datetime import datetime

from src.constants import DATE_FORMAT, DURATION_DELIMITER, EVENT_DELIMITER, MINUTES_IN_9_HOURS
from src.exceptions import ValidationError


def _get_event_duration(start_time, end_time):
    duration = end_time - start_time
    duration = duration.seconds / 60
    remainder = duration % 5  # Each event is multiple of 5 mins
    return duration + remainder


def validate_event(start_time, end_time, duration):
    if duration > MINUTES_IN_9_HOURS:
        raise ValidationError("Event can't be longer than 9 hours")

    if start_time > end_time:
        raise ValidationError("Event Start can't be after event end.")


def parse_event_details(event_details: str) -> dict:
    start_time, _, end_time_n_event = event_details.partition(DURATION_DELIMITER)
    end_time, _, event = end_time_n_event.partition(EVENT_DELIMITER)
    if not (start_time and end_time and event):
        raise ValidationError("Invalid event string.")
    start_time = datetime.strptime(start_time.strip(), DATE_FORMAT)
    end_time = datetime.strptime(end_time.strip(), DATE_FORMAT)

    duration = _get_event_duration(start_time, end_time)

    validate_event(start_time, end_time, duration)
    return {"start": start_time, "end": end_time, "duration": duration, "description": event.strip()}


def parse_input_events(event_list: str) -> list[dict]:
    return [parse_event_details(event.strip()) for event in event_list.split(",")]
