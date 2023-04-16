# Garendar

Python3 script for Scheduling events for Gary, so that no event overlaps and all events are scheduled.
- The script accepts a comma separated string as input.
- All the events are persisted in a sqlite3 db.
- The script outputs all the events.
- Each event is in the following format:

  `<start_date> -> <end_date> - <event_name>`

  Ex:

  `2022/08/23 15:00 -> 2022/08/23 16:00 - Meet Jamie for coffee`

#### System Requirements
`Python >= 3.10`

#### Steps before running the script.
1. Install poetry 
```shell
pip install poetry
```
2. Initialise project
```shell
poetry init
```
3. Run migrations
```shell
pw_migrate migrate --database sqlite:///garendar.db
```


#### Executing the script
```shell
python scheduler.py "<event_string>"
```

Example:
```shell
python scheduler.py \
"2022/08/27 16:10 -> 2022/08/27 16:40 - Meet Jamie for 30 mins, \
2022/08/27 16:20 -> 2022/08/27 16:27 - Meet Jamie for 7 mins,\
2022/08/27 17:10 -> 2022/08/27 19:40 - Meet Jamie for 2 hr 30 mins,\
2022/08/27 15:10 -> 2022/08/27 15:30 - Meet Jamie for 20 mins"
```
