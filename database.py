import sqlite3
from pathlib import Path
from contextlib import closing
import os

PROJECT_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("SYSPOS_DB_PATH", str(PROJECT_DIR / "syspos.db")))
SCHEMA_PATH = PROJECT_DIR / "schema.sql"


def connect_db() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db() -> None:
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with closing(connect_db()) as connection:
        connection.executescript(schema)


if __name__ == "__main__":
    init_db()
    print("Database initialized.")