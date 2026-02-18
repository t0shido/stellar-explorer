# Architecture Documentation

## Overview

Stellar Explorer is a full-stack application for exploring the Stellar blockchain network. It follows a microservices architecture with clear separation of concerns.

## System Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ HTTP/WebSocket
       │
┌──────▼──────┐
│  Next.js    │
│  Frontend   │
│  (Port 3000)│
└──────┬──────┘
       │
       │ REST API
       │
┌──────▼──────┐      ┌──────────┐
│   FastAPI   │◄─────┤PostgreSQL│
│   Backend   │      │ Database │
│  (Port 8000)│      └──────────┘
└──────┬──────┘
       │
       │ Task Queue
       │
┌──────▼──────┐      ┌──────────┐
│   Celery    │◄─────┤  Redis   │
│   Worker    │      │  Broker  │
└──────┬──────┘      └──────────┘
       │
       │ API Calls
       │
┌──────▼──────┐
│   Stellar   │
│   Network   │
└─────────────┘
```

## Components

### Frontend (Next.js + TypeScript)

**Location:** `/apps/web`

**Responsibilities:**
- User interface and interaction
- Data visualization
- API consumption
- Client-side routing

**Key Technologies:**
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- Axios for API calls
- Lucide React for icons

**Structure:**
```
apps/web/
├── src/
│   ├── app/              # Next.js pages
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Home page
│   │   ├── accounts/     # Accounts page
│   │   ├── transactions/ # Transactions page
│   │   └── network/      # Network info page
│   └── lib/              # Utilities
│       ├── api.ts        # API client
│       └── utils.ts      # Helper functions
```

---

### Backend (FastAPI)

**Location:** `/apps/api`

**Responsibilities:**
- REST API endpoints
- Database operations
- Business logic
- Data validation
- Integration with Stellar network

**Key Technologies:**
- FastAPI
- SQLAlchemy (ORM)
- Alembic (migrations)
- Pydantic (validation)
- Stellar SDK

**Structure:**
```
apps/api/
├── app/
│   ├── main.py           # Application entry point
│   ├── core/             # Core configuration
│   │   └── config.py     # Settings
│   ├── db/               # Database
│   │   ├── database.py   # Connection
│   │   └── models.py     # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   │   ├── account.py
│   │   └── transaction.py
│   └── api/              # API routes
│       └── v1/
│           ├── router.py
│           └── endpoints/
│               ├── accounts.py
│               ├── transactions.py
│               └── stellar.py
```

**API Versioning:**
- All endpoints are prefixed with `/api/v1`
- Future versions can be added as `/api/v2`, etc.

---

### Worker (Celery)

**Location:** `/apps/worker`

**Responsibilities:**
- Background job processing
- Periodic tasks
- Data synchronization
- Heavy computations

**Key Technologies:**
- Celery
- Redis (broker & backend)
- Stellar SDK

**Structure:**
```
apps/worker/
├── app/
│   ├── celery_app.py     # Celery configuration
│   ├── core/
│   │   └── config.py     # Settings
│   └── tasks/
│       └── stellar_tasks.py  # Task definitions
```

**Periodic Tasks:**
- `sync_recent_transactions`: Every 60 seconds
- `update_network_stats`: Every 5 minutes

---

### Database (PostgreSQL)

**Responsibilities:**
- Persistent data storage
- Relational data management
- Transaction support

**Schema:**

**accounts**
- id (PK)
- account_id (unique)
- sequence
- balance
- num_subentries
- created_at
- updated_at

**transactions**
- id (PK)
- hash (unique)
- source_account
- fee
- operation_count
- successful
- ledger
- created_at

**assets**
- id (PK)
- asset_code
- asset_issuer
- asset_type
- num_accounts
- amount
- created_at
- updated_at

---

### Message Broker (Redis)

**Responsibilities:**
- Task queue management
- Result storage
- Caching (future)
- Pub/Sub messaging (future)

---

## Data Flow

### 1. User Request Flow

```
User → Frontend → API → Database → API → Frontend → User
```

1. User interacts with the frontend
2. Frontend makes HTTP request to API
3. API queries database
4. API returns JSON response
5. Frontend displays data

### 2. Background Task Flow

```
API → Redis → Celery Worker → Stellar Network → Database
```

1. API triggers background task
2. Task is queued in Redis
3. Celery worker picks up task
4. Worker fetches data from Stellar
5. Worker stores data in database

### 3. Periodic Task Flow

```
Celery Beat → Redis → Celery Worker → Stellar Network → Database
```

1. Celery Beat schedules periodic task
2. Task is queued in Redis
3. Celery worker executes task
4. Worker syncs data from Stellar
5. Worker updates database

---

## Design Patterns

### Clean Architecture

- **Separation of Concerns**: Each layer has a specific responsibility
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Domain-Driven Design**: Business logic is isolated from infrastructure

### Repository Pattern

- Database access is abstracted through SQLAlchemy ORM
- Models represent domain entities
- Schemas handle data validation and serialization

### Service Layer

- Business logic is encapsulated in service functions
- Services orchestrate operations across multiple repositories
- Services are reusable across different endpoints

---

## Security Considerations

1. **CORS**: Configured to allow frontend origin
2. **Environment Variables**: Sensitive data stored in `.env`
3. **Database**: Connection pooling and prepared statements
4. **API**: Input validation with Pydantic
5. **Docker**: Isolated containers for each service

---

## Scalability

### Horizontal Scaling

- **Frontend**: Can be deployed to CDN
- **API**: Stateless, can run multiple instances
- **Worker**: Can run multiple worker processes
- **Database**: Can use read replicas

### Vertical Scaling

- Increase container resources in `docker-compose.yml`
- Adjust worker concurrency settings
- Optimize database queries and indexes

---

## Monitoring & Logging

### Current Implementation

- Console logging in all services
- Docker logs accessible via `docker-compose logs`

### Future Enhancements

- Centralized logging (ELK stack)
- Application monitoring (Prometheus + Grafana)
- Error tracking (Sentry)
- Performance monitoring (New Relic)

---

## Development Workflow

1. **Local Development**: Docker Compose
2. **Version Control**: Git
3. **Testing**: Pytest (API), Jest (Frontend)
4. **CI/CD**: GitHub Actions / GitLab CI
5. **Deployment**: Docker containers

---

## Technology Decisions

### Why FastAPI?

- Modern, fast Python framework
- Automatic API documentation
- Type hints and validation
- Async support

### Why Next.js?

- Server-side rendering
- File-based routing
- Built-in optimization
- Great developer experience

### Why Celery?

- Mature task queue
- Flexible scheduling
- Reliable message delivery
- Good monitoring tools

### Why PostgreSQL?

- ACID compliance
- Rich feature set
- JSON support
- Strong community

### Why Docker?

- Consistent environments
- Easy deployment
- Service isolation
- Reproducible builds
