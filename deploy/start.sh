#!/bin/bash

echo "Running migrations..."
python manage.py migrate --noinput

if [ $? -ne 0 ]; then
  echo "Migration failed!"
  exit 1
fi

echo "Migrations completed successfully"

# Calculate sensible default for workers: (2 * CPUs) + 1
# Fallback to 3 workers if nproc is not available (though it should be in standard linux containers)
if command -v nproc > /dev/null; then
    CORES=$(nproc)
else
    CORES=1
fi
DEFAULT_WORKERS=$((2 * CORES + 1))

# Allow env vars to override defaults
WORKERS=${WORKERS:-$DEFAULT_WORKERS}
TIMEOUT=${GUNICORN_TIMEOUT:-120}
LOG_LEVEL=${GUNICORN_LOG_LEVEL:-info}

echo "Starting gunicorn with $WORKERS workers, timeout $TIMEOUT, log level $LOG_LEVEL..."
exec gunicorn core.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers "$WORKERS" \
    --timeout "$TIMEOUT" \
    --log-level "$LOG_LEVEL"