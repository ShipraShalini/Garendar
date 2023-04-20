import bisect
from collections import defaultdict
from contextlib import suppress
from datetime import timedelta
from operator import itemgetter

from models.event import Event
from src.utils import (
    calculate_duration_minutes,
    get_all_events,
    get_next_workday_start,
    get_workday_end,
    get_workday_start,
)


class Scheduler:
    def __init__(self):
        existing_events = get_all_events()
        self.existing_events = list(existing_events.dicts())
        self.unscheduled_events = {}
        self.scheduled_events = []
        self.unscheduled_event_durations = []
        self.unscheduled_slots = defaultdict(list)

    def _clean_unassigned_slots(self, duration: int, sorted_slot_durations: list[int]):
        """Clean unassigned slots.

        If there's slot duration which doesn't have any slot left, remove the duration from the unscheduled_slots dict
        and from the sorted_slot_durations list.
        """
        if duration in self.unscheduled_slots and not self.unscheduled_slots.get(duration):
            self.unscheduled_slots.pop(duration)
            sorted_slot_durations.remove(duration)

    def _clean_unscheduled_events(self, event_duration: int):
        """Clean unscheduled events.

        If there's event duration which doesn't have any unscheduled event left,
        remove the duration from the unscheduled_events dict and from the unscheduled_event_durations list.
        """
        if not self.unscheduled_events[event_duration]:
            self.unscheduled_events.pop(event_duration)
            self.unscheduled_event_durations.remove(event_duration)

    @staticmethod
    def is_overlapping(event1: dict, event2: dict) -> bool:
        """Check if the two events overlap."""
        return (
            (event1["start"] > event2["start"] and event1["end"] < event2["end"])
            or (event1["start"] < event2["start"] and event1["end"] > event2["end"])
            or (event1["end"] > event2["start"])
            or (event2["end"] < event1["start"])
        )

    def persist_new_events(self):
        """Save new events to the db."""
        Event.insert_many(self.scheduled_events).execute()

    def _get_last_scheduled_event(self):
        """Get last scheduled event.

        Return the last existing_event if existing_events is populated.

        There can be a case if there is no event in the db and all the events are on weekends, then existing_event.
        will be empty. So schedule the first event and return it.
        """
        if self.existing_events:
            return self.existing_events[-1]
        # Get the first smallest unassigned event.
        smallest_duration = self.unscheduled_event_durations[0]
        event = self.unscheduled_events[smallest_duration].pop(0)
        event_duration = event.pop("duration")
        # Schedule the event at the starting of the first workday.
        event["start"] = get_next_workday_start(event["start"])
        event["end"] = event["start"] + timedelta(minutes=event_duration)
        self.scheduled_events.append(event)
        self._clean_unscheduled_events(event_duration)
        return event

    def update_unscheduled_events(self, event: dict) -> None:
        """Add events that need rescheduling to unscheduled_events.

        Also update unscheduled_event_durations, if required.
        """
        duration = event["duration"]
        if duration not in self.unscheduled_event_durations:
            bisect.insort(self.unscheduled_event_durations, duration)
            self.unscheduled_events[duration] = []
        self.unscheduled_events[duration].append(event)

    def _add_remaining_time_to_unscheduled_slots(self, scheduled_event: dict, slot: dict, sorted_slot_durations: list):
        """Add a new `unscheduled slot` using the time left in the slot after scheduling the event.

        Also update sorted_slot_durations.
        """
        gap_duration = calculate_duration_minutes(scheduled_event["end"], slot["end"])
        if gap_duration not in self.unscheduled_slots:
            self.unscheduled_slots[gap_duration] = []
            bisect.insort(sorted_slot_durations, gap_duration)

        self.unscheduled_slots[gap_duration].append({"start": scheduled_event["end"], "end": slot["end"]})

    def schedule_next(self, last_event: dict, event_to_be_rescheduled: dict) -> dict:
        """Schedule the event after the last event."""
        duration = event_to_be_rescheduled.pop("duration")
        start_time = last_event["end"]
        end_time = last_event["end"] + timedelta(minutes=duration)
        # The new event end time is after the workday, assign it to the next
        if end_time > get_workday_end(end_time):
            start_time = get_next_workday_start(end_time)
            end_time = start_time + timedelta(minutes=duration)

        event_to_be_rescheduled["start"] = start_time
        event_to_be_rescheduled["end"] = end_time
        # No need to update `self.existing_events`.
        self.scheduled_events.append(event_to_be_rescheduled)
        return event_to_be_rescheduled

    def _reschedule(self, event: dict, slot: dict, slot_duration: int) -> dict:
        """Reschedule event to the provided slot.

        Remove the event from `unscheduled_events` and add to `existing_events`.
        Remove event duration from `unscheduled_event_durations`, if required.
        """
        event_duration = event.pop("duration")
        event_start = slot["start"]
        if event_duration < slot_duration:
            event_end = event_start + timedelta(minutes=event_duration)
        else:
            event_end = slot["end"]
        event["start"] = event_start
        event["end"] = event_end

        self.scheduled_events.append(event)
        self._clean_unscheduled_events(event_duration)
        bisect.insort(self.existing_events, event, key=lambda x: x["start"])
        return event

    def needs_rescheduling(self, event: dict) -> bool:
        """Check if the event needs rescheduling."""
        event_start = event["start"]
        event_end = event["end"]

        # Check if event falls during the weekends
        if event_start.date().isoweekday() > 5:
            return True

        # Check if the even falls outside the workday
        if event_start < get_workday_start(event_start) or event_end > get_workday_end(event_end):
            return True

        # Get the index of event whose start is just before the event start.
        pivot = bisect.bisect_left(self.existing_events, event["start"], key=itemgetter("start"))

        # Check if the event overlaps with the event scheduled before it.
        with suppress(IndexError):
            earlier_event = self.existing_events[pivot]
            if self.is_overlapping(earlier_event, event):
                return True

        # Check if the event overlaps with the event scheduled after it.
        with suppress(IndexError):
            next_event = self.existing_events[pivot + 1]
            if self.is_overlapping(event, next_event):
                return True

    def update_unscheduled_slots(self, event1: dict, event2: dict) -> dict:
        """Get the slots between two events.

        Generally, the slot will be only one, but in case the two events are a day apart, two slots will be created.
        """
        # Check if the events fall on different dates.
        if event1["start"].date() != event2["start"].date():
            # If the first event doesn't end at the workday end, add the gap between the event and workday end.
            workday_end = get_workday_end(event1["start"])
            duration = calculate_duration_minutes(event1["end"], workday_end)
            if duration:
                self.unscheduled_slots[duration].append({"start": event1["end"], "end": workday_end})

            # If the second doesn't start at the workday start, add the gap between the workday start and event start.
            workday_start = get_workday_start(event2["start"])
            duration = calculate_duration_minutes(workday_start, event2["start"])

            if duration:
                self.unscheduled_slots[duration].append({"start": workday_start, "end": event2["start"]})

        # If the events fall on the same date, add the gap between the events if there's any.
        duration = calculate_duration_minutes(event1["end"], event2["start"])
        if duration:
            self.unscheduled_slots[duration].append({"start": event1["end"], "end": event2["start"]})
        return self.unscheduled_slots

    def reschedule_events(self):
        """Reschedule events."""
        if not (self.unscheduled_events and self.unscheduled_slots):
            return
        sorted_slot_durations = sorted(self.unscheduled_slots.keys(), reverse=True)
        for duration in sorted_slot_durations:
            # If there's an exact match between any slot duration and event duration, assign events.
            if duration in self.unscheduled_events:
                relevant_slots = self.unscheduled_slots[duration]
                for _ in range(len(relevant_slots)):
                    if not self.unscheduled_events[duration]:
                        continue
                    event_to_reschedule = self.unscheduled_events[duration].pop(0)
                    slot = relevant_slots.pop(0)
                    self._reschedule(event_to_reschedule, slot, duration)
                # If there are still unscheduled slots left after scheduling all events of same duration,
                # assign slot to events with shorter duration.
                if relevant_slots:
                    self.assign_slots_to_shorter_events(duration, sorted_slot_durations)

            # If there is no exact match between any slot duration and event duration,
            # assign slot to events with shorter duration.
            else:
                self.assign_slots_to_shorter_events(duration, sorted_slot_durations)

            self._clean_unassigned_slots(duration, sorted_slot_durations)

    def assign_slots_to_shorter_events(self, slot_duration: int, sorted_slot_durations: list[int]) -> None:
        """Assign slot to events shorter than slot duration.

        Update `unscheduled_slots` with the time gap between the shorter event and the slot end.
        """
        if not (self.unscheduled_events and self.unscheduled_slots):
            return
        # Find the index of the longest duration that is smaller than slot duration.
        pivot = bisect.bisect_right(self.unscheduled_event_durations, slot_duration) - 1
        if pivot < 0:
            return
        # Get the longest duration that is smaller than slot duration using the index.
        relevant_event_duration = self.unscheduled_event_durations[pivot]

        # Get all the slots with duration `slot_duration` and assign events of shorter durations.
        relevant_slots = self.unscheduled_slots[slot_duration]

        for _ in range(len(relevant_slots)):
            # If all the events with `relevant_event_duration` have been scheduled,
            # assign the smaller events to `relevant_event_duration`.
            if relevant_event_duration not in self.unscheduled_events:
                pivot -= 1
                if pivot < 0:
                    break
                relevant_event_duration = self.unscheduled_event_durations[pivot]

            # Assign the first event in unscheduled_events for the duration to the first slot.
            event_to_reschedule = self.unscheduled_events[relevant_event_duration].pop(0)
            slot = relevant_slots.pop(0)
            scheduled_event = self._reschedule(event_to_reschedule, slot, slot_duration)
            # Add a new `unscheduled slot` using the time left in the slot after scheduling the event.
            self._add_remaining_time_to_unscheduled_slots(scheduled_event, slot, sorted_slot_durations)
            self._clean_unassigned_slots(slot_duration, sorted_slot_durations)

    def schedule_events(self, new_events: list[dict]):
        """Schedule all input events."""
        # Sort input events based on start time.
        sorted_new_events = sorted(new_events, key=lambda e: e["start"])

        for event in sorted_new_events:
            # If event needs rescheduling add it to unscheduled_events, to be scheduled later.
            if self.needs_rescheduling(event):
                self.update_unscheduled_events(event)
            else:
                # If event does need rescheduling add it to scheduled_events.
                # Also add the event to existing_events, since that time slot is blocked.
                event.pop("duration")
                self.scheduled_events.append(event)
                bisect.insort(self.existing_events, event, key=lambda x: x["start"])

        # If there is no unscheduled_events, persist the scheduled events.
        if not self.unscheduled_events:
            self.persist_new_events()
            return

        # if there are unscheduled events, then find available slots between events.
        for i, event in enumerate(self.existing_events):
            if self.unscheduled_events and i < len(self.existing_events) - 1:
                next_event = self.existing_events[i + 1]
                self.update_unscheduled_slots(event, next_event)
                # If we reschedule here, we will iterate less but might waste a few slot.
                # self.reschedule_events()

        # If we reschedule here, we will iterate over all the slots but will be the most efficient use of time.
        self.reschedule_events()

        # If there are still events left which weren't assigned between the events.
        # Schedule them after the last event, after one another.

        last_event = self._get_last_scheduled_event()
        for duration in self.unscheduled_event_durations:
            # Assigning smaller events first, so that we make most of the day.
            events = self.unscheduled_events[duration]
            for event in events:
                scheduled_event = self.schedule_next(last_event, event)
                last_event = scheduled_event

        # Persist the new events in the DB.
        self.persist_new_events()
