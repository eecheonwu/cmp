# CMP Docker Development Environment

This document provides a complete guide for setting up a local development environment using Docker to test AWS deployment and database functionality.

## Overview

The Docker setup includes:

- **PostgreSQL 15** - Primary database with all CMP tables
- **Redis 7** - For Celery task queue and rate limiting
- **LocalStack** - AWS service mocking (KMS, Secrets Manager, STS)
- **Backend API** - FastAPI application
- **Celery Worker** - Background task processing
- **Frontend** - React PWA development server
- **Adminer** - Database management UI (optional)

## Prerequisites

- Docker Desktop (Windows) or Docker Engine (Linux/macOS)
- Docker Compose v3.8+
- At least 4GB RAM allocated to Docker

## Quick Start

1. **Start all services:**

   ```bash
   docker-compose up -d
   ```

2. **Wait for services to be ready (30-60 seconds):**

   ```bash
   docker-compose logs -f backend
   ```

3. **Access the services:**
   - Backend API: <http://localhost:8000>
   - API Docs (Swagger): <http://localhost:8000/docs>
   - Frontend: <http://localhost:5173>
   - Adminer (DB UI): <http://localhost:8080>
   - LocalStack: <http://localhost:4566>

4. **Stop all services:**

   ```bash
   docker-compose down
   ```

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network (cmp-network)              │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Backend   │◄──►│   Postgres  │    │   Redis     │     │
│  │  (FastAPI)  │    │  (Database) │    │  (Cache)    │     │
│  └─────────────┘    └─────────────┘    └─────────────┘     │
│         ▲                                                   │
│         │                                                   │
│  ┌─────────────┐                                           │
│  │ Celery      │                                           │
│  │ Worker      │                                           │
│  └─────────────┘                                           │
│         ▲                                                   │
│         │                                                   │
│  ┌─────────────┐    ┌─────────────┐                         │
│  │  Frontend   │    │ LocalStack  │                         │
│  │  (React)    │    │  (AWS Mock) │                         │
│  └─────────────┘    └─────────────┘                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Environment Configuration

### Using the Docker Environment

The `.env.docker` file contains all necessary environment variables for the Docker setup. Copy it to `.env` in the project root:

```bash
cp .env.docker .env
```

### Key Environment Variables

| Variable | Description | Docker Value |
|----------|-------------|--------------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+asyncpg://cmp_user:cmp_password@postgres:5432/cmp_db` |
| `REDIS_URL` | Redis connection string | `redis://redis:6379/0` |
| `AWS_ENDPOINT_URL` | LocalStack endpoint | `http://localstack:4566` |
| `KMS_KEY_ID` | KMS key identifier | `test-master-key` |

## AWS Service Mocking with LocalStack

### KMS (Key Management Service)

LocalStack provides a mock KMS service for testing encryption without real AWS credentials.

**Initialize KMS key:**

```bash
# After starting LocalStack, run the init script
docker-compose exec localstack /tmp/localstack-setup/init-kms.sh
```

**Or manually create a key:**

```bash
# Access LocalStack container
docker-compose exec localstack sh

# Create KMS key
awslocal kms create-key \
  --description "CMP Development Master Key" \
  --key-usage "ENCRYPT_DECRYPT" \
  --query 'KeyMetadata.KeyId' \
  --output text
```

### Testing AWS Integration

The backend is configured to use LocalStack when `AWS_ENDPOINT_URL` is set. All KMS operations will be directed to the mock service.

## Database Management

### Access Database via Adminer

1. Open <http://localhost:8080>
2. Use these credentials:
   - System: PostgreSQL
   - Server: postgres
   - Username: cmp_user
   - Password: cmp_password
   - Database: cmp_db

### Run Migrations

Migrations run automatically on backend startup. To run manually:

```bash
docker-compose exec backend alembic upgrade head
```

### Create New Migration

```bash
docker-compose exec backend alembic revision --autogenerate -m "description"
```

## Development Workflow

### Hot Reload

The frontend supports hot reload:

- Backend: Hot reload is disabled in Docker due to WatchFiles I/O errors on Windows Docker bind mounts. To pick up code changes, restart the backend container: `docker-compose restart backend`
- Frontend: Vite HMR (Hot Module Replacement) enabled

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery-worker
```

### Execute Commands

```bash
# Run Python shell
docker-compose exec backend python

# Run tests
docker-compose exec backend pytest

# Run Alembic commands
docker-compose exec backend alembic current
```

## Testing AWS Deployment

### Test KMS Encryption

```python
# In the backend container
import boto3
from botocore.config import Config

kms = boto3.client(
    'kms',
    endpoint_url='http://localstack:4566',
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    config=Config(region_name='us-east-1')
)

# List keys
response = kms.list_keys()
print(response['Keys'])
```

### Test Database Connection

```bash
# From host machine
psql -h localhost -U cmp_user -d cmp_db -p 5432
```

## Production Considerations

When deploying to production:

1. **Remove LocalStack** - Use real AWS services
2. **Use real RDS** - AWS RDS PostgreSQL instead of container
3. **Use real ElastiCache** - AWS Redis instead of container
4. **Update environment variables** - Use production secrets
5. **Enable HTTPS** - Add SSL/TLS termination
6. **Use multi-stage builds** - Optimize frontend Dockerfile

## Troubleshooting

### Services won't start

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs backend

# Restart specific service
docker-compose restart backend
```

### Database connection issues

```bash
# Check if PostgreSQL is ready
docker-compose exec postgres pg_isready

# Check database logs
docker-compose logs postgres
```

### LocalStack not ready

```bash
# Check health
curl http://localhost:4566/_localstack/health

# Wait and retry
sleep 10 && docker-compose logs localstack
```

### Reset everything

```bash
# Stop and remove all containers, networks, and volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

## Docker Commands Reference

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start all services in detached mode |
| `docker-compose up` | Start all services with logs |
| `docker-compose down` | Stop all services |
| `docker-compose down -v` | Stop services and remove volumes |
| `docker-compose build` | Build all images |
| `docker-compose logs -f` | Follow logs from all services |
| `docker-compose ps` | List running services |
| `docker-compose exec <service> <command>` | Execute command in service |

## File Structure

```
cmp/
├── docker-compose.yml          # Main Docker Compose configuration
├── .env.docker               # Docker environment variables
├── DOCKER-README.md          # This file
├── init-db/
│   └── init.sql              # Database initialization script
├── localstack-setup/
│   └── init-kms.sh           # KMS key initialization script
├── src/
│   ├── backend/
│   │   ├── Dockerfile        # Backend Docker image
│   │   ├── requirements.txt    # Python dependencies
│   │   └── ...
│   └── frontend/
│       ├── Dockerfile        # Frontend Docker image
│       ├── package.json        # Node dependencies
│       └── ...
└── logs/                     # Application logs (created on startup)
