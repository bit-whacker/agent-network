# Simple Agent-Based Networking Application

A minimal implementation of an agent-based professional networking system where AI agents help users find matching professionals.

## Features

1. **Profile Builder** - Agent asks questions to build user profile
2. **Smart Search** - Natural language search to find matching professionals
3. **Agent Communication** - Agents evaluate matches and return ranked results

## Tech Stack

- **Backend**: Python + FastAPI
- **Frontend**: HTML/CSS/JavaScript (Vanilla)
- **Database**: PostgreSQL with pgvector
- **AI**: Claude API via LangChain
- **Agent Framework**: LangChain

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Claude API key from Anthropic

### Installation

1. Clone and setup:
```bash
cd agent-network
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

2. Start the application:
```bash
docker-compose up -d
```

3. Initialize database:
```bash
docker-compose exec backend python init_db.py
```

4. Access the application:
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs

### Without Docker

1. Install dependencies:
```bash
pip install -r requirements.txt
npm install -g http-server
```

2. Setup PostgreSQL with pgvector extension

3. Run backend:
```bash
cd backend
python main.py
```

4. Run frontend:
```bash
cd frontend
http-server -p 3000
```

## Project Structure

```
agent-network/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── agent.py             # LangChain agent logic
│   ├── database.py          # Database connections
│   ├── models.py            # Pydantic models
│   └── init_db.py           # Database initialization
├── frontend/
│   ├── index.html           # Main UI
│   ├── style.css            # Styling
│   └── app.js               # Frontend logic
├── sql/
│   └── schema.sql           # Database schema
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## Usage

### 1. Build Your Profile

- Click "Build Profile"
- Answer agent's questions about your skills, experience, availability
- Agent creates structured profile

### 2. Search for Professionals

- Enter search query: "Looking for a React developer in SF"
- Agent processes request and searches connected network
- View ranked results with match scores

## API Endpoints

- `POST /api/profile/build` - Start profile building conversation
- `POST /api/profile/save` - Save completed profile
- `POST /api/search` - Search for matching professionals
- `GET /api/connections/{user_id}` - Get user connections
- `POST /api/connections` - Create connection

## Environment Variables

```
ANTHROPIC_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:password@localhost:5432/agent_network
```

## Development

Run tests:
```bash
pytest backend/tests/
```

Reset database:
```bash
docker-compose exec backend python init_db.py --reset
```

## License

MIT
