from datetime import datetime

import pytest

from src.event_parser import _get_event_duration, parse_event_details, parse_input_events
from src.exceptions import ValidationError


@pytest.mark.parametrize(
    "start_time, end_time, expected_duration",
    [
        ("2023-10-15 12:00", "2023-10-15 13:00", 60),
        ("2023-10-15 23:30", "2023-10-16 00:10", 40),
        ("2023-10-15 14:30", "2023-10-15 14:37", 10),
        ("2023-10-15 14:32", "2023-10-15 14:37", 5),
        ("2023-10-15 14:33", "2023-10-15 14:37", 5),
    ],
)
def test_get_event_duration(start_time, end_time, expected_duration):
    start_time = datetime.fromisoformat(start_time)
    end_time = datetime.fromisoformat(end_time)

    duration = _get_event_duration(start_time, end_time)

    assert duration == expected_duration


@pytest.mark.parametrize(
    "event_string, expected_event_dict",
    [
        (
            "2022/08/27 16:20   ->   2022/08/27 16:27 -    7 minutes",
            {
                "description": "7 minutes",
                "duration": 10,
                "start": datetime(2022, 8, 27, 16, 20),
                "end": datetime(2022, 8, 27, 16, 27),
            },
        ),
        (
            "2022/08/27 16:10 -> 2022/08/27 16:40 - 30 minutes",
            {
                "description": "30 minutes",
                "duration": 30,
                "start": datetime(2022, 8, 27, 16, 10),
                "end": datetime(2022, 8, 27, 16, 40),
            },
        ),
    ],
)
def test_parse_event_details(event_string, expected_event_dict):
    event_dict = parse_event_details(event_string)
    assert event_dict == expected_event_dict


@pytest.mark.parametrize(
    "event_string, error_msg",
    [
        ("", "Invalid event string: "),
        ("2022/08/27 16:10 -> 2022/08/27 16:40 -> 30 minutes", "Invalid event string: "),
        ("2022-08-27 16:10 -> 2022-08-27 16:40 - 30 minutes", "Dates should be in the format YYYY/MM/DD HH:mm: "),
        ("2022/08/27 16:10 -> 2022/08/27 16:40 - ", "Invalid event string: "),
        ("2022/08/27 16:10 -> 2022/08/28 16:10 - 1 day", "Event can't be longer than 9 hours: "),
        ("2022/08/27 16:40 -> 2022/08/27 16:10 - 1 day", "Event Start can't be after event end: "),
    ],
)
def test_parse_event_details_error_cases(event_string, error_msg):
    expected_error_message = error_msg + event_string
    with pytest.raises(ValidationError, match=expected_error_message):
        parse_event_details(event_string)


def test_parse_input_events():
    input_string = (
        "2022/08/23 15:00 -> 2022/08/23 16:00 - Meet Jamie for coffee,"
        "2022/08/23 16:15 -> 2022/08/23 17:00 - Guitar lessons"
    )
    events = parse_input_events(input_string)

    assert events == [
        {
            "description": "Meet Jamie for coffee",
            "duration": 60,
            "start": datetime(2022, 8, 23, 15, 00),
            "end": datetime(2022, 8, 23, 16, 00),
        },
        {
            "description": "Guitar lessons",
            "duration": 45,
            "start": datetime(2022, 8, 23, 16, 15),
            "end": datetime(2022, 8, 23, 17, 00),
        },
    ]
