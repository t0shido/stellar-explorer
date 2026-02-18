# Stellar Explorer

A full-stack blockchain explorer for the Stellar network with real-time data processing and analytics.

## Tech Stack

- **Backend**: Python FastAPI
- **Worker/Jobs**: Celery + Redis
- **Database**: PostgreSQL
- **Frontend**: Next.js + TypeScript + Tailwind CSS
- **Infrastructure**: Docker Compose

## Project Structure

```
stellar_explorer/
├── apps/
│   ├── api/          # FastAPI backend
│   ├── web/          # Next.js frontend
│   └── worker/       # Celery worker
├── infra/            # Infrastructure configs
├── docs/             # Documentation
├── docker-compose.yml
├── Makefile
└── README.md
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Make (optional, but recommended)

### Setup

1. **Clone and navigate to the project**
   ```bash
   cd stellar_explorer
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Start all services**
   ```bash
   make up
   ```
   
   Or without Make:
   ```bash
   docker-compose up -d
   ```

4. **Initialize database and run migrations**
   ```bash
   chmod +x scripts/init_db.sh
   ./scripts/init_db.sh
   ```
   
   Or manually:
   ```bash
   make migrate
   ```

5. **Access the application**
   - **Frontend**: http://localhost:3000
   - **API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **PostgreSQL**: localhost:5432
   - **Redis**: localhost:6379

## Available Commands

```bash
make up        # Start all services
make down      # Stop all services
make logs      # View logs from all services
make restart   # Restart all services
make build     # Build all Docker images
make clean     # Remove all containers and volumes
make migrate   # Run database migrations
make shell     # Open API shell
make test      # Run tests
```

## Development

### Backend (FastAPI)

```bash
# Access API container
docker-compose exec api bash

# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "description"
```

### Frontend (Next.js)

```bash
# Access web container
docker-compose exec web sh

# Install new package
docker-compose exec web npm install package-name
```

### Worker (Celery)

```bash
# View worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker
```

## Database Schema

The project uses a comprehensive PostgreSQL schema designed for blockchain analysis:

**Core Tables:**
- `accounts` - Stellar accounts with risk scoring
- `assets` - Asset definitions and metadata
- `account_balances` - Balance snapshots over time
- `transactions` - Transaction records
- `operations` - Individual operations within transactions

**Analysis Tables:**
- `counterparty_edges` - Transaction graph relationships
- `watchlists` - Account monitoring lists
- `watchlist_members` - Watchlist memberships
- `flags` - Risk flags and compliance markers
- `alerts` - System alerts and notifications

**Key Features:**
- JSONB fields for flexible metadata storage
- Comprehensive indexing for performance
- Foreign key relationships with cascade rules
- Temporal tracking (first_seen, last_seen, created_at)

See [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) for complete schema documentation.

## Features

- 🔍 Search accounts, transactions, and assets
- 📊 Real-time network statistics
- 📈 Historical data visualization
- 🔔 Background job processing with Celery
- 🚀 Fast API with automatic documentation
- 💾 PostgreSQL for reliable data storage
- 🎨 Modern UI with Tailwind CSS
- 🛡️ Risk scoring and compliance tracking
- 📈 Network graph analysis
- 🚨 Alert and notification system

## Environment Variables

See `.env.example` for all required environment variables.

## Testing

```bash
# Run all tests
make test

# Run API tests only
docker-compose exec api pytest

# Run frontend tests only
docker-compose exec web npm test
```

## Troubleshooting

### Services won't start

```bash
# Check logs
make logs

# Rebuild containers
make build
make up
```

### Database connection issues

```bash
# Ensure PostgreSQL is healthy
docker-compose ps

# Reset database
make clean
make up
make migrate
```

### Port conflicts

If ports 3000, 8000, 5432, or 6379 are already in use, modify the port mappings in `docker-compose.yml`.

## License

MIT
