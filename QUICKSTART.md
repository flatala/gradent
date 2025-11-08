# Quick Start Commands

## Install Everything

```bash
# Install backend dependencies
poetry install

# Install frontend dependencies
cd frontend && npm install && cd ..
```

## Run Application

### Option 1: Use start script (easiest)
```bash
./start.sh
```

### Option 2: Manual (3 terminals)

**Terminal 1 - Next.js API:**
```bash
cd QuestGen-AI-Agent/code
npm run dev
```

**Terminal 2 - Backend:**
```bash
python -m app.main
```

**Terminal 3 - Frontend:**
```bash
cd frontend
npm run dev
```

## Access

- **Frontend (UI):** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Next.js API:** http://localhost:3000

## First Time Setup

1. Copy `.env.example` to `.env`
2. Add your OpenRouter API key
3. Install dependencies (see above)
4. Run services (see above)
5. Open http://localhost:5173

Done! 🎉
