# Frontend & Backend Setup Guide

## 🎯 Understanding Frontend vs Backend

### **Backend (Python + FastAPI)** - The Brain 🧠
Located in: `/app/main.py`

**What it does:**
- Receives requests from the web interface
- Processes PDF files
- Runs AI workflows (LangGraph)
- Calls OpenRouter API for question generation
- Returns generated exams

**Technology:** FastAPI (Python web framework)

### **Frontend (React + Vite)** - The Face 👁️
Located in: `/frontend/`

**What it does:**
- Beautiful web interface users interact with
- Upload PDFs via drag-and-drop
- Fill out exam requirements form
- Display generated exams with nice formatting
- Download/copy results

**Technology:** React (JavaScript UI library) + Vite (build tool)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- Poetry (Python package manager)

### 1️⃣ Install Backend Dependencies

```bash
# Install Python packages
poetry install

# Or if not using poetry:
pip install fastapi uvicorn python-multipart httpx langchain langgraph
```

### 2️⃣ Install Frontend Dependencies

```bash
cd frontend
npm install
cd ..
```

### 3️⃣ Configure Environment

Make sure your `.env` file has:
```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### 4️⃣ Start the Next.js API (Required!)

The backend needs this to process questions:

```bash
cd QuestGen-AI-Agent/code
npm install  # First time only
npm run dev  # Starts on http://localhost:3000
```

Keep this running in a separate terminal.

### 5️⃣ Start Backend Server

In a new terminal:

```bash
# From project root
python -m app.main

# Or:
cd app
python main.py
```

Backend will run on: **http://localhost:8000**
API docs available at: **http://localhost:8000/docs**

### 6️⃣ Start Frontend

In another new terminal:

```bash
cd frontend
npm run dev
```

Frontend will run on: **http://localhost:5173**

---

## 📖 How to Use

1. **Open browser** → http://localhost:5173
2. **Upload PDFs** → Drag & drop or click to select
3. **Fill form:**
   - Exam title: "Midterm Exam - Machine Learning"
   - Requirements: "10 multiple choice questions, mixed difficulty"
4. **Click "Generate Exam"** → Wait ~30-60 seconds
5. **View results** → Download or copy the generated exam

---

## 🏗️ Architecture Overview

```
┌─────────────────┐
│   Web Browser   │  ← User sees pretty interface
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  React Frontend │  ← Port 5173
│   (Vite dev)    │
└────────┬────────┘
         │ HTTP API calls
         ▼
┌─────────────────┐
│ FastAPI Backend │  ← Port 8000
│  (Python/app)   │
└────────┬────────┘
         │ Invokes
         ▼
┌─────────────────┐
│ LangGraph Flow  │  ← Your exam_api workflow
│  (Python/workflows)│
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  Next.js API    │  ← Port 3000
│ (QuestGen-AI)   │
└────────┬────────┘
         │ API call
         ▼
┌─────────────────┐
│  OpenRouter     │  ← Cloud AI service
│   (Gemini AI)   │
└─────────────────┘
```

---

## 🔧 Troubleshooting

### Backend won't start
```bash
# Install missing dependencies
poetry install

# Or check what's missing:
python -m app.main
```

### Frontend won't start
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### "Connection refused" errors
Make sure all 3 services are running:
1. ✅ Next.js API on port 3000
2. ✅ Backend API on port 8000  
3. ✅ Frontend on port 5173

### CORS errors
The backend is configured to allow requests from the frontend.
If you change ports, update `app/main.py` CORS settings.

---

## 📂 File Structure

```
gradent/
├── app/                          # BACKEND
│   ├── __init__.py
│   └── main.py                   # FastAPI server
│
├── frontend/                     # FRONTEND
│   ├── src/
│   │   ├── App.jsx              # Main app component
│   │   ├── main.jsx             # Entry point
│   │   ├── index.css            # Global styles
│   │   └── components/
│   │       ├── ExamForm.jsx     # Upload & form UI
│   │       └── Results.jsx      # Display results
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── workflows/                    # AI WORKFLOWS
│   └── exam_api/                # Your exam generation
│       ├── tools.py
│       ├── nodes.py
│       ├── graph.py
│       └── state.py
│
└── QuestGen-AI-Agent/           # NEXT.JS API
    └── code/
        └── app/api/generate-questions/
```

---

## 🎨 Customization

### Change Frontend Colors
Edit `frontend/src/index.css`:
```css
/* Line 11 - gradient background */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
```

### Change Backend Port
Edit `app/main.py` line 220:
```python
uvicorn.run("app.main:app", port=8000)  # Change 8000
```

### Change AI Model
Edit form default in `frontend/src/components/ExamForm.jsx` line 7:
```javascript
const [modelName, setModelName] = useState('qwen/qwen3-30b-a3b:free')
```

---

## 🧪 Testing

### Test Backend Only
```bash
# Start backend
python -m app.main

# In another terminal, test with curl:
curl http://localhost:8000/api/health
```

### Test Full Stack
1. Start all 3 services (Next.js, Backend, Frontend)
2. Open http://localhost:5173
3. Upload a test PDF
4. Fill form and generate

---

## 🚢 Production Deployment

### Backend
```bash
# Install gunicorn for production
pip install gunicorn

# Run with gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Frontend
```bash
cd frontend
npm run build  # Creates dist/ folder

# Serve with any static server:
npx serve -s dist -l 3000
```

---

## 💡 Tips

1. **Keep terminals organized:** Use 3 terminal tabs/panes
2. **Check logs:** Backend prints useful debug info
3. **Use API docs:** http://localhost:8000/docs for backend
4. **Save API key:** Put in `.env` instead of typing each time
5. **Clear uploads:** Backend auto-deletes PDFs after processing

---

Need help? Check:
- Backend logs in terminal running `python -m app.main`
- Frontend console in browser DevTools (F12)
- Next.js logs in terminal running `npm run dev`
