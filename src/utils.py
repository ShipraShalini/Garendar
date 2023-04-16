from datetime import datetime, timedelta

from models.event import Event


def display_all_events():
    for event in get_all_events():
        print(event)


def get_all_events():
    return Event.select().order_by(Event.start)


def get_workday_end(workday: datetime):
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=18)


def get_workday_start(workday: datetime):
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=9)


def get_next_workday_start(workday: datetime) -> datetime:
    workday = get_workday_start(workday)
    # Refer: https://stackoverflow.com/a/58665023/3803979
    if workday.isoweekday() in {5, 6}:
        day_increment = 8 - workday.isoweekday()
    else:
        day_increment = 1

    return workday + timedelta(days=day_increment)


def calculate_duration_mins(start_time, end_time):
    duration = end_time - start_time
    return duration.total_seconds() / 60
