# Quick Start Guide

## 1. Get Your API Key
1. Go to https://console.anthropic.com/
2. Create an account or sign in
3. Navigate to API Keys
4. Create a new key and copy it

## 2. Setup

```bash
cd agent-network

# Copy environment template
cp .env.example .env

# Edit .env and add your key
nano .env  # or use your favorite editor
# Replace: your_anthropic_api_key_here
# With: sk-ant-api03-...your-actual-key...
```

## 3. Start the Application

### Option A: Using Docker (Recommended)
```bash
./start.sh
```

### Option B: Manual Start
```bash
docker-compose up -d
sleep 5
docker-compose exec backend python backend/init_db.py
```

## 4. Access the Application

- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

## 5. Using the Application

### First Time Setup
1. Enter your email and name
2. Click "Get Started"
3. Chat with the agent to build your profile
4. Answer questions about your skills, experience, etc.
5. Save your profile when complete

### Connecting with Others
1. Go to "Connections" tab
2. Select a user from the dropdown
3. Click "Connect"

### Searching
1. Go to "Search Network" tab
2. Type: "Looking for a React developer"
3. Click "Search"
4. View ranked matches

## 6. Stop the Application

```bash
docker-compose down
```

## Troubleshooting

### Database connection errors
```bash
docker-compose down
docker-compose up -d
sleep 10
docker-compose exec backend python backend/init_db.py
```

### Reset everything
```bash
docker-compose down -v
docker-compose up -d
sleep 10
docker-compose exec backend python backend/init_db.py --reset
```

### View logs
```bash
docker-compose logs -f backend
docker-compose logs -f db
```

## Sample Workflow

1. **User Alice** builds profile: "Senior UX Designer, 8 years experience, Figma expert"
2. **User Bob** builds profile: "Full-stack Developer, 5 years, React/Node.js"
3. **Alice connects with Bob**
4. **Bob searches**: "Looking for a designer with Figma experience"
5. **Agent finds Alice** with high match score (shares matched skills, explanation)

## Architecture

```
Frontend (Nginx)
    ↓
Backend (FastAPI + LangChain)
    ↓
PostgreSQL (with pgvector)
    ↓
Claude API (Anthropic)
```

The agents use LangChain to:
- Build profiles through conversation
- Parse natural language search queries
- Evaluate candidate matches
- Generate explanations
