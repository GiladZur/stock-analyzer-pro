#!/bin/bash
# ─── Stock Analyzer Pro — Setup Script (Mac / Linux) ─────────────────────────
set -e

echo "📈 Stock Analyzer Pro — Setup"
echo "================================"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python 3 לא נמצא. אנא התקן Python 3.10+ מ: https://www.python.org"
    exit 1
fi

PYTHON_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "✅ Python $PYTHON_VER נמצא"

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo "📦 יוצר סביבת Python..."
    python3 -m venv .venv
fi

# Activate
source .venv/bin/activate
echo "✅ סביבת Python מופעלת"

# Upgrade pip
pip install --upgrade pip --quiet

# Install dependencies
echo "📥 מתקין תלויות (עשוי לקחת מספר דקות)..."
pip install -r requirements.txt --quiet

echo ""
echo "✅ ההתקנה הושלמה!"
echo ""

# Setup .env
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "📝 נוצר קובץ .env"
    echo ""
    echo "⚠️  חשוב: ערוך את קובץ .env והוסף את מפתח ה-API שלך:"
    echo "   ANTHROPIC_API_KEY=your_key_here"
    echo ""
    echo "   קבל מפתח API בחינם ב: https://console.anthropic.com"
    echo ""
else
    echo "ℹ️  קובץ .env קיים כבר"
fi

echo "🚀 להרצת האפליקציה:"
echo "   source .venv/bin/activate"
echo "   streamlit run app.py"
echo ""
echo "   או פשוט הפעל: ./run.sh"
