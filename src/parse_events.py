from datetime import datetime

from src.constants import DATE_FORMAT, DURATION_DELIMITER, EVENT_DELIMITER


def parse_event_details(event_details: str) -> tuple[datetime, datetime, str]:
    start_time, _, end_time_n_event = event_details.partition(DURATION_DELIMITER)
    end_time, _, event = end_time_n_event.partition(EVENT_DELIMITER)
    if not (start_time and end_time and event):
        raise ValueError()
    start_time = datetime.strptime(start_time.strip(), DATE_FORMAT)
    end_time = datetime.strptime(end_time.strip(), DATE_FORMAT)
    return start_time, end_time, event.strip()


def parse_input_events(event_list):
    event_list = event_list.split(",")
    return [parse_event_details(event.strip()) for event in event_list]
