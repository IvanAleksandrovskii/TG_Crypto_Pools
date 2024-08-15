#!/bin/sh

# Wait until Postgres is ready
POSTGRES_PORT=5432
while ! nc -z pg "$POSTGRES_PORT"; do sleep 1; done

## Set the python path
#export PYTHONPATH=$(pwd)
# Run migrations
alembic upgrade head

# Run the app
exec python3 main.py