```
┌──────────────────────────────────────────────────────────────────────┐
│                        🌐 USER'S WEB BROWSER                         │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                     FRONTEND (React)                        │    │
│  │              http://localhost:5173                          │    │
│  │                                                             │    │
│  │  📁 Upload PDFs                                             │    │
│  │  ✏️  Fill Exam Form                                         │    │
│  │  ⏳ Loading Spinner                                         │    │
│  │  📄 Display Results                                         │    │
│  │  💾 Download/Copy Buttons                                   │    │
│  └─────────────────────┬───────────────────────────────────────┘    │
└────────────────────────┼──────────────────────────────────────────────┘
                         │
                         │ HTTP POST /api/generate-exam
                         │ (sends: PDFs, header, description)
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                      💻 BACKEND SERVER (FastAPI)                     │
│                      http://localhost:8000                           │
│                                                                      │
│  📂 app/main.py                                                      │
│                                                                      │
│  Endpoints:                                                          │
│  • POST /api/generate-exam  ← Main endpoint                         │
│  • GET  /api/health         ← Health check                          │
│  • GET  /docs               ← API documentation                     │
│                                                                      │
│  What it does:                                                       │
│  1. Receives uploaded PDFs                                           │
│  2. Saves them temporarily                                           │
│  3. Calls your LangGraph workflow ───┐                               │
│  4. Returns generated questions      │                               │
│  5. Cleans up temp files             │                               │
└──────────────────────────────────────┼───────────────────────────────┘
                                       │
                                       │ Invokes workflow
                                       ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    🤖 LANGGRAPH WORKFLOW                             │
│                    workflows/exam_api/                               │
│                                                                      │
│  graph.py    → Defines workflow steps                                │
│  nodes.py    → upload_pdfs, generate_questions                       │
│  tools.py    → HTTP calls to Next.js API                            │
│  state.py    → Stores PDF paths, questions, etc.                    │
│                                                                      │
│  Flow:                                                               │
│  1. upload_pdfs node        → POST PDFs to Next.js                  │
│  2. generate_questions node → GET streaming questions               │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               │ HTTP API calls
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                   🎯 NEXT.JS API SERVER                              │
│                   http://localhost:3000                              │
│                                                                      │
│  QuestGen-AI-Agent/code/app/api/generate-questions/route.ts         │
│                                                                      │
│  Multi-Agent Workflow:                                               │
│  1. Extractor     → Analyzes requirements                            │
│  2. QuestionCreator → Generates questions                            │
│  3. Formatter     → Formats as exam                                  │
│                                                                      │
│  Uses:                                                               │
│  • Convex (cloud storage for PDFs)                                   │
│  • Server-Sent Events (SSE) for streaming                            │
│  • LangChain agents                                                  │
│                                                                      │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               │ OpenRouter API call
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     ☁️ OPENROUTER (Cloud AI)                         │
│                                                                      │
│  Model: google/gemini-flash-1.5-8b                                   │
│                                                                      │
│  • Analyzes PDF content                                              │
│  • Generates exam questions                                          │
│  • Formats markdown output                                           │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════

📊 DATA FLOW EXAMPLE:

1. USER uploads "lecture.pdf" via Frontend
   ↓
2. FRONTEND sends to Backend: FormData with PDF + "10 MCQ questions"
   ↓
3. BACKEND saves PDF to /uploads/lecture.pdf
   ↓
4. BACKEND invokes exam_api_graph workflow
   ↓
5. WORKFLOW uploads PDF to Next.js API
   ↓
6. NEXT.JS saves to Convex cloud storage
   ↓
7. NEXT.JS runs multi-agent workflow:
   - Extractor analyzes: "Create 10 MCQ"
   - QuestionCreator generates questions using AI
   - Formatter creates markdown exam
   ↓
8. NEXT.JS streams back: "### Question 1..."
   ↓
9. WORKFLOW collects all chunks
   ↓
10. BACKEND returns complete exam to Frontend
    ↓
11. FRONTEND displays with nice formatting + math support
    ↓
12. USER downloads or copies the exam

═══════════════════════════════════════════════════════════════════════

🔑 KEY CONCEPTS:

FRONTEND (React)           BACKEND (FastAPI)          WORKFLOW (LangGraph)
----------------           -----------------          --------------------
• User Interface           • REST API                 • Business Logic
• HTML/CSS/JS              • Python                   • PDF Processing
• Runs in browser          • Runs on server           • AI Integration
• Port 5173                • Port 8000                • Stateful flow

SEPARATION OF CONCERNS:
Frontend  → "What user sees"       (Presentation)
Backend   → "How to serve data"    (API/Server)
Workflow  → "What to do with data" (Business Logic)
Next.js   → "AI processing"        (External Service)

═══════════════════════════════════════════════════════════════════════
```
