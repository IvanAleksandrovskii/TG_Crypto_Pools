#!/bin/sh

# Wait until Postgres is ready
POSTGRES_PORT=5432
while ! nc -z pg "$POSTGRES_PORT"; do sleep 1; done

# Run migrations
alembic upgrade head

# Check if initial data collection has been done
INIT_FLAG="/app/.init_data_collected"
if [ ! -f "$INIT_FLAG" ]; then
    echo "Running initial data collection..."
    python3 collect_data_on_start.py
    # Create the flag file to indicate initial collection is done
    touch "$INIT_FLAG"
else
    echo "Initial data already collected. Skipping..."
fi

# Run the app
exec python3 main.py