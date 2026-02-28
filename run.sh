#!/bin/bash
set -e

# Use PORT from environment or default to 8018
BIND_PORT=${PORT:-8018}

echo "Starting Gunicorn on port: $BIND_PORT"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$BIND_PORT \
    --log-file - \
    --access-logfile - \
    --error-logfile -
