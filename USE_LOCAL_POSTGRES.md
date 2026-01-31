# Using Your Existing PostgreSQL (pgAdmin)

Since Docker PostgreSQL is having issues, let's use your existing PostgreSQL installation.

## Step 1: Install pgvector Extension

Open pgAdmin and run this on your `agent_network` database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

**If you get "extension not found" error:**

### For Windows PostgreSQL:
1. Download pgvector from: https://github.com/pgvector/pgvector/releases
2. Or use this simpler method:
   - Open pgAdmin
   - Right-click Extensions → Create → Extension
   - Name: `vector`
   - If not available, you may need to install it manually

### Alternative: Skip vector extension for now
The application will work without vector search (just won't do semantic matching).

---

## Step 2: Run Database Schema

In pgAdmin, open Query Tool on your `agent_network` database and execute:

```sql
-- Copy the entire contents of sql/schema.sql and run it
-- This creates all tables, functions, indexes, and sample data
```

Or from command line:
```powershell
psql -U postgres -d agent_network -f sql/schema.sql
```

---

## Step 3: Update .env File

Update your `.env` to point to localhost PostgreSQL:

```env
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here

# Point to your local PostgreSQL
DATABASE_URL=postgresql://postgres:YOUR_PGADMIN_PASSWORD@host.docker.internal:5432/agent_network

# These are not used when using local DB
POSTGRES_USER=postgres
POSTGRES_PASSWORD=YOUR_PGADMIN_PASSWORD
POSTGRES_DB=agent_network

BACKEND_PORT=8000
FRONTEND_PORT=3000
DEBUG=True
```

**Important:** 
- Replace `YOUR_PGADMIN_PASSWORD` with your actual PostgreSQL password
- Use `host.docker.internal` not `localhost` (so Docker can reach your Windows PostgreSQL)

---

## Step 4: Use Alternative Docker Compose

```powershell
# Use the version without database container
docker-compose -f docker-compose-local-db.yml up -d
```

Or rename files:
```powershell
# Backup original
mv docker-compose.yml docker-compose-with-db.yml

# Use local DB version
mv docker-compose-local-db.yml docker-compose.yml

# Now you can use normal commands
docker-compose up -d
```

---

## Step 5: Verify Connection

```powershell
# Check backend logs to see if it connects to database
docker-compose logs -f backend
```

You should see: `✓ Database is ready`

---

## Step 6: Access Application

- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

---

## Troubleshooting

### Error: "Connection refused"

**Solution:** Make sure your PostgreSQL service is running:
```powershell
# Check if PostgreSQL is running
Get-Service postgresql*

# If not running, start it
net start postgresql-x64-14
```

### Error: "Authentication failed"

**Solution:** Check your password in .env matches your PostgreSQL password

### Error: "Database does not exist"

**Solution:** Create the database in pgAdmin:
```sql
CREATE DATABASE agent_network;
```

### Error: "Extension vector does not exist"

**Solution:** The app will still work, just won't have semantic search. Continue anyway.

---

## Advantages of This Approach

✅ Uses your existing PostgreSQL
✅ No port conflicts
✅ Can view data directly in pgAdmin
✅ Fewer Docker containers to manage
✅ Easier to debug database issues

---

## To Switch Back to Docker PostgreSQL Later

Just rename the files back:
```powershell
mv docker-compose.yml docker-compose-local-db.yml
mv docker-compose-with-db.yml docker-compose.yml
```
