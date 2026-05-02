import os
import time
import json
import re
import requests
import streamlit as st
from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage


def _secret(key: str) -> str:
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, "")


GROQ_API_KEY = _secret("GROQ_API_KEY")

_MODEL_CHAIN = [
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]

SYSTEM_PROMPT = """You are a world-class marketing strategist AI with 20+ years of experience
helping startups, students, and small businesses grow from zero to profitable.
Your strategies are practical, low-budget, and immediately actionable.
Grounded in real frameworks (STP, 4Ps, AIDA). Always be specific — give real channel names,
real cost estimates, real timelines, and tactics a small team can execute today."""

TONE_PROMPTS = {
    "Professional":      "Use formal, data-driven, professional language.",
    "Casual & Friendly": "Use conversational, friendly, easy-to-understand language.",
    "Aggressive Growth": "Focus on rapid scaling, bold moves, and high-growth tactics.",
    "Minimal Budget":    "Focus entirely on zero or near-zero cost tactics and organic growth.",
}

LANGUAGES = {
    "English": "", "Hindi": "Respond in Hindi.", "Spanish": "Respond in Spanish.",
    "French": "Respond in French.", "Arabic": "Respond in Arabic.",
    "German": "Respond in German.", "Urdu": "Respond in Urdu.",
}

EXAMPLE_PROMPTS = [
    "Online tutoring app for school students in rural areas via WhatsApp",
    "Handmade eco-friendly jewelry sold on Instagram and Etsy",
    "AI-powered resume builder for fresh graduates",
    "Local home-cooked food delivery for working professionals",
    "Fitness coaching app for women over 40",
]

SECTIONS = {
    "Market Analysis": (
        "Analyze the market for this product. Cover: (1) estimated market size and growth trend, "
        "(2) top 2-3 direct competitors and their weaknesses, (3) key market gaps this product can fill."
    ),
    "STP Model": (
        "Apply the STP framework: Segmentation — identify 2-3 customer segments with demographics. "
        "Targeting — recommend the primary segment and explain why. "
        "Positioning — craft a clear positioning statement that differentiates this product."
    ),
    "Value Proposition": (
        "Write a compelling value proposition: (1) the core problem being solved, "
        "(2) the unique solution offered, (3) top 3 benefits customers will experience, "
        "(4) a one-line tagline."
    ),
    "4Ps Strategy": (
        "Define the 4Ps: Product — features and branding approach. "
        "Price — recommended strategy with a suggested price range. "
        "Place — top 2-3 distribution channels. Promotion — top 3 tactics with estimated reach."
    ),
    "Marketing Channels": (
        "Recommend the 4 best marketing channels. For each: name it, explain why it fits, "
        "describe the specific tactic, and estimate monthly cost (total budget $200-500/month)."
    ),
    "Content Strategy": (
        "Design a content strategy: (1) 3 content pillars, (2) formats with posting frequency, "
        "(3) platform-specific tips for top 2 platforms, (4) one content idea for the first week."
    ),
    "Budget Plan": (
        "Create a monthly marketing budget assuming $300/month total. "
        "Break it down by activity with exact dollar amounts. "
        "Also suggest 2-3 free/zero-cost tactics."
    ),
    "Execution Plan": (
        "Provide a 3-month execution roadmap. "
        "Month 1: Foundation & launch. Month 2: Growth & optimization. Month 3: Scale & retain. "
        "List 3-4 specific actions per month with milestones and success metrics."
    ),
    "Expected Results": (
        "Project realistic results after 3 months. Estimate: social media followers, website traffic, "
        "leads generated, conversion rate, and revenue potential. List 3 KPIs to track weekly."
    ),
}

_ERRORS = {
    "AuthenticationError": ("🔑 Invalid API Key",    "Your Groq API key is invalid or expired."),
    "RateLimitError":      ("⏳ Rate Limit Reached", "Too many requests. Retrying automatically..."),
    "APIConnectionError":  ("🌐 No Connection",      "Can't reach Groq API. Check your internet connection."),
    "APITimeoutError":     ("⌛ Request Timed Out",  "The request took too long. Retrying..."),
    "BadRequestError":     ("⚠️ Bad Request",        "Something was wrong with the request. Try rephrasing your idea."),
    "default":             ("❌ Unexpected Error",   "Something went wrong. Please try again in a moment."),
}

_INJECTION_PATTERNS = [
    "ignore previous", "ignore all", "disregard", "forget instructions",
    "you are now", "act as", "jailbreak", "system prompt", "new instructions",
    "override", "bypass", "pretend you",
]


def _friendly(e: Exception) -> tuple:
    return _ERRORS.get(type(e).__name__, _ERRORS["default"])


def _get_serpapi_key() -> str:
    return _secret("SERPAPI_KEY")


def sanitize_input(text: str) -> tuple[str, bool]:
    lower = text.lower()
    for pattern in _INJECTION_PATTERNS:
        if pattern in lower:
            return text, False
    return " ".join(text.split()), True


def validate_input(text: str) -> str | None:
    text = text.strip()
    if not text:
        return "Please describe your product or business idea."
    if len(text) < 10:
        return "That's a bit short — add a few more details for a better strategy."
    if len(text) > 1500:
        return "Please keep your description under 1500 characters."
    _, safe = sanitize_input(text)
    if not safe:
        return "Your input contains restricted phrases. Please describe your product naturally."
    return None


