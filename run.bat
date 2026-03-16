@echo off
REM ─── Stock Analyzer Pro — Run Script (Windows) ───────────────────────────────

REM Activate virtual environment
IF EXIST ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Check .env
IF NOT EXIST ".env" (
    echo ⚠️  קובץ .env לא נמצא. מעתיק מ-.env.example...
    copy .env.example .env
    echo 📝 ערוך את .env והוסף את מפתח ה-ANTHROPIC_API_KEY שלך.
    echo.
)

echo 🚀 מפעיל Stock Analyzer Pro...
echo 📍 פתח בדפדפן: http://localhost:8501
echo    לעצירה: Ctrl+C
echo.

streamlit run app.py --server.port 8501 --browser.gatherUsageStats false --theme.base dark --theme.primaryColor "#00d4a0"
