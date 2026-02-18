.PHONY: help up down logs restart build clean migrate shell test

help:
	@echo "Stellar Explorer - Available commands:"
	@echo "  make up        - Start all services"
	@echo "  make down      - Stop all services"
	@echo "  make logs      - View logs from all services"
	@echo "  make restart   - Restart all services"
	@echo "  make build     - Build all Docker images"
	@echo "  make clean     - Remove all containers and volumes"
	@echo "  make migrate   - Run database migrations"
	@echo "  make shell     - Open API shell"
	@echo "  make test      - Run tests"

up:
	docker-compose up -d
	@echo "✅ Services started!"
	@echo "API: http://localhost:8000"
	@echo "Web: http://localhost:3000"
	@echo "API Docs: http://localhost:8000/docs"

down:
	docker-compose down

logs:
	docker-compose logs -f

restart:
	docker-compose restart

build:
	docker-compose build

clean:
	docker-compose down -v
	@echo "✅ All containers and volumes removed"

migrate:
	docker-compose exec api alembic upgrade head
	@echo "✅ Migrations applied"

shell:
	docker-compose exec api python

test:
	docker-compose exec api pytest
	docker-compose exec web npm test
