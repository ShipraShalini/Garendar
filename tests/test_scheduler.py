from datetime import datetime

import pytest

from src.scheduler import Scheduler
from src.utils import get_all_events


def test_schedule_events(db):
    new_event_details = [
        (_get_dt("2022-08-23 13:00"), _get_dt("2022-08-23 14:00"), 60, "1 hr"),
        (_get_dt("2022-08-23 16:00"), _get_dt("2022-08-23 17:00"), 60, "1 hr"),
        (_get_dt("2022-08-23 16:10"), _get_dt("2022-08-23 16:40"), 30, "30 mins"),
        (_get_dt("2022-08-23 16:10"), _get_dt("2022-08-23 16:40"), 30, "30 mins"),
        (_get_dt("2022-08-23 16:20"), _get_dt("2022-08-23 16:27"), 10, "7 mins"),
        (_get_dt("2022-08-23 17:10"), _get_dt("2022-08-23 19:40"), 150, "2 hr 30 mins"),
        (_get_dt("2022-08-23 15:10"), _get_dt("2022-08-23 15:30"), 20, "20 mins"),
    ]

    expected_result = [
        (_get_dt("2022-08-23 13:00:00"), _get_dt("2022-08-23 14:00:00"), "1 hr"),
        (_get_dt("2022-08-23 14:00:00"), _get_dt("2022-08-23 14:30:00"), "30 mins"),
        (_get_dt("2022-08-23 15:10:00"), _get_dt("2022-08-23 15:30:00"), "20 mins"),
        (_get_dt("2022-08-23 16:00:00"), _get_dt("2022-08-23 17:00:00"), "1 hr"),
        (_get_dt("2022-08-23 16:10:00"), _get_dt("2022-08-23 16:40:00"), "30 mins"),
        (_get_dt("2022-08-23 16:20:00"), _get_dt("2022-08-23 16:27:00"), "7 mins"),
        (_get_dt("2022-08-24 09:00:00"), _get_dt("2022-08-24 11:30:00"), "2 hr 30 mins"),
    ]

    new_events = [
        {"start": start, "end": end, "duration": duration, "description": desc}
        for start, end, duration, desc in new_event_details
    ]

    Scheduler().schedule_events(new_events)
    for event, expected_event in zip(get_all_events(), expected_result):
        assert event.start == expected_event[0]
        assert event.end == expected_event[1]
        assert event.description == expected_event[2]


@pytest.mark.parametrize(
    "event1, event2, expected_result",
    [
        (
            {"start": "2023-10-15 12:00", "end": "2023-10-15 12:30"},
            {"start": "2023-10-15 12:10", "end": "2023-10-15 14:00"},
            True,
        ),
        (
            {"start": "2023-10-15 12:00", "end": "2023-10-15 09:00"},
            {"start": "2023-10-15 11:30", "end": "2023-10-15 12:20"},
            True,
        ),
        (
            {"start": "2023-10-15 12:00", "end": "2023-10-15 13:00"},
            {"start": "2023-10-15 11:30", "end": "2023-10-15 14:00"},
            True,
        ),
        (
            {"start": "2023-10-15 12:00", "end": "2023-10-15 13:00"},
            {"start": "2023-10-15 12:10", "end": "2023-10-15 12:30"},
            True,
        ),
        (
            {"start": "2023-10-15 12:00", "end": "2023-10-15 13:00"},
            {"start": "2023-10-15 13:00", "end": "2023-10-15 14:00"},
            False,
        ),
    ],
)
def test_is_overlapping(event1: dict, event2: dict, expected_result: bool):
    """Check if the two events overlap."""
    event1 = {"start": datetime.fromisoformat(event1["start"]), "end": datetime.fromisoformat(event1["end"])}
    event2 = {"start": datetime.fromisoformat(event2["start"]), "end": datetime.fromisoformat(event2["end"])}

    result = Scheduler.is_overlapping(event1, event2)

    assert result is expected_result


def test_add_remaining_time_to_unscheduled_slots():
    scheduled_event = {"start": _get_dt("2023-10-15 12:00"), "end": _get_dt("2023-10-15 12:40"), "description": "abc"}
    slot = {"start": _get_dt("2023-10-15 12:00"), "end": _get_dt("2023-10-15 13:00")}

    sorted_slot_durations = [10, 30, 45]

    scheduler = Scheduler()
    scheduler._add_remaining_time_to_unscheduled_slots(scheduled_event, slot, sorted_slot_durations)

    assert scheduler.unscheduled_slots == {
        20: [{"start": _get_dt("2023-10-15 12:40"), "end": _get_dt("2023-10-15 13:00")}]
    }
    assert sorted_slot_durations == [10, 20, 30, 45]


