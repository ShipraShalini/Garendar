import pytest
from _pytest.fixtures import fixture
from peewee import SqliteDatabase

from models.event import Event

MODELS = [Event]


@fixture(autouse=True, scope="session")
def my_fixture():
    test_db = SqliteDatabase(":memory:")
    test_db.bind(MODELS, bind_refs=False, bind_backrefs=False)
    test_db.connect()
    test_db.create_tables(MODELS)
    yield
    test_db.close()


@pytest.fixture()
def db():
    yield
    Event.delete()
