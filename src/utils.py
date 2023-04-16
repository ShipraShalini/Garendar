from datetime import datetime, timedelta

from peewee import ModelSelect

from models.event import Event


def display_all_events():
    """Display all events on stdin."""
    for event in get_all_events():
        print(event)


def get_all_events() -> ModelSelect:
    """Get all events from the db in ascending order of start time."""
    return Event.select().order_by(Event.start)


def get_workday_start(workday: datetime) -> datetime:
    """Get the datetime at which the workday starts."""
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=9)


def get_workday_end(workday: datetime) -> datetime:
    """Get the datetime at which the workday ends."""
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=18)


def get_next_workday_start(workday: datetime) -> datetime:
    """Get the datetime at which the next workday starts."""
    workday = get_workday_start(workday)
    day_increment = (8 - workday.isoweekday()) if workday.isoweekday() in {5, 6} else 1
    return workday + timedelta(days=day_increment)


def calculate_duration_minutes(start_time, end_time) -> int:
    """Calculate the duration in minutes."""
    duration = end_time - start_time
    return int(duration.total_seconds() / 60)
