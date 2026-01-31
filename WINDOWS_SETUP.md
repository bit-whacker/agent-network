# Windows Setup Guide

## Complete Step-by-Step Instructions for Windows Users

### Prerequisites Installation

#### 1. Install Docker Desktop for Windows
1. Download from: https://www.docker.com/products/docker-desktop/
2. Run the installer
3. **Important**: Enable "WSL 2" when prompted
4. Restart your computer
5. Start Docker Desktop
6. Wait for it to show "Docker Desktop is running"

#### 2. Get Anthropic API Key
1. Go to: https://console.anthropic.com/
2. Sign up or login
3. Click "API Keys" in the left sidebar
4. Click "Create Key"
5. Copy your key (starts with `sk-ant-api03-...`)

---

## Quick Start (Recommended Method)

### Step 1: Extract the Project
```powershell
# In PowerShell or File Explorer
# Extract agent-network.tar.gz to a folder like C:\Projects\agent-network
```

### Step 2: Configure Environment
1. Open the `agent-network` folder
2. Copy `env.example` and rename it to `.env`
3. Open `.env` in Notepad
4. Replace `your_anthropic_api_key_here` with your actual key
5. Save and close

**Your .env should look like:**
```env
ANTHROPIC_API_KEY=sk-ant-api03-XXXXXXXXXXXXXXXXXXXX

# Leave these unchanged:
DATABASE_URL=postgresql://postgres:postgres@db:5432/agent_network
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=agent_network
```

### Step 3: Start the Application

**Option A: Using PowerShell (Recommended)**
```powershell
cd C:\Projects\agent-network
.\start.ps1
```

**Option B: Using Manual Commands**
```powershell
cd C:\Projects\agent-network
docker-compose up -d
timeout /t 10
docker-compose exec backend python backend/init_db.py
```

**Option C: Using Git Bash**
```bash
cd /c/Projects/agent-network
./start.sh
```

### Step 4: Access the Application
- Open browser: http://localhost:3000
- API Documentation: http://localhost:8000/docs

---

## Troubleshooting

### Error: "Docker is not running"
**Solution:**
1. Start Docker Desktop from Windows Start Menu
2. Wait for "Docker Desktop is running" status
3. Try again

### Error: "Port already in use"
**Solution:**
```powershell
# Check what's using port 8000
netstat -ano | findstr :8000

# Stop the application and restart
docker-compose down
docker-compose up -d
```

### Error: "Cannot connect to database"
**Solution:**
```powershell
# Restart everything
docker-compose down
docker-compose up -d
timeout /t 15
docker-compose exec backend python backend/init_db.py
```

### Error: "PowerShell execution policy"
**Solution:**
```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try ./start.ps1 again
```

### View Logs
```powershell
# See all logs
docker-compose logs -f

# See only backend logs
docker-compose logs -f backend

# See only database logs
docker-compose logs -f db
```

---

## Using Your Existing PostgreSQL (Optional)

If you already created a database in pgAdmin and want to use it:

1. **Install pgvector** in your PostgreSQL:
   - Download from: https://github.com/pgvector/pgvector/releases
   - Or use pgAdmin to run: `CREATE EXTENSION vector;`

2. **Update .env:**
   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@host.docker.internal:5432/agent_network
   ```

3. **Modify docker-compose.yml:**
   - Remove the `db:` service section
   - Remove `depends_on: db` from backend

4. **Run schema in pgAdmin:**
   - Open `sql/schema.sql`
   - Execute in your `agent_network` database

See `LOCAL_POSTGRES_GUIDE.md` for detailed instructions.

---

## Stopping the Application

```powershell
cd C:\Projects\agent-network
docker-compose down
```

## Completely Reset Everything

```powershell
# Warning: This deletes all data!
docker-compose down -v
docker-compose up -d
timeout /t 10
docker-compose exec backend python backend/init_db.py --reset
```

---

## File Structure

```
agent-network/
├── backend/           # Python FastAPI application
├── frontend/          # HTML/CSS/JS interface
├── sql/              # Database schema
├── .env.example      # Template (copy to .env)
├── .env              # Your config (create this)
├── docker-compose.yml # Docker configuration
├── start.sh          # Linux/Mac startup
├── start.ps1         # Windows PowerShell startup
└── README.md         # Documentation
```

---

## Quick Commands Reference

```powershell
# Start application
docker-compose up -d

# Stop application
docker-compose down

# View logs
docker-compose logs -f

# Restart backend only
docker-compose restart backend

# Access database shell
docker-compose exec db psql -U postgres -d agent_network

# Reset database
docker-compose exec backend python backend/init_db.py --reset

# Check running containers
docker ps

# Remove everything including data
docker-compose down -v
```

---

## Next Steps

1. ✅ Application is running at http://localhost:3000
2. Create your profile by chatting with the AI agent
3. Connect with other users (or create test users)
4. Search for professionals using natural language
5. View your connections and network

---

## Getting Help

If you encounter issues:

1. Check Docker Desktop is running
2. View logs: `docker-compose logs -f backend`
3. Ensure .env has correct ANTHROPIC_API_KEY
4. Try reset: `docker-compose down -v` then restart
5. Check ports 3000 and 8000 are not in use

---

## Common Windows-Specific Issues

### WSL 2 Not Installed
- Docker Desktop requires WSL 2
- Install from: https://aka.ms/wsl2kernel
- Restart computer

### Antivirus Blocking Docker
- Add Docker Desktop to antivirus exceptions
- Add project folder to exceptions

### File Sharing Issues
- In Docker Desktop settings: Resources → File Sharing
- Add your project folder (e.g., C:\Projects)

### Slow Performance
- In Docker Desktop: Settings → Resources
- Increase CPUs to 4
- Increase Memory to 4GB
