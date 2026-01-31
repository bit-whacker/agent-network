#!/bin/bash

echo "=== Complete Reset and Setup ==="
echo ""

echo "1. Stopping all containers..."
docker-compose down -v

echo ""
echo "2. Starting fresh containers..."
docker-compose up -d

echo ""
echo "3. Waiting for database (20 seconds)..."
sleep 20

echo ""
echo "4. Creating extensions..."
docker-compose exec -T db psql -U postgres -d agent_network -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker-compose exec -T db psql -U postgres -d agent_network -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
docker-compose exec -T db psql -U postgres -d agent_network -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"

echo ""
echo "5. Running schema (this may show some errors, that's OK)..."
docker-compose exec -T db psql -U postgres -d agent_network < sql/schema.sql 2>&1 | grep -v "already exists" | grep -v "does not exist, skipping"

echo ""
echo "6. Checking backend connection..."
docker-compose logs backend | tail -20

echo ""
echo "=========================================="
echo "✓ Setup complete!"
echo ""
echo "Frontend: http://localhost:3000"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "If frontend shows errors, check backend logs:"
echo "  docker-compose logs backend"
echo "=========================================="
