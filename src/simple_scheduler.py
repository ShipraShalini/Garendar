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
        if event1["start"].date() != event2["start"].date():
            workday_end = _get_workday_end(event1["start"])
            duration = self._calculate_duration_mins(event1["end"], workday_end)
            if duration:
                unscheduled_slots[duration].append({"start": event1["end"], "end": workday_end})

            workday_start = _get_workday_start(event2["start"])
            duration = self._calculate_duration_mins(workday_start, event2["start"])
            if duration:
                unscheduled_slots[duration].append({"start": workday_start, "end": event2["start"]})

        duration = self._calculate_duration_mins(event1["end"], event2["start"])
        if duration:
            unscheduled_slots[duration].append({"start": event1["end"], "end": event2["start"]})
        return unscheduled_slots

    def get_smaller_slot(self, event, slot):
        duration = self._calculate_duration_mins(event["end"], slot["end"])

    def reschedule_events(self, unscheduled_slots: dict):
        if not (self.unscheduled_events and unscheduled_slots):
            return
        sorted_slot_durations = sorted(list(unscheduled_slots.keys()), reverse=True)
        for duration in sorted_slot_durations:
            if duration in self.unscheduled_events:
                relevant_slots = unscheduled_slots[duration]
                for i in range(len(relevant_slots)):
                    if not self.unscheduled_events[duration]:
                        continue
                    event_to_reschedule = self.unscheduled_events[duration].pop(0)
                    slot = relevant_slots.pop(0)
                    self._reschedule(event_to_reschedule, slot)
                if relevant_slots:
                    self._handle_slots(duration, unscheduled_slots, sorted_slot_durations)

            else:
                self._handle_slots(duration, unscheduled_slots, sorted_slot_durations)

            if not unscheduled_slots.get(duration):
                unscheduled_slots.pop(duration)
                sorted_slot_durations.remove(duration)

    def _handle_slots(self, duration, unscheduled_slots, sorted_slot_durations):
        # todo : rename
        pivot = bisect.bisect(self.unscheduled_event_durations, duration)
        relevant_event_duration = self.unscheduled_event_durations[pivot - 1]
        pivot -= 1
        relevant_slots = unscheduled_slots[duration]
        for i in range(len(relevant_slots)):
            if not self.unscheduled_events[relevant_event_duration]:
                self.unscheduled_events.pop(relevant_event_duration)
                self.unscheduled_event_durations.remove(relevant_event_duration)
                if pivot <= 0:
                    break
                relevant_event_duration = self.unscheduled_event_durations[pivot - 1]
                pivot -= 1
            event_to_reschedule = self.unscheduled_events[relevant_event_duration].pop(0)
            slot = relevant_slots.pop(0)
            scheduled_event = self._reschedule(event_to_reschedule, slot, duration)
            gap_duration = self._calculate_duration_mins(scheduled_event["end"], slot["end"])
            if gap_duration not in unscheduled_slots:
                unscheduled_slots[gap_duration] = []
                bisect.insort(sorted_slot_durations, gap_duration)

            unscheduled_slots[gap_duration].append({"start": scheduled_event["end"], "end": slot["end"]})

    def _reschedule(self, event, slot, slot_duration=None):
        event_duration = event.pop("duration")
        event_start = slot["start"]
        if slot_duration and event_duration < slot_duration:
            event_end = event_start + timedelta(minutes=event_duration)
        else:
            event_end = slot["end"]
        event["start"] = event_start
        event["end"] = event_end

        self.scheduled_events.append(event)
        bisect.insort(self.existing_events, event, key=lambda x: x["start"])
        return event

    def update_unscheduled_events(self, event):
        duration = event["duration"]

        if duration not in self.unscheduled_event_durations:
            bisect.insort(self.unscheduled_event_durations, duration)
            self.unscheduled_events[duration] = []

        self.unscheduled_events[duration].append(event)

    @staticmethod
    def get_next_workday_start(workday: datetime) -> datetime:
        workday = _get_workday_start(workday)
        # Refer: https://stackoverflow.com/a/58665023/3803979
        if workday.isoweekday() in {5, 6}:
            day_increment = 8 - workday.isoweekday()
        else:
            day_increment = 1

        return workday + timedelta(days=day_increment)

    def schedule_next(self, last_event, event_to_be_rescheduled):
        duration = event_to_be_rescheduled.pop("duration")
        start_time = last_event["end"]
        end_time = last_event["end"] + timedelta(minutes=duration)
        if end_time > _get_workday_end(end_time):
            start_time = self.get_next_workday_start(end_time)
            end_time = start_time + timedelta(minutes=duration)

        event_to_be_rescheduled["start"] = start_time
        event_to_be_rescheduled["end"] = end_time
        self.scheduled_events.append(event_to_be_rescheduled)
        return event_to_be_rescheduled

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
        if not self.unscheduled_events:
            self.persist_new_events()
            return

        for i, event in enumerate(self.existing_events):
            if i < len(self.existing_events) - 1:
                next_event = self.existing_events[i + 1]
                unscheduled_slots = self.get_unscheduled_slots(event, next_event)
                self.reschedule_events(unscheduled_slots)

        # last_event = self.existing_events[-1]
        # for events in self.unscheduled_events.values():
        #     for event in events:
        #         scheduled_event = self.schedule_next(last_event, event)
        #         last_event = scheduled_event
        self.persist_new_events()
