# Dark Pattern Detector

An AI-powered web application that analyzes websites and identifies potential dark patterns that may influence or mislead users.

## Features

- Analyze websites using a URL or webpage content
- Detect potential dark patterns using Google Gemini AI
- Show pattern type, severity, confidence and evidence
- Provide user impact and recommendations
- View analytics of detected patterns
- Simple interactive dashboard using Streamlit

## Tech Stack

- **Frontend:** Streamlit
- **Backend:** FastAPI
- **AI:** Google Gemini API
- **Web Scraping:** HTTPX, BeautifulSoup
- **Database:** SQLite
- **Analytics:** PySpark
- **Testing:** pytest
- **Version Control:** Git, GitHub

## How It Works

```text
Website URL
    ↓
Web Scraping
    ↓
Content Analysis
    ↓
Gemini AI
    ↓
Dark Pattern Detection
    ↓
Results & Analytics
```

## Run Locally

```bash
git clone https://github.com/chetanapatil8822-afk/dark-pattern-detector.git
cd dark-pattern-detector
pip install -r requirements.txt
```

Create a `.env` file and add your Gemini API key:

```text
GEMINI_API_KEY=your_api_key
```

Start the backend:

```bash
uvicorn backend.main:app --reload --port 8000
```

Start the frontend in another terminal:

```bash
streamlit run frontend/app.py
```

## Project

This project was developed as an AI and Big Data Analytics application for detecting and analyzing dark patterns in websites.