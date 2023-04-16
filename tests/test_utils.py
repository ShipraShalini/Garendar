from datetime import datetime

import pytest

from src.utils import calculate_duration_minutes, get_next_workday_start, get_workday_end, get_workday_start


@pytest.mark.parametrize(
    "workday, expected_workday_start",
    [
        ("2023-10-15 12:00", "2023-10-15 09:00"),
        ("2023-10-15 00:00", "2023-10-15 09:00"),
    ],
)
def test_get_workday_start(workday, expected_workday_start):
    workday = datetime.fromisoformat(workday)
    expected_workday_start = datetime.fromisoformat(expected_workday_start)

    workday_start = get_workday_start(workday)

    assert workday_start == expected_workday_start


@pytest.mark.parametrize(
    "workday, expected_workday_end",
    [
        ("2023-10-15 12:00", "2023-10-15 18:00"),
        ("2023-10-15 00:00", "2023-10-15 18:00"),
    ],
)
def test_get_workday_end(workday, expected_workday_end):
    workday = datetime.fromisoformat(workday)
    expected_workday_end = datetime.fromisoformat(expected_workday_end)

    workday_end = get_workday_end(workday)

    assert workday_end == expected_workday_end


@pytest.mark.parametrize(
    "workday, expected_next_workday_start",
    [
        ("2022-08-22 12:00", "2022-08-23 09:00"),  # Monday -> Tuesday
        ("2022-08-23 12:00", "2022-08-24 09:00"),  # Tuesday -> Wednesday
        ("2022-08-24 12:00", "2022-08-25 09:00"),  # Wednesday -> Thursday
        ("2022-08-25 12:00", "2022-08-26 09:00"),  # Thursday -> Friday
        ("2022-08-26 12:00", "2022-08-29 09:00"),  # Friday -> Monday
        ("2022-08-27 12:00", "2022-08-29 09:00"),  # Saturday -> Monday
        ("2022-08-28 12:00", "2022-08-29 09:00"),  # Sunday -> Monday
    ],
)
def test_get_workday_end(workday, expected_next_workday_start):
    workday = datetime.fromisoformat(workday)
    expected_next_workday_start = datetime.fromisoformat(expected_next_workday_start)

    next_workday_start = get_next_workday_start(workday)

    assert next_workday_start == expected_next_workday_start


@pytest.mark.parametrize(
    "start_time, end_time, expected_duration",
    [
        ("2023-10-15 12:00", "2023-10-15 13:00", 60),
        ("2023-10-15 14:30", "2023-10-15 14:37", 7),
        ("2023-10-15 14:32", "2023-10-15 14:37", 5),
    ],
)
def test_calculate_duration_minutes(start_time, end_time, expected_duration):
    start_time = datetime.fromisoformat(start_time)
    end_time = datetime.fromisoformat(end_time)

    duration = calculate_duration_minutes(start_time, end_time)

    assert duration == expected_duration
