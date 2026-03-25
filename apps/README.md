# Smart Home Sensor Management API

## Prerequisites

- Docker and Docker Compose
- Optional: Postman for manual API checks

## Getting Started

### Option 1: Using Docker Compose (Recommended)

The easiest way to start the application is to use Docker Compose:

```bash
./init.sh
```

This script will:

1. Build and start the PostgreSQL and application containers
2. Wait for the services to be ready
3. Display information about how to access the API

Alternatively, you can run Docker Compose directly:

```bash
docker compose up --build -d
```

The services will be available at:

- Monolith API: http://localhost:8080
- Temperature API: http://localhost:8081

### Option 2: Manual setup

If you prefer to run the application without Docker:

1. Start the PostgreSQL database:

```bash
docker-compose up -d postgres
```

2. Build and run the application:

```bash
go build -o smarthome
./smarthome
```

## API Testing

A Postman collection is provided for testing the API. Import the `smarthome-api.postman_collection.json` file into Postman to get started.

To reproduce the coursework check:

1. Run `Create Sensor` for a temperature sensor.
2. Run `Get All Sensors` several times.
3. Verify that the `value` for temperature sensors changes between requests.

## Failure and latency simulation

The `temperature-api` service supports environment variables in `docker-compose.yml` that help expose monolith limitations:

- `TEMPERATURE_DELAY_MS` - adds a fixed delay to every temperature response.
- `TEMPERATURE_FAILURE_RATE` - returns intermittent `503` responses, value from `0` to `1`.

Examples:

- `TEMPERATURE_DELAY_MS=1500` shows how the monolith waits on the upstream dependency.
- `TEMPERATURE_FAILURE_RATE=0.5` simulates an unstable telemetry provider.

## API Endpoints

- `GET /health` - Health check
- `GET /api/v1/sensors` - Get all sensors
- `GET /api/v1/sensors/:id` - Get a specific sensor
- `POST /api/v1/sensors` - Create a new sensor
- `PUT /api/v1/sensors/:id` - Update a sensor
- `DELETE /api/v1/sensors/:id` - Delete a sensor
- `PATCH /api/v1/sensors/:id/value` - Update a sensor's value and status

## VPS notes

For a coursework-grade VPS deployment:

- Ubuntu 24.04 LTS is the easiest target for Docker-based deployment.
- 2 vCPU and 4 GB RAM is comfortable for the monolith, Postgres, and `temperature-api`.
- 25-30 GB SSD is enough for the services, logs, and a few rebuilds.
- A public IP is sufficient; add a firewall and expose only SSH plus the ports you truly need.
