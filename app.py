"""
Kat Intelligence Engine — Medierkat & Markat
Patched build: explicit Developer API routing, robust key sanitization, guest entry,
grounded-URL verification, per-campaign domain dedup, reach maths, and active dashboard metrics.
"""

import copy
import datetime
import html
import io
import json
import re
from collections import Counter
from urllib.parse import urlparse

import altair as alt
import pandas as pd
import requests
import streamlit as st
from docx import Document
from fpdf import FPDF
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

try:
    from importlib.metadata import version as _pkg_version
    GENAI_VERSION = _pkg_version("google-genai")
except Exception:
    GENAI_VERSION = "unknown"

st.set_page_config(page_title="Kat Intelligence Engine", page_icon="🦦", layout="wide")

# ============================================================================
# 0. CONSTANTS
# ============================================================================
DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-flash-latest"
NUM_PASSES = 4

PASS_ANGLES = [
    "official institutional media releases, announcements and newsroom posts",
    "mainstream national and international news mastheads, broadcasters and wire services",
    "trade press, specialist outlets and peer-reviewed publications",
    "social media and Reddit community discussion",
]

RECENCY_OPTIONS = {
    "Past 24 hours (Current cycle)": 1,
    "Past 7 days (Past week)": 7,
    "Past 30 days (Past month)": 30,
    "Past 12 months (Past year)": 365,
    "Past 5 years archive": 1826,
    "Custom time horizon": None,
}

JOURNAL_DOMAINS = (
    "sciencedirect.com", "springer.com", "link.springer.com", "nature.com", "wiley.com",
    "onlinelibrary.wiley.com", "tandfonline.com", "mdpi.com", "sagepub.com", "cell.com",
    "science.org", "pnas.org", "plos.org", "frontiersin.org", "iopscience.iop.org",
    "acs.org", "rsc.org", "bmj.com", "thelancet.com", "doi.org",
)

UNIT_MULTIPLIERS = {"trillion": 1e12, "billion": 1e9, "b": 1e9, "million": 1e6, "m": 1e6, "k": 1e3}

TITLE_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "rmit", "university", "research", "new",
    "breakthrough", "study", "report", "news", "media", "release", "campaign", "coverage",
}


# ============================================================================
# 1. SECRETS & AUTHENTICATION
# ============================================================================
def secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def sanitize_api_key(raw_key: str) -> str:
    """Removes non-printable ASCII and hidden whitespace chars like non-breaking space."""
    if not raw_key:
        return ""
    return re.sub(r"[^\w\.\-]", "", str(raw_key).strip())


def create_gemini_client(api_key: str) -> genai.Client:
    """Forces use of Google AI Studio Developer API and bypasses Vertex AI env variables."""
    clean_key = sanitize_api_key(api_key)
    return genai.Client(api_key=clean_key, vertexai=False, enterprise=False)


SESSION_DEFAULTS = {
    "authenticated_user": None,
    "active_app": "Medierkat (PR & Media)",
    "main_mode": "📊 Dashboard",
    "cumulative_brief": None,
    "executed_query": "",
    "pending_query": None,
    "saved_queries": [],
    "report_library": [],
}
for _k, _v in SESSION_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = copy.deepcopy(_v)

# ============================================================================
# 2. STYLES
# ============================================================================
st.markdown("""
    <style>
    @import url('[https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap](https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap)');

    .stApp { background-color: #14120F !important; color: #F2EDE3 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #1A1814 !important; border-right: 1px solid #2C2822 !important; }
    [data-testid="stSidebar"] * { color: #C6BCA9 !important; }

    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
        background-color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important; border-radius: 2px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input, div[data-baseweb="textarea"] textarea, textarea {
        background-color: #F2EDE3 !important; color: #14120F !important; font-weight: 600 !important; font-size: 0.95rem !important; opacity: 1 !important;
    }
    div[data-baseweb="input"] input::placeholder, textarea::placeholder { color: #777777 !important; opacity: 0.8 !important; }
    div[data-baseweb="select"] * { color: #14120F !important; font-weight: 600 !important; }

    .st-key-prominent_search input {
        font-size: 1.35rem !important; padding: 14px 18px !important; height: 56px !important; font-weight: 600 !important;
    }
    .st-key-prominent_search button {
        height: 56px !important; font-size: 1.1rem !important; font-weight: 700 !important; letter-spacing: 0.15em !important;
        background-color: #C6BCA9 !important; color: #14120F !important; border: none !important; border-radius: 2px !important;
    }

    .metric-card {
        background-color: #1A1814; border: 1px solid #2C2822; padding: 18px 12px; border-radius: 2px; text-align: center;
        height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;
        min-height: 125px; box-sizing: border-box; overflow: hidden;
    }
    .metric-card h4 { font-size: clamp(0.65rem, 0.9vw, 0.75rem); letter-spacing: 0.12em; text-transform: uppercase; color: #C6BCA9; margin: 0 0 6px 0; }
    .metric-card h2 { font-size: clamp(0.95rem, 1.4vw, 1.25rem); font-weight: 600; color: #F2EDE3; line-height: 1.2; margin: 0 0 6px 0; word-break: break-word; }
    .metric-card .cap { font-size: clamp(0.6rem, 0.8vw, 0.7rem); color: #8A8275; margin: 0; }

    .stButton>button {
        background-color: transparent !important; color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        border-radius: 2px !important; padding: 0.65rem 1.4rem !important; font-size: 0.75rem !important;
        letter-spacing: 0.15em !important; text-transform: uppercase !important;
    }
    .stDownloadButton>
