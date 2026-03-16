@echo off
REM ─── Stock Analyzer Pro — Setup Script (Windows) ─────────────────────────────
echo 📈 Stock Analyzer Pro — Setup
echo ================================

REM Check Python
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ❌ Python לא נמצא. אנא התקן Python 3.10+ מ: https://www.python.org
    pause
    exit /b 1
)
echo ✅ Python נמצא

REM Create virtual environment
IF NOT EXIST ".venv" (
    echo 📦 יוצר סביבת Python...
    python -m venv .venv
)

REM Activate
call .venv\Scripts\activate.bat
echo ✅ סביבת Python מופעלת

REM Upgrade pip
python -m pip install --upgrade pip --quiet

REM Install dependencies
echo 📥 מתקין תלויות (עשוי לקחת מספר דקות)...
pip install -r requirements.txt --quiet

echo.
echo ✅ ההתקנה הושלמה!
echo.

REM Setup .env
IF NOT EXIST ".env" (
    copy .env.example .env
    echo 📝 נוצר קובץ .env
    echo.
    echo ⚠️  חשוב: ערוך את קובץ .env והוסף את מפתח ה-API שלך:
    echo    ANTHROPIC_API_KEY=your_key_here
    echo.
    echo    קבל מפתח API בחינם ב: https://console.anthropic.com
    echo.
) ELSE (
    echo ℹ️  קובץ .env קיים כבר
)

echo 🚀 להרצת האפליקציה:
echo    run.bat
echo.
pause
