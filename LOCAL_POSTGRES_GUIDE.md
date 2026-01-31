# Using Local PostgreSQL Instead of Docker

## Prerequisites
1. PostgreSQL installed locally (you have this via pgAdmin)
2. pgvector extension installed
3. Database created in pgAdmin

## Steps

### 1. Install pgvector Extension

In pgAdmin, run this SQL on your database:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

### 2. Update .env File

Change the DATABASE_URL to point to localhost:

```env
# Your Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Point to your local PostgreSQL (not Docker)
DATABASE_URL=postgresql://postgres:your_password@host.docker.internal:5432/agent_network

# These are not used when using local DB, but keep them:
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=agent_network
```

**Important**: Use `host.docker.internal` instead of `localhost` so Docker can reach your Windows PostgreSQL!

### 3. Modify docker-compose.yml

Remove or comment out the `db` service since you're using local PostgreSQL:

```yaml
version: '3.8'

services:
  # Comment out or remove this entire section:
  # db:
  #   image: ankane/pgvector:latest
  #   ...

  backend:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    volumes:
      - ./backend:/app/backend
    # Remove this line:
    # depends_on:
    #   db:
    #     condition: service_healthy
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    image: nginx:alpine
    ports:
      - "3000:80"
    volumes:
      - ./frontend:/usr/share/nginx/html:ro
    depends_on:
      - backend

# Remove this if using local DB:
# volumes:
#   postgres_data:
```

### 4. Initialize Database

Run the schema manually in pgAdmin:
```sql
-- Copy contents from sql/schema.sql and run in pgAdmin
```

Or run the init script:
```bash
docker-compose up -d backend frontend
docker-compose exec backend python backend/init_db.py
```

## Verification

Check if backend can connect:
```bash
docker-compose logs backend
```

You should see: "✓ Database is ready"
