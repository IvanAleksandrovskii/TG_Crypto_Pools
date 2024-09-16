#!/bin/sh

# Wait until Postgres is ready
POSTGRES_PORT=5432
while ! nc -z pg "$POSTGRES_PORT"; do sleep 1; done

# Run migrations
alembic upgrade head

# Collect first data
# python3 collect_data_on_start.py  # TODO: think how to make it run only once, when container is build and then just follow the schedule

# Run the app
exec python3 main.py