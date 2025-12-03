#!/bin/bash

# Get the project root directory (parent of scripts directory)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Set PYTHONPATH to include project root
export PYTHONPATH="${PROJECT_ROOT}:${PYTHONPATH}"

uv run scripts/run_collector.py &
COLLECTOR_PID=$!

uv run scripts/run_analytics.py &
ANALYTICS_PID=$!

echo "Services started: Collector=$COLLECTOR_PID, Analytics=$ANALYTICS_PID"

# Trap signals for graceful shutdown
trap "kill $COLLECTOR_PID $ANALYTICS_PID; wait" SIGINT SIGTERM

wait