#!/usr/bin/env bash
# start.sh — Launch Hospital Capacity Forecasting System (Review 1)

echo "=========================================================="
echo " Starting Hospital Capacity Forecasting System (Review 1)"
echo "=========================================================="

# 1. Seed database if not present
if [ ! -f "data/hospital.db" ]; then
    echo "[*] Initializing synthetic hospital database..."
    python3 scripts/generate_hospital_data.py
fi

# 2. Start FastAPI Backend in background
echo "[*] Launching FastAPI Backend on http://localhost:8000 ..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 3. Start Vite Frontend
echo "[*] Launching Vite Frontend on http://localhost:5173 ..."
cd frontend && npm run dev -- --host &
FRONTEND_PID=$!

echo ""
echo "=========================================================="
echo " System Live!"
echo " Web UI:  http://localhost:5173"
echo " API Docs: http://localhost:8000/docs"
echo " Demo Accounts:"
echo "   Admin: admin@hospital.com / admin123"
echo "   Staff: staff@hospital.com / staff123"
echo " Press Ctrl+C to terminate both servers."
echo "=========================================================="

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
