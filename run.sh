#!/bin/bash
set -e

# Appliku sets PORT to match container_port in appliku.yaml
BIND_PORT=${PORT:-8000}

echo "Starting Gunicorn on port: $BIND_PORT"
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:$BIND_PORT \
    --log-file - \
    --access-logfile - \
    --error-logfile -
