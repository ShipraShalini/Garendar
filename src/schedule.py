from models.event import Event


def schedule_event(start_time, end_time, event):
    last_overlapping_event = get_last_overlapping_event(start_time, end_time)

    if not last_overlapping_event:
        Event.create(start=start_time, end=end_time, description=event)


def get_last_overlapping_event(start_time, end_time):
    return (
        Event.select()
        .where(
            (Event.start >= start_time & Event.start < end_time)
            | (Event.end >= start_time & Event.end < end_time)
            | (Event.end >= start_time & Event.end < end_time)
        )
        .order_by(Event.end.desc())
        .first()
    )


def get_unassigned_slots(start_time, end_time, last_overlapping_event):
    duration = end_time - start_time
    event_date = start_time.date
    all_following_events = Event.select().where(
        (Event.start >= end_time, Event.start.date == event_date)
    )

    events = last_overlapping_event + all_following_events


def display_all_events():
    all_events = Event.select()
    for event in all_events:
        print(event)
