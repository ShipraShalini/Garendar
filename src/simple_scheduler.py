from collections import defaultdict
from datetime import datetime

from models.event import Event


def get_all_events():
    return Event.select().order_by(Event.start)


def _get_workday_start(workday: datetime):
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=9)


def _get_workday_end(workday: datetime):
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=18)


def needs_rescheduling(new_event: dict, existing_event: Event) -> bool:
    event_start = new_event["start"]
    event_end = new_event["end"]

    # Check if event falls during the weekends
    if event_start.date().weekday() > 4:
        return True

    # Check if the even falls outside the workday
    if event_start < _get_workday_start(event_start) or event_end > _get_workday_end(event_end):
        return True

    return existing_event.start >= event_start or existing_event.end <= event_start


class Scheduler:
    def __init__(self):
        self.unscheduled_events = defaultdict(list)
        self.scheduled_events = []

    @staticmethod
    def _calculate_duration_mins(start_time, end_time):
        duration = end_time - start_time
        return duration.seconds / 60

    def get_unscheduled_slots(self, event1: Event, event2: Event):
        unscheduled_slots = defaultdict(list)
        if event1.start.date != event2.start.date:
            workday_end = _get_workday_end(event1)
            duration = self._calculate_duration_mins(event1.end, workday_end)
            unscheduled_slots[duration].append({"start": event1.end, "end": workday_end})

            workday_start = _get_workday_start(event2)
            duration = self._calculate_duration_mins(workday_start, event2.start)
            unscheduled_slots[duration].append({"start": workday_start, "end": event2.start})

        duration = self._calculate_duration_mins(event1.end, event2.start)
        unscheduled_slots[duration].append({"start": event1.end, "end": event2.start})
        return unscheduled_slots

    def reschedule(self, unscheduled_slots: dict):
        pass

    def update_unscheduled_events(self, event):
        duration = event.pop("duration")
        self.unscheduled_events[duration].append(event)

    def persist_new_events(self):
        Event.insert_many(self.scheduled_events)

    def schedule_events(self, new_events: list[dict]):
        sorted_new_events = sorted(new_events, key=lambda e: e["start"])
        existing_events = get_all_events()

        for i, event in enumerate(existing_events):
            if i > 0:
                previous_event = existing_events[i - 1]
                unscheduled_slots = self.get_unscheduled_slots(previous_event, event)
                self.reschedule(unscheduled_slots)

            curr_event = sorted_new_events.pop(0)
            if needs_rescheduling(curr_event, event):
                self.update_unscheduled_events(curr_event)
            else:
                event.pop("duration")
                self.scheduled_events.append(event)

        self.persist_new_events()
