import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import OperationalError

from database.config import Settings

WAIT_SECONDS = 30


def connect_admin(url: URL):
    engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    deadline = time.monotonic() + WAIT_SECONDS
    while True:
        try:
            return engine, engine.connect()
        except OperationalError:
            if time.monotonic() > deadline:
                raise
            time.sleep(1)


def ensure_database(url: URL) -> None:
    engine, conn = connect_admin(url)
    with conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
        ).scalar()
        if exists:
            print(f"Database {url.database} already exists on {url.host}:{url.port}")
        else:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
            print(f"Created database {url.database} on {url.host}:{url.port}")
    engine.dispose()


def main() -> int:
    for env_file in (".env", ".env.test"):
        ensure_database(make_url(Settings(_env_file=env_file).database_url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
