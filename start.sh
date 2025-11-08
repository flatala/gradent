#!/bin/bash

# Quick start script for the exam generator application

echo "================================================"
echo "🚀 Starting Exam Generator Application"
echo "================================================"
echo ""

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Check if Next.js API is running
echo "1️⃣ Checking Next.js API (port 3000)..."
if ! lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "⚠️  Next.js API not running on port 3000"
    echo "   Start it with: cd QuestGen-AI-Agent/code && npm run dev"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
else
    echo "✅ Next.js API is running"
fi

echo ""
echo "2️⃣ Starting Backend Server (port 8000)..."
echo "   Press Ctrl+C to stop all services"
echo ""

# Start backend in background
python -m app.main &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

echo ""
echo "3️⃣ Starting Frontend Server (port 5173)..."
echo ""

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

# Wait for frontend to start
sleep 3

echo ""
echo "================================================"
echo "✅ All services started!"
echo "================================================"
echo ""
echo "📊 Service URLs:"
echo "   Frontend: http://localhost:5173"
echo "   Backend:  http://localhost:8000"
echo "   API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for interrupt
trap "echo ''; echo 'Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM

# Keep script running
wait
