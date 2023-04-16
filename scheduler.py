import sys

from src.event_parser import parse_input_events
from src.exceptions import ValidationError
from src.scheduler import Scheduler
from src.utils import display_all_events

input_events = sys.argv[1]


def main():
    events = parse_input_events(input_events)
    Scheduler().schedule_events(events)
    display_all_events()


if __name__ == "__main__":
    try:
        main()
    except ValidationError as e:
        print(e)
        exit(1)
