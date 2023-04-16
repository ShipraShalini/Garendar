from peewee import SqliteDatabase

from src.config import DB_NAME

db = SqliteDatabase(DB_NAME)
