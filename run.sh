#!/bin/bash
# ─── Stock Analyzer Pro — Run Script (Mac / Linux) ───────────────────────────

# Activate virtual environment if exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check .env
if [ ! -f ".env" ]; then
    echo "⚠️  קובץ .env לא נמצא. מעתיק מ-.env.example..."
    cp .env.example .env
    echo "📝 ערוך את .env והוסף את מפתח ה-ANTHROPIC_API_KEY שלך."
    echo ""
fi

echo "🚀 מפעיל Stock Analyzer Pro..."
echo "📍 פתח בדפדפן: http://localhost:8501"
echo "   לעצירה: Ctrl+C"
echo ""

streamlit run app.py \
    --server.port 8501 \
    --server.headless false \
    --browser.gatherUsageStats false \
    --theme.base dark \
    --theme.primaryColor "#00d4a0"
