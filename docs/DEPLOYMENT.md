# Deployment Guide

## Local Development

### Prerequisites

- Docker Desktop
- Docker Compose
- Git

### Quick Start

1. **Clone the repository**
   ```bash
   cd stellar_explorer
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   ```

3. **Start services**
   ```bash
   make up
   ```

4. **Run migrations**
   ```bash
   make migrate
   ```

5. **Access the application**
   - Frontend: http://localhost:3000
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

---

## Production Deployment

### Option 1: Docker Compose (Single Server)

**Best for:** Small to medium applications

1. **Prepare server**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Clone repository**
   ```bash
   git clone <repository-url>
   cd stellar_explorer
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   nano .env  # Edit with production values
   ```

4. **Update docker-compose for production**
   ```yaml
   # Remove volume mounts for code
   # Change command to production mode
   # Add restart: always
   ```

5. **Deploy**
   ```bash
   docker-compose up -d
   ```

---

### Option 2: Kubernetes

**Best for:** Large-scale applications

1. **Create Kubernetes manifests**
   ```bash
   mkdir k8s
   ```

2. **Deploy to cluster**
   ```bash
   kubectl apply -f k8s/
   ```

3. **Set up ingress**
   ```bash
   kubectl apply -f k8s/ingress.yaml
   ```

---

### Option 3: Cloud Platforms

#### AWS

**Services:**
- ECS/Fargate for containers
- RDS for PostgreSQL
- ElastiCache for Redis
- ALB for load balancing
- Route53 for DNS

**Steps:**
1. Build and push Docker images to ECR
2. Create ECS task definitions
3. Set up RDS instance
4. Configure ElastiCache
5. Create ECS services
6. Set up ALB and target groups

#### Google Cloud Platform

**Services:**
- Cloud Run for containers
- Cloud SQL for PostgreSQL
- Memorystore for Redis
- Cloud Load Balancing

#### Azure

**Services:**
- Container Instances
- Azure Database for PostgreSQL
- Azure Cache for Redis
- Application Gateway

---

## Environment Variables

### Production Settings

```bash
# Database
POSTGRES_USER=stellar_prod_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=stellar_explorer_prod
DATABASE_URL=postgresql://user:pass@host:5432/db

# Redis
REDIS_URL=redis://redis-host:6379/0

# API
API_HOST=0.0.0.0
API_PORT=8000
SECRET_KEY=<generate-strong-secret>
ENVIRONMENT=production

# Celery
CELERY_BROKER_URL=redis://redis-host:6379/0
CELERY_RESULT_BACKEND=redis://redis-host:6379/0

# Stellar
STELLAR_NETWORK=public  # or testnet
STELLAR_HORIZON_URL=https://horizon.stellar.org

# Frontend
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```

---

## SSL/TLS Configuration

### Using Nginx Reverse Proxy

1. **Install Nginx**
   ```bash
   sudo apt install nginx
   ```

2. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name yourdomain.com;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl;
       server_name yourdomain.com;

       ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }

       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Get SSL certificate**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d yourdomain.com
   ```

---

## Database Migrations

### Creating Migrations

```bash
# Inside API container
docker-compose exec api alembic revision --autogenerate -m "description"
```

### Running Migrations

```bash
# Local
make migrate

# Production
docker-compose exec api alembic upgrade head
```

### Rolling Back

```bash
docker-compose exec api alembic downgrade -1
```

---

## Backup & Recovery

### Database Backup

```bash
# Backup
docker-compose exec postgres pg_dump -U stellar_user stellar_explorer > backup.sql

# Restore
docker-compose exec -T postgres psql -U stellar_user stellar_explorer < backup.sql
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * /path/to/backup-script.sh
```

---

## Monitoring

### Health Checks

- API: `http://localhost:8000/health`
- Database: Check container status
- Redis: Check container status
- Worker: Check Celery logs

### Logging

```bash
# View all logs
make logs

# View specific service
docker-compose logs -f api
docker-compose logs -f worker
```

---

## Performance Optimization

### Frontend

1. **Build optimization**
   ```bash
   docker-compose exec web npm run build
   ```

2. **Enable caching**
   - Configure CDN
   - Set proper cache headers

### Backend

1. **Database indexing**
   - Add indexes to frequently queried columns
   - Use EXPLAIN to analyze queries

2. **Connection pooling**
   - Configure SQLAlchemy pool size
   - Use pgBouncer for connection pooling

3. **Caching**
   - Implement Redis caching
   - Cache expensive queries

### Worker

1. **Concurrency**
   ```bash
   celery -A app.celery_app worker --concurrency=4
   ```

2. **Task optimization**
   - Batch operations
   - Use task priorities

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Use strong SECRET_KEY
- [ ] Enable HTTPS
- [ ] Configure CORS properly
- [ ] Set up firewall rules
- [ ] Regular security updates
- [ ] Database backups
- [ ] Monitor logs for suspicious activity
- [ ] Use environment variables for secrets
- [ ] Implement rate limiting

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose build --no-cache
docker-compose up -d
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check connection string
docker-compose exec api env | grep DATABASE_URL
```

### Worker not processing tasks

```bash
# Check worker logs
docker-compose logs worker

# Check Redis connection
docker-compose exec worker redis-cli -h redis ping
```

---

## Scaling

### Horizontal Scaling

1. **API**
   ```bash
   docker-compose up -d --scale api=3
   ```

2. **Worker**
   ```bash
   docker-compose up -d --scale worker=5
   ```

3. **Load Balancer**
   - Use Nginx or HAProxy
   - Configure round-robin or least-connections

### Vertical Scaling

Update `docker-compose.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

---

## Maintenance

### Updating Dependencies

```bash
# Backend
docker-compose exec api pip install --upgrade -r requirements.txt

# Frontend
docker-compose exec web npm update
```

### Database Maintenance

```bash
# Vacuum
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "VACUUM ANALYZE;"

# Reindex
docker-compose exec postgres psql -U stellar_user -d stellar_explorer -c "REINDEX DATABASE stellar_explorer;"
```
