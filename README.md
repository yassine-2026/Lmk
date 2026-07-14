# AI Video Script Generator

A complete AI Video Script Generator website using Groq API (free tier). The site generates professional video scripts for Reels/TikTok/Shorts.

## Features
- Single file Flask app (`app.py`)
- LLaMA 3.3 70B model via Groq
- Arabic RTL support
- Mobile-responsive Tailwind CSS frontend

## Local Setup
1. `pip install -r requirements.txt`
2. Create `.env` file with your API key: `GROQ_API_KEY=gsk_your_key_here`
3. `python app.py`
4. Open http://localhost:5000

## Render.com Deployment
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`
- **Environment Variable**: `GROQ_API_KEY = your_groq_key`
