#!/bin/bash

# Database initialization script for Stellar Explorer
# This script initializes the PostgreSQL database and runs Alembic migrations

set -e

echo "🚀 Stellar Explorer - Database Initialization"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running"
    exit 1
fi

# Check if services are up
echo "📦 Checking if services are running..."
if ! docker-compose ps | grep -q "postgres"; then
    echo "⚠️  PostgreSQL is not running. Starting services..."
    docker-compose up -d postgres redis
    echo "⏳ Waiting for PostgreSQL to be ready..."
    sleep 10
fi

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U stellar_user > /dev/null 2>&1; do
    echo "   PostgreSQL is unavailable - sleeping"
    sleep 2
done
echo "✅ PostgreSQL is ready!"

# Check if database exists
echo "🔍 Checking database..."
DB_EXISTS=$(docker-compose exec -T postgres psql -U stellar_user -lqt | cut -d \| -f 1 | grep -w stellar_explorer | wc -l)

if [ "$DB_EXISTS" -eq 0 ]; then
    echo "📝 Creating database 'stellar_explorer'..."
    docker-compose exec -T postgres psql -U stellar_user -c "CREATE DATABASE stellar_explorer;"
    echo "✅ Database created!"
else
    echo "✅ Database 'stellar_explorer' already exists"
fi

# Run Alembic migrations
echo "🔄 Running database migrations..."
docker-compose exec -T api alembic upgrade head

if [ $? -eq 0 ]; then
    echo "✅ Migrations completed successfully!"
else
    echo "❌ Migration failed!"
    exit 1
fi

# Show current migration version
echo ""
echo "📊 Current database version:"
docker-compose exec -T api alembic current

# Show table count
echo ""
echo "📊 Database statistics:"
TABLE_COUNT=$(docker-compose exec -T postgres psql -U stellar_user -d stellar_explorer -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
echo "   Tables created: $TABLE_COUNT"

# List all tables
echo ""
echo "📋 Tables in database:"
docker-compose exec -T postgres psql -U stellar_user -d stellar_explorer -c "\dt"

echo ""
echo "✅ Database initialization complete!"
echo ""
echo "Next steps:"
echo "  1. Start all services: make up"
echo "  2. Access API docs: http://localhost:8000/docs"
echo "  3. Access frontend: http://localhost:3000"
