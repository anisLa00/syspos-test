import sqlite3
from pathlib import Path
from contextlib import closing

DB_PATH = Path(__file__).resolve().with_name("syspos.db")


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db() -> None:
    schema = DB_PATH.with_name("schema.sql").read_text(encoding="utf-8")
    with closing(connect_db()) as connection:
        connection.executescript(schema)


if __name__ == "__main__":
    init_db()
    print("Database initialized.")