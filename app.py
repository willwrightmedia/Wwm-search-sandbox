import json
import datetime
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- UI CONFIGURATION (WILL WRIGHT MEDIA BRANDING) ---
st.set_page_config(page_title="World Wide Monitor | Will Wright Media", page_icon="📡", layout="wide")

# CUSTOM CSS INJECTION - REPLACE COLOR HEX CODES TO MATCH YOUR SITE
st.markdown("""
    <style>
    /* Global Background & Typography */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    .main { background-color: #f8fafc; }
    
    /* Top Brand Bar / Header Banner */
    .brand-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #ffffff;
        padding: 24px 32px;
        border-radius: 12px;
        margin-bottom: 24px;
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.1);
    }
    .brand-title {
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        margin: 0;
        color: #ffffff;
    }
    .brand-subtitle {
        color: #94a3b8;
        font-size: 1rem;
        margin-top: 4px;
    }
    
    /* Executive Card Container */
    .report-card { 
        background-color: #ffffff; 
        padding: 32px; 
        border-radius: 12px; 
        border: 1px solid #e2e8f0; 
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.03); 
    }
    
    /* Primary Buttons */
    .stButton>button { 
        background-color: #0f172a; 
        color: #ffffff; 
        border-radius: 8px; 
        font-weight: 600; 
        padding: 0.65rem 1.4rem;
        border: none;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1e293b;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
    }
    
    /* Green Download Action Button */
    .stDownloadButton>button {
        background-color: #10b981 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.7rem 1.5rem !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.25) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stDownloadButton>button:hover {
        background-color: #059669 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(16, 185, 129, 0.35) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    # OPTIONAL LOGO PLACEHOLDER
    # st.image("https://your-domain.com/path-to-logo.png", width=220)
    
    st.title("Will Wright Media")
    st.caption("World Wide Monitor Engine")
    st.divider()
    
    st.subheader("1. API Configuration")
    api_provider = st.selectbox(
        "AI Engine Provider",
        ["Google Gemini (Native Grounding)", "Tavily + Gemini", "OpenAI GPT-4o"],
        index=0
    )
    
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    
    st.divider()
    st.subheader("2. Search Parameters")
    date_window = st.selectbox(
        "Time Horizon",
        ["Past 7 Days (Current Cycle)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive"],
        index=0
    )
    
    selected_sources = st.multiselect(
        "Target Channels",
        [
            "Global Tier-1 Media (Washington Post, Reuters, CNN, BBC)",
            "Australian National Press (AFR, ABC News, SMH, The Age)",
            "Official & Primary Releases (.gov.au, .edu.au)"
        ],
        default=[
            "Global Tier-1 Media (Washington Post, Reuters, CNN, BBC)",
            "Australian National Press (AFR, ABC News, SMH, The Age)",
            "Official & Primary Releases (.gov.au, .edu.au)"
        ]
    )

# --- BRANDED TOP HEADER BANNER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-title">World Wide Monitor</div>
        <div class="brand-subtitle">Executive Media Intelligence & Strategic Analysis</div>
    </div>
""", unsafe_allow_html=True)

# --- MAIN ENGINE INTERFACE ---
search_mode = st.radio("Search Mode:", ["Structured Parameters", "Advanced Boolean Search"], horizontal=True)

final_query = ""

if search_mode == "Structured Parameters":
    col1, col2, col3 = st.columns(3)
    with col1:
        must_all = st.text_input("Must include (AND)", placeholder="e.g., Sustainable Concrete")
    with col2:
        any_one = st.text_input("Any of these (OR)", placeholder="e.g., RMIT Roychand")
    with col3:
        not_mention = st.text_input("Exclude (NOT)", placeholder="e.g., Sports")
        
    query_parts = []
    if must_all.strip():
        query_parts.append(" ".join([f'"{w.strip()}"' if " " in w.strip() else w.strip() for w in must_all.split(",") if w.strip()]))
    if any_one.strip():
        query_parts.append(f"({' OR '.join([f'\"{w.strip()}\"' if ' ' in w.strip() else w.strip() for w in any_one.split() if w.strip()])})")
    if not_mention.strip():
        query_parts.append(" ".join([f"-{w.strip()}" for w in not_mention.split() if w.strip()]))
    final_query = " ".join(query_parts)

else:
    final_query = st.text_input("Raw Query String", value='("Coffee Biochar" OR "Sustainable Concrete") AND "RMIT"')

if final_query.strip():
    st.markdown("**Active Query Parameters:**")
    st.code(final_query, language="text")

st.markdown("<br>", unsafe_allow_html=True)

if st.button("Generate Executive Brief"):
    st.info("Trigger search pipeline using configured parameters...")
