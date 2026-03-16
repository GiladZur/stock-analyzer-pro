# 📈 Stock Analyzer Pro — ישראל & ארה"ב

אפליקציית ניתוח מניות מקיפה עם בינה מלאכותית — ניתוח טכני, פונדמנטלי, חדשות והמלצות השקעה.

![Python](https://img.shields.io/badge/Python-3.10+-blue) ![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-red) ![Claude](https://img.shields.io/badge/Claude-AI-purple)

---

## 🌟 תכונות עיקריות

### 📊 ניתוח טכני מלא
- **12+ אינדיקטורים**: RSI, MACD, Bollinger Bands, Stochastic, Williams %R, CCI, ADX, OBV, EMA, SMA
- **סיגנלים**: קנייה / מכירה / נייטרלי לכל אינדיקטור
- **Golden/Death Cross** — זיהוי אוטומטי
- **מחיר כניסה, יעדים (T1, T2), Stop Loss** — חישוב מבוסס ATR
- **גרפים אינטראקטיביים** — Candlestick, Volume, RSI, MACD, Stochastic, Williams %R, CCI

### 📑 ניתוח פונדמנטלי
- **מדדי הערכת שווי**: P/E, P/B, EV/EBITDA, PEG, P/S
- **רווחיות**: EPS, מרווחי רווח, ROE, ROA
- **צמיחה**: גידול הכנסות ורווחים
- **בריאות פיננסית**: חוב/הון, נזילות, תזרים מזומנים חופשי
- **גרף מגמת הכנסות ורווח** שנתי
- **תאריכי דוחות כספיים**

### 📰 חדשות וסנטימנט
- חדשות מ**90 הימים האחרונים**
- **סיווג אוטומטי**: חיובי 🟢 / שלילי 🔴 / נייטרלי ⚪
- ניתוח סנטימנט מעמיק על ידי Claude AI

### 🤖 ניתוח AI — 4 סוכנים מתמחים
1. **סוכן טכני** — מפרש אינדיקטורים ומגמות
2. **סוכן פונדמנטלי** — מעריך שווי הוגן ובריאות פיננסית
3. **סוכן חדשות** — מנתח סנטימנט ואירועים
4. **סוכן סיכום** — מייצר המלצת השקעה מנומקת

---

## 🚀 התקנה מהירה

### דרישות
- Python 3.10+
- חיבור לאינטרנט
- מפתח API של Anthropic (לניתוח AI)

### Mac / Linux

```bash
# 1. שכפל את הפרויקט
cd stock-analyzer

# 2. הרץ את סקריפט ההתקנה
chmod +x setup.sh run.sh
./setup.sh

# 3. ערוך את .env והוסף API key
nano .env  # או פתח בכל עורך טקסט

# 4. הפעל
./run.sh
```

### Windows

```bat
REM 1. פתח CMD או PowerShell בתיקיית הפרויקט

REM 2. הרץ את ההתקנה
setup.bat

REM 3. ערוך את .env (Notepad)
notepad .env

REM 4. הפעל
run.bat
```

### התקנה ידנית

```bash
# צור סביבת Python
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
# .venv\Scripts\activate.bat     # Windows

# התקן תלויות
pip install -r requirements.txt

# הגדר API key
cp .env.example .env
# ערוך .env והוסף: ANTHROPIC_API_KEY=sk-...

# הפעל
streamlit run app.py
```

---

## ⚙️ הגדרות (.env)

```env
# [חובה] מפתח API של Claude
ANTHROPIC_API_KEY=sk-ant-...

# [אופציונלי] מודל Claude (ברירת מחדל: claude-opus-4-6)
CLAUDE_MODEL=claude-opus-4-6

# [אופציונלי] NewsAPI לחדשות מורחבות
NEWS_API_KEY=...
```

קבל מפתח API בחינם: [https://console.anthropic.com](https://console.anthropic.com)

---

## 📖 שימוש

1. פתח את האפליקציה בדפדפן (http://localhost:8501)
2. הזן **סימבול מניה** בסרגל הצד:
   - ארה"ב: `AAPL`, `TSLA`, `NVDA`, `MSFT`
   - ישראל (TASE): `ESLT.TA`, `ICL.TA`, `TEVA.TA`
3. בחר **שוק** ו**תקופה**
4. הפעל **Claude AI** לניתוח מלא
5. לחץ **🚀 נתח מניה**

### מניות ישראליות נפוצות

| חברה | סימבול |
|------|--------|
| אלביט מערכות | `ESLT.TA` |
| כימיקלים לישראל | `ICL.TA` |
| טבע | `TEVA.TA` |
| חברת השמירה | `SHVA.TA` |
| Nice Systems | `NICE` (Nasdaq) |
| Check Point | `CHKP` (Nasdaq) |
| Monday.com | `MNDY` (Nasdaq) |
| Wix | `WIX` (Nasdaq) |

---

## 🏗️ מבנה הפרויקט

```
stock-analyzer/
├── app.py                  # אפליקציית Streamlit הראשית
├── config.py               # הגדרות ופרמטרים
├── requirements.txt        # תלויות Python
├── .env.example            # תבנית הגדרות
├── setup.sh / setup.bat    # סקריפטי התקנה
├── run.sh / run.bat        # סקריפטי הרצה
├── agents/
│   └── claude_agent.py     # 4 סוכני Claude AI
├── data/
│   ├── stock_fetcher.py    # שליפת נתוני מניות (yfinance)
│   └── news_fetcher.py     # שליפת חדשות
├── analysis/
│   ├── technical.py        # חישוב אינדיקטורים טכניים
│   └── fundamental.py      # ניתוח מדדים פונדמנטליים
└── charts/
    └── plotly_charts.py    # גרפים אינטראקטיביים
```

---

## 🔧 טכנולוגיות

| רכיב | טכנולוגיה |
|------|-----------|
| ממשק משתמש | Streamlit |
| נתוני מחיר | yfinance (Yahoo Finance) |
| אינדיקטורים | pandas-ta |
| גרפים | Plotly |
| AI | Claude API (Anthropic) |
| חדשות | yfinance + NewsAPI |

---

## ⚠️ כתב ויתור

המידע באפליקציה זו הוא **לצרכי מחקר ומידע בלבד** ואינו מהווה ייעוץ השקעות, שיווק השקעות, ייעוץ מס או כל ייעוץ פיננסי אחר. כל החלטת השקעה היא באחריות המשקיע בלבד. ביצועי עבר אינם ערובה לביצועי עתיד.

---

*Stock Analyzer Pro | Powered by Claude AI | נתונים: Yahoo Finance*
