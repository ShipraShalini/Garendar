import sys

from src.parse_events import parse_input_events
from src.schedule import display_all_events
from src.simple_scheduler import Scheduler

input_events = sys.argv[1]


def main():
    events = parse_input_events(input_events)
    Scheduler().schedule_events(events)
    display_all_events()


if __name__ == "__main__":
    main()
