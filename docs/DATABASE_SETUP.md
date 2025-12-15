## Database Setup Guide

**Prerequisites**: Docker and Docker Compose installed

```bash
# Start PostgreSQL and Redis with one command
docker-compose up -d

# Verify services are running
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis
```

**To stop services**:
```bash
docker-compose down
```

**To remove volumes (destructive)**:
```bash
docker-compose down -v
```

## Environment Configuration

### Create `.env` File

Copy the example file and customize:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials (if using non-default values):

```bash
# Database Configuration
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=hermes_market_engine
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration (Hot Path)
REDIS_URL=redis://localhost:6379
REDIS_CHANNEL=hermes:market_data
REDIS_PORT=6379

# Cold Path Configuration
DB_BATCH_INTERVAL_SECONDS=10.0
DB_BATCH_SIZE=1000
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
DB_MAX_RETRY_ATTEMPTS=3

# Logging
LOG_LEVEL=INFO
```

### Load Environment Variables

The application automatically loads `.env` if using Pydantic's `BaseSettings`:

```python
from src.config import settings
# settings now contains all values from .env
```

## Docker Compose Configuration

The included `docker-compose.yml` provides:

- **PostgreSQL 16 Alpine** - Small, efficient image
- **Redis 7 Alpine** - In-memory data store
- **Health checks** - Automatic service verification
- **Data persistence** - Volumes for PostgreSQL and Redis
- **Networking** - Internal docker network for service-to-service communication
- **Environment variables** - Load from `.env` or use defaults

Environment variables supported:
- `DB_USER` (default: postgres)
- `DB_PASSWORD` (default: postgres)
- `DB_NAME` (default: hermes_market_engine)
- `DB_PORT` (default: 5432)
- `REDIS_PORT` (default: 6379)

Example with custom values:

```bash
DB_USER=myuser DB_PASSWORD=mypass DB_NAME=my_db docker-compose up -d
```