@pytest.mark.parametrize(
    "last_event, event, expected_final_event",
    [
        (
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-16 12:40", "2023-10-16 13:20"),
        ),
        (
            ("2023-10-16 17:00", "2023-10-16 17:40"),
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-17 09:00", "2023-10-17 09:40"),
        ),
        (
            ("2023-10-15 17:00", "2023-10-15 17:40"),
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-16 09:00", "2023-10-16 09:40"),
        ),
        (
            ("2023-10-14 17:00", "2023-10-14 17:40"),
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-16 09:00", "2023-10-16 09:40"),
        ),
        (
            ("2023-10-13 17:00", "2023-10-13 17:40"),
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-16 09:00", "2023-10-16 09:40"),
        ),
        (
            ("2023-10-12 17:00", "2023-10-12 17:40"),
            ("2023-10-16 12:00", "2023-10-16 12:40"),
            ("2023-10-13 09:00", "2023-10-13 09:40"),
        ),
    ],
)
def test_schedule_next(last_event, event, expected_final_event):
    last_event = {"start": _get_dt(last_event[0]), "end": _get_dt(last_event[1]), "description": "last_event"}
    event = {"start": _get_dt(event[0]), "end": _get_dt(event[1]), "duration": 40, "description": "schedule_me"}
    expected_final_event = {
        "start": _get_dt(expected_final_event[0]),
        "end": _get_dt(expected_final_event[1]),
        "description": "schedule_me",
    }

    scheduler = Scheduler()
    final_event = scheduler.schedule_next(last_event, event)

    assert final_event == expected_final_event == scheduler.scheduled_events[0]


# @pytest.mark.parametrize(
#     "event, slot, expected_updated_event, slot_duration",
#     [
#         (
#             ("2023-10-16 12:00", "2023-10-16 13:00"),
#             ("2023-10-16 12:00", "2023-10-16 12:40"),
#             ("2023-10-17 09:00", "2023-10-17 09:40"),
#             60,
#         ),
#         (
#             ("2023-10-16 17:00", "2023-10-16 17:40"),
#             ("2023-10-16 12:00", "2023-10-16 12:40"),
#             ("2023-10-17 09:00", "2023-10-17 09:40"),
#         ),
#         (
#             ("2023-10-15 17:00", "2023-10-15 17:40"),
#             ("2023-10-16 12:00", "2023-10-16 12:40"),
#             ("2023-10-16 09:00", "2023-10-16 09:40"),
#         ),
#         (
#             ("2023-10-14 17:00", "2023-10-14 17:40"),
#             ("2023-10-16 12:00", "2023-10-16 12:40"),
#             ("2023-10-16 09:00", "2023-10-16 09:40"),
#         ),
#         (
#             ("2023-10-13 17:00", "2023-10-13 17:40"),
#             ("2023-10-16 12:00", "2023-10-16 12:40"),
#             ("2023-10-16 09:00", "2023-10-16 09:40"),
#         ),
#         (
#             ("2023-10-12 17:00", "2023-10-12 17:40"),
#             ("2023-10-16 12:00", "2023-10-16 12:40"),
#             ("2023-10-13 09:00", "2023-10-13 09:40"),
#         ),
#     ],
# )
# def test_reschedule(event, slot, expected_updated_event, slot_duration):
#     event = {"start": _get_dt(event[0]), "end": _get_dt(event[1]), "duration": 40, "description": "schedule_me"}
#     slot = {"start": _get_dt(slot[0]), "end": _get_dt(slot[1])}
#     expected_updated_event = {
#         "start": _get_dt(expected_updated_event[0]),
#         "end": _get_dt(expected_updated_event[1]),
#         "description": "schedule_me",
#     }
#
#     scheduler = Scheduler()
#     scheduler.existing_events = [
#         {"start": _get_dt("2023-10-16 11:00"), "end": _get_dt("2023-10-16 12:00"), "description": "scheduled1"},
#         {"start": _get_dt("2023-10-16 13:00"), "end": _get_dt("2023-10-16 14:00"), "description": "scheduled2"},
#         {"start": _get_dt("2023-10-16 15:00"), "end": _get_dt("2023-10-16 16:00"), "description": "scheduled2"},
#     ]
#     updated_event = scheduler._reschedule(event, slot, slot_duration)
#
#     assert updated_event == expected_updated_event == scheduler.scheduled_events[0]


def _get_dt(datetime_str):
    """Return datetime in less characters."""
    return datetime.fromisoformat(datetime_str)
