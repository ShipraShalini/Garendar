import sys

from src.parse_events import parse_input_events
from src.schedule import display_all_events, schedule_event

input_events = sys.argv[1]


def main():
    events = parse_input_events(input_events)
    for event in events:
        schedule_event(*event)
    display_all_events()


if __name__ == "__main__":
    main()
