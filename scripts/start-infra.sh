#!/bin/bash
# Start infrastructure services (Redpanda, PostgreSQL)

set -e

echo "🚀 Starting Pipeline Whisperer infrastructure..."

cd "$(dirname "$0")/.."

# Start Docker Compose services
docker compose -f docker/docker-compose.yaml up -d

echo "⏳ Waiting for services to be healthy..."
sleep 5

# Wait for Redpanda
echo "Checking Redpanda..."
until docker exec pipeline-redpanda rpk cluster health 2>/dev/null | grep -q "Healthy"; do
  echo "  Waiting for Redpanda to be healthy..."
  sleep 2
done
echo "✅ Redpanda is healthy"

# Wait for PostgreSQL
echo "Checking PostgreSQL..."
until docker exec pipeline-postgres pg_isready -U pipeline_user 2>/dev/null | grep -q "accepting connections"; do
  echo "  Waiting for PostgreSQL to be ready..."
  sleep 2
done
echo "✅ PostgreSQL is ready"

# Create Kafka topics
echo "Creating Kafka topics..."
docker exec pipeline-redpanda rpk topic create leads.raw --partitions 3 --replicas 1 || echo "  Topic leads.raw already exists"
docker exec pipeline-redpanda rpk topic create leads.scored --partitions 3 --replicas 1 || echo "  Topic leads.scored already exists"
docker exec pipeline-redpanda rpk topic create outreach.events --partitions 3 --replicas 1 || echo "  Topic outreach.events already exists"

echo ""
echo "✅ All services are up and running!"
echo ""
echo "Access points:"
echo "  - Redpanda Console: http://localhost:8080"
echo "  - PostgreSQL: localhost:5432 (user: pipeline_user, db: pipeline_db)"
echo "  - Kafka brokers: localhost:19092"
echo ""
echo "To view logs: docker compose -f docker/docker-compose.yaml logs -f"
echo "To stop: docker compose -f docker/docker-compose.yaml down"
