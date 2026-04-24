# Startup Job Intelligence

A full-stack platform that aggregates startup job listings from multiple sources (YC, VC portfolios, job boards) and provides AI-powered features like resume matching and cold email generation.


## Tech Stack
| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + TypeScript, Vite, Framer Motion |
| **Backend** | Python, FastAPI, Uvicorn |
| **AI Services** | Google Gemini, Groq (LLaMA 3), APIMart (GPT-4o) |
| **Data** | In-memory store with JSON persistence |

## Architecture
```
backend/
├── main.py              # FastAPI entry point
├── routes.py            # REST API endpoints
├── models.py            # Pydantic data models
├── store.py             # In-memory job store with JSON persistence
├── coordinator.py       # Agent orchestrator
├── agents/              # Data collection agents (YC, HN, GitHub, etc.)
│   ├── diverse_seed.py  # Curated VC portfolio startup data
│   └── ...              # 16+ scraping/data agents
├── services/            # AI and utility services
│   ├── gemini_service.py    # JD summarization, field inference
│   ├── groq_service.py      # Cold DM/email generation
│   ├── resume_parser.py     # PDF resume parsing
│   ├── resume_matcher.py    # Job-resume matching
│   └── antiblock.py         # Rate-limited HTTP client
└── data/                # Runtime data (gitignored)

frontend/
├── src/
│   ├── App.tsx          # Root component
│   ├── api.ts           # API client
│   ├── types.ts         # TypeScript interfaces
│   ├── components/      # React components
│   └── hooks/           # Custom hooks
└── public/
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
cp .env.example .env         # Add your API keys
python main.py
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173` with the API at `http://localhost:8000`.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/jobs` | Paginated job listings with filters |
| GET | `/api/companies/{slug}` | Company details with jobs |
| GET | `/api/founders/search` | Search founders by name |
| POST | `/api/cold-message` | Generate cold DM for a job |
| POST | `/api/resume/upload` | Upload resume for job matching |
| POST | `/api/resume/cold-email` | Generate personalized cold email |
| GET | `/api/health` | Health check |

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for required configuration.

## License

MIT
