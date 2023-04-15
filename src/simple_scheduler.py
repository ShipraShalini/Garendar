import bisect
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timedelta
from operator import attrgetter, itemgetter

from models.event import Event


def get_all_events():
    return Event.select().order_by(Event.start)


def _get_workday_start(workday: datetime):
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=9)


def _get_workday_end(workday: datetime):
    return datetime(day=workday.day, month=workday.month, year=workday.year, hour=18)


class Scheduler:
    def __init__(self):
        existing_events = get_all_events()
        self.existing_events = list(existing_events.dicts())
        self.unscheduled_events = {}
        self.scheduled_events = []
        self.unscheduled_event_durations = []

    @staticmethod
    def _calculate_duration_mins(start_time, end_time):
        duration = end_time - start_time
        return duration.seconds / 60

    def needs_rescheduling(self, event: dict) -> bool:
        event_start = event["start"]
        event_end = event["end"]

        # Check if event falls during the weekends
        if event_start.date().weekday() > 4:
            return True

        # Check if the even falls outside the workday
        if event_start < _get_workday_start(event_start) or event_end > _get_workday_end(event_end):
            return True
        pivot = bisect.bisect_left(self.existing_events, event["start"], key=itemgetter("start"))
        with suppress(IndexError):
            earlier_event = self.existing_events[pivot]
            if self.is_overlapping(earlier_event, event):
                return True

        with suppress(IndexError):
            next_event = self.existing_events[pivot + 1]
            if self.is_overlapping(event, next_event):
                return True

    @staticmethod
    def is_overlapping(event1, event2):
        return event1["end"] >= event2["start"] or event1["start"] <= event2["end"]

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

    def get_smaller_slot(self, event, slot):
        duration = self._calculate_duration_mins(event["end"], slot["end"])

    def reschedule(self, unscheduled_slots: dict):
        if not (self.unscheduled_events and unscheduled_slots):
            return
        sorted_slot_durations = sorted(list(unscheduled_slots.keys()), reverse=True)
        for duration in sorted_slot_durations:
            if duration in self.scheduled_events:
                relevant_slots = unscheduled_slots[duration]
                for i in range(len(relevant_slots)):
                    event_to_reschedule = self.scheduled_events[duration].pop(0)
                    slot = relevant_slots.pop(0)
                    self._reschedule_event(event_to_reschedule, slot)
            else:
                pivot = bisect.bisect(self.unscheduled_event_durations, duration)
                relevant_event_duration = self.unscheduled_event_durations[pivot - 1]
                pivot -= 1
                relevant_slots = unscheduled_slots[duration]
                for i in range(len(relevant_slots)):
                    if not self.scheduled_events[relevant_event_duration]:
                        self.scheduled_events.pop(relevant_event_duration)
                        self.unscheduled_event_durations.remove(relevant_event_duration)
                        relevant_event_duration = self.unscheduled_event_durations[pivot - 1]
                        pivot -= 1

                    event_to_reschedule = self.scheduled_events[relevant_event_duration].pop(0)
                    slot = relevant_slots.pop(0)
                    scheduled_event = self._reschedule_event(event_to_reschedule, slot)
                    gap_duration = self._calculate_duration_mins(scheduled_event["end"], slot["end"])
                    if gap_duration not in unscheduled_slots:
                        unscheduled_slots[gap_duration] = []
                        bisect.insort(sorted_slot_durations, gap_duration)

                    unscheduled_slots[gap_duration].append({"start": scheduled_event["end"], "end": slot["end"]})

    def _reschedule_event(self, event, slot, slot_duration=None):
        event_duration = event.pop("duration")
        event_start = slot["start"]
        if slot_duration and event_duration < slot_duration:
            event_end = event_start + timedelta(seconds=event_duration * 60)
        else:
            event_end = slot["end"]
        event["start"] = event_start
        event["end"] = event_end

        self.scheduled_events.append(event)
        return event

    def update_unscheduled_events(self, event):
        duration = event["duration"]

        if duration not in self.unscheduled_event_durations:
            bisect.insort(self.unscheduled_event_durations, duration)
            self.unscheduled_events[duration] = []

        self.unscheduled_events[duration].append(event)

    def persist_new_events(self):
        Event.insert_many(self.scheduled_events).execute()

    def schedule_events(self, new_events: list[dict]):
        sorted_new_events = sorted(new_events, key=lambda e: e["start"])

        for event in sorted_new_events:
            curr_event = sorted_new_events.pop(0)
            if self.needs_rescheduling(curr_event):
                self.update_unscheduled_events(curr_event)
            else:
                event.pop("duration")
                self.scheduled_events.append(event)
                bisect.insort(self.existing_events, event, key=lambda x: x["start"])

            # if i < len(self.existing_events) -1:
            #     previous_event = self.existing_events[i + 1]
            #     unscheduled_slots = self.get_unscheduled_slots(previous_event, event)
            #     self.reschedule(unscheduled_slots)
            #
            # if needs_rescheduling(curr_event, event):
            #     self.update_unscheduled_events(curr_event)
            # else:
            #     event.pop("duration")
            #     self.scheduled_events.append(event)
            #     bisect.insort(self.existing_events, event, key=lambda x: x["start"])
        self.persist_new_events()
