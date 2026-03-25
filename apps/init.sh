#!/bin/bash

# Exit on any error
set -e

if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  COMPOSE_CMD="docker compose"
fi

echo "Starting the Smart Home Sensor API..."
echo "Building and starting containers..."
$COMPOSE_CMD up --build -d

echo "Waiting for services to be ready..."
# Wait for PostgreSQL to be ready
for i in {1..30}; do
  if docker exec smarthome-postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "PostgreSQL is ready!"
    break
  fi
  echo "Waiting for PostgreSQL to start... ($i/30)"
  sleep 1
done

# Check if PostgreSQL is ready
if ! docker exec smarthome-postgres pg_isready -U postgres > /dev/null 2>&1; then
  echo "Error: PostgreSQL did not start within the expected time."
  exit 1
fi

echo "All services are up and running!"
echo "The API is available at http://localhost:8080"
echo "The temperature API is available at http://localhost:8081"
echo ""
echo "To view logs, run: $COMPOSE_CMD logs -f"
echo "To stop the services, run: $COMPOSE_CMD down"