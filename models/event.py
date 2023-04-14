from uuid import uuid4

from peewee import DateTimeField, Model, TextField, UUIDField

from models import db
from src.constants import DATE_FORMAT


class Event(Model):
    id = UUIDField(primary_key=True, default=uuid4)
    description = TextField()
    start = DateTimeField(index=True)
    end = DateTimeField(index=True)

    class Meta:
        database = db

    def duration(self):
        return self.end - self.start

    def __str__(self):
        return (
            f"{self.start.strftime(DATE_FORMAT)} -> "
            f"{self.end.strftime(DATE_FORMAT)} - "
            f"{self.description}"
        )
