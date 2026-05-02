# 🚀 AI Marketing Strategy Generator

An agentic AI system that generates complete, structured marketing strategies for any product or business idea.

**Built with:** Groq + LLaMA 3.1 · LangChain · Streamlit · SQLite

## Features
- 9-section marketing strategy (STP, 4Ps, Budget, Execution Plan, and more)
- Parallel AI agents for fast generation
- Competitor radar chart
- Tone selector (Professional, Casual, Aggressive Growth, Minimal Budget)
- Multi-language output
- Export as PDF, Word, or Text
- User login & saved strategies
- Real market data via SerpAPI (optional)

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Add your API keys
Create `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "your_groq_key_here"
SERPAPI_KEY  = ""   # optional
```
Get a free Groq key at [console.groq.com](https://console.groq.com)

### 3. Run
```bash
streamlit run app.py
```

## Deploy to Streamlit Cloud
1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) → New app
3. Select repo, set main file to `app.py`
4. Add secrets in app settings → Secrets

> **Note:** The SQLite user database resets on Streamlit Cloud redeploys.
> For persistent users in production, connect a hosted database (Supabase, PlanetScale, etc.)