def _get_llm(model: str) -> ChatGroq:
    if not GROQ_API_KEY:
        st.error(
            "🔑 **No API key found.**\n\n"
            "Add your Groq API key to `.streamlit/secrets.toml`:\n"
            "```toml\nGROQ_API_KEY = 'your_key_here'\n```"
        )
        st.stop()
    return ChatGroq(model=model, api_key=GROQ_API_KEY, temperature=0.7)


def _invoke_with_fallback(messages: list, retries: int = 2, delay: float = 2.0) -> tuple[str, str]:
    last_error = None
    for model in _MODEL_CHAIN:
        llm = _get_llm(model)
        for attempt in range(retries):
            try:
                return llm.invoke(messages).content, model
            except Exception as e:
                last_error = e
                etype = type(e).__name__
                if attempt < retries - 1 and etype in ("RateLimitError", "APITimeoutError"):
                    time.sleep(delay * (attempt + 1))
                    continue
                if etype == "AuthenticationError":
                    title, msg = _friendly(e)
                    st.error(f"**{title}** — {msg}")
                    st.stop()
                break
    title, msg = _friendly(last_error)
    st.error(f"**{title}** — {msg}\n\nAll fallback models failed.")
    st.stop()


def _build_messages(product: str, instruction: str,
                    tone: str = "Professional", language: str = "English") -> list:
    tone_note = TONE_PROMPTS.get(tone, "")
    lang_note = LANGUAGES.get(language, "")
    extra = " ".join(filter(None, [tone_note, lang_note]))
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Product/Business Idea: {product}\n\n"
            f"Task: {instruction}\n\n"
            f"Respond in clear bullet points or short paragraphs. "
            f"Be specific, practical, and concise (max 150 words). {extra}"
        )),
    ]


@st.cache_data(show_spinner=False, ttl=86400)
def fetch_market_data(query: str) -> dict:
    key = _get_serpapi_key()
    if not key:
        return {}
    try:
        params = {"q": f"{query} market size trends competitors 2024",
                  "api_key": key, "num": 5, "engine": "google"}
        resp = requests.get("https://serpapi.com/search", params=params, timeout=8)
        resp.raise_for_status()
        snippets = [r.get("snippet", "") for r in resp.json().get("organic_results", [])[:4] if r.get("snippet")]
        return {"snippets": snippets, "source": "Google Search via SerpAPI"}
    except Exception:
        return {}


def _enrich_with_market_data(product: str, instruction: str) -> str:
    data = fetch_market_data(product)
    if not data or not data.get("snippets"):
        return instruction
    snippets = "\n".join(f"- {s}" for s in data["snippets"])
    return f"{instruction}\n\nReal market data:\n{snippets}\n(Source: {data['source']})"


@st.cache_data(show_spinner=False, ttl=3600)
def run_agents(product: str, tone: str = "Professional", language: str = "English") -> dict:
    section_names = list(SECTIONS.keys())
    model_used = {}

    def fetch(section: str) -> tuple[str, str, str]:
        instruction = SECTIONS[section]
        if section == "Market Analysis":
            instruction = _enrich_with_market_data(product, instruction)
        content, model = _invoke_with_fallback(
            _build_messages(product, instruction, tone, language)
        )
        return section, content, model

    results = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        for section, content, model in [f.result() for f in as_completed(
            {executor.submit(fetch, s): s for s in section_names}
        )]:
            results[section] = content
            model_used[section] = model

    ordered = {s: results[s] for s in section_names if s in results}
    ordered["_meta_model"] = list(set(model_used.values()))[0] if model_used else _MODEL_CHAIN[0]
    return ordered


def regenerate_section(product: str, section: str,
                       tone: str = "Professional", language: str = "English") -> str:
    instruction = SECTIONS[section]
    if section == "Market Analysis":
        instruction = _enrich_with_market_data(product, instruction)
    content, _ = _invoke_with_fallback(_build_messages(product, instruction, tone, language))
    return content


@st.cache_data(show_spinner=False, ttl=3600)
def get_competitor_data(product: str) -> dict:
    llm = _get_llm(_MODEL_CHAIN[0])
    messages = [
        SystemMessage(content="You are a market research analyst. Return only valid JSON, no explanation."),
        HumanMessage(content=(
            f"Product: {product}\n\n"
            "Identify 3 real competitors. Score each and the product on 5 dimensions (0-10): "
            "Price Competitiveness, Feature Set, Market Reach, Brand Awareness, Customer Support.\n\n"
            "Return ONLY this JSON:\n"
            '{"your_product":"short name","dimensions":["Price Competitiveness","Feature Set",'
            '"Market Reach","Brand Awareness","Customer Support"],'
            '"competitors":[{"name":"Name","scores":[7,8,9,6,7]},{"name":"Name","scores":[5,6,7,8,5]},'
            '{"name":"Name","scores":[8,7,6,9,8]}],"your_scores":[6,7,5,4,8]}'
        )),
    ]
    try:
        raw = llm.invoke(messages).content
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            data = json.loads(match.group())
            if "product" in data and "your_product" not in data:
                data["your_product"] = data.pop("product")
            if "scores" in data and "your_scores" not in data:
                data["your_scores"] = data.pop("scores")
            return data
    except Exception:
        pass
    return {
        "your_product": "Your Product",
        "dimensions": ["Price", "Features", "Market Reach", "Brand", "Support"],
        "competitors": [
            {"name": "Competitor A", "scores": [7, 8, 9, 8, 6]},
            {"name": "Competitor B", "scores": [5, 6, 7, 9, 7]},
            {"name": "Competitor C", "scores": [8, 7, 6, 7, 8]},
        ],
        "your_scores": [6, 7, 5, 4, 9],
    }
