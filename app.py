import json
import datetime
import io
import re
import time
import streamlit as st
import pandas as pd
import altair as alt
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from docx import Document
from fpdf import FPDF
from duckduckgo_search import DDGS

# ============================================================================
# 1. GLOBAL PAGE CONFIG & AUTHENTICATION SESSION STATE
# ============================================================================
st.set_page_config(page_title="Kat Intelligence Engine", page_icon="🦦", layout="wide")

# Persistent Founder Credentials (Blank by default on public UI)
FOUNDER_EMAIL = "will@willwrightmedia.com"
FOUNDER_PASSWORD = "MyPa$$wordI5Hard"
FOUNDER_API_KEY = "AQ.Ab8RN6JvY9bawEOyAp-SNM2vJ1jwjtFjAdNgh2bxg_Othfr7HA"

if "users_db" not in st.session_state:
    st.session_state.users_db = {
        FOUNDER_EMAIL: {
            "email": FOUNDER_EMAIL,
            "password": FOUNDER_PASSWORD,
            "full_name": "Will Wright",
            "is_admin": True,
            "current_plan": "Founder / Kat Engine Admin",
            "default_engine": "Google Gemini 3 (Native search grounding)",
            "api_key": FOUNDER_API_KEY,
            "total_searches": 0,
            "created_at": "2026-09-26"
        }
    }

if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None

# Custom CSS - HIGH-CONTRAST BONE INPUT FIELDS, DARK INK PALETTE & ANIMATED MEERKAT MASCOT
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    .stApp { background-color: #14120F !important; color: #F2EDE3 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #1A1814 !important; border-right: 1px solid #2C2822 !important; }
    [data-testid="stSidebar"] * { color: #C6BCA9 !important; }

    /* HIGH-CONTRAST BONE INPUT FIELDS */
    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
        background-color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important; border-radius: 2px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input, div[data-baseweb="textarea"] textarea, textarea {
        background-color: #F2EDE3 !important; color: #14120F !important; font-weight: 600 !important; font-size: 0.95rem !important; opacity: 1 !important;
    }
    div[data-baseweb="input"] input::placeholder, div[data-baseweb="textarea"] textarea::placeholder, textarea::placeholder {
        color: #777777 !important; opacity: 0.8 !important;
    }
    div[data-baseweb="select"] * { color: #14120F !important; font-weight: 600 !important; }

    /* RESPONSIVE METRIC CARDS */
    .metric-card {
        background-color: #1A1814;
        border: 1px solid #2C2822;
        padding: 16px 8px;
        border-radius: 2px;
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 110px;
        box-sizing: border-box;
        overflow: hidden;
    }
    .metric-card h4 {
        font-family: 'Inter', sans-serif;
        font-size: clamp(0.65rem, 1vw, 0.75rem);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #C6BCA9;
        margin: 0 0 4px 0;
        word-break: break-word;
        max-width: 100%;
    }
    .metric-card h2 {
        font-family: 'Inter', sans-serif;
        font-size: clamp(1.0rem, 1.8vw, 1.4rem);
        font-weight: 600;
        color: #F2EDE3;
        margin: 0 0 4px 0;
        word-break: break-word;
        max-width: 100%;
    }
    .metric-card caption {
        font-size: clamp(0.6rem, 0.85vw, 0.7rem);
        color: #6B6B6B;
        margin: 0;
        word-break: break-word;
        max-width: 100%;
    }

    .stButton>button {
        background-color: transparent !important; color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        border-radius: 2px !important; padding: 0.65rem 1.4rem !important; font-family: 'Inter', sans-serif !important;
        font-size: 0.75rem !important; letter-spacing: 0.15em !important; text-transform: uppercase !important;
    }
    .stDownloadButton>button {
        background-color: #C6BCA9 !important; color: #14120F !important; font-weight: 600 !important;
        padding: 0.75rem 1.4rem !important; border-radius: 2px !important; border: none !important;
    }
    .reset-btn>button {
        background-color: #2C2822 !important; color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        font-weight: 600 !important; padding: 0.5rem 1rem !important;
    }
    .report-card { background-color: #1A1814; border: 1px solid #2C2822; padding: 28px; border-radius: 2px; }
    .disclaimer-box { background-color: #1A1814; border-left: 2px solid #C6BCA9; padding: 10px 14px; font-size: 0.8rem; color: #6B6B6B; margin-top: 20px; }
    .notice-box { background-color: #1A1814; border-left: 2px solid #6B6B6B; padding: 8px 12px; font-size: 0.78rem; color: #C6BCA9; margin-bottom: 14px; }
    .admin-card { background-color: #1F1C18; border: 1px solid #C6BCA9; padding: 18px; margin-bottom: 20px; border-radius: 2px; }

    /* ANIMATED MEERKAT SEARCH GRAPHIC */
    .meerkat-search-container {
        background-color: #1A1814;
        border: 1px solid #2C2822;
        padding: 24px;
        text-align: center;
        margin: 20px 0;
        border-radius: 2px;
    }
    .meerkat-anim-box {
        height: 90px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .meerkat-svg {
        animation: meerkatCycle 4s infinite ease-in-out;
    }
    @keyframes meerkatCycle {
        0% { transform: translateY(20px) scale(0.8) rotate(15deg); opacity: 0.6; } /* Burrowed / Low */
        25% { transform: translateY(10px) scale(0.9) rotate(0deg); opacity: 0.8; } /* On All Fours */
        50% { transform: translateY(-10px) scale(1.15); opacity: 1; }              /* Standing Tall to Attention */
        75% { transform: translateY(-5px) scale(1.1) rotate(-5deg); opacity: 1; }   /* Looking Out for Threats */
        100% { transform: translateY(25px) scale(0.7); opacity: 0.4; }             /* Retreating to Burrow */
    }

    /* TABLET & MOBILE REFLOW RULES */
    @media (max-width: 992px) {
        div[data-testid="column"] {
            flex: 1 1 45% !important;
            min-width: 45% !important;
            margin-bottom: 12px;
        }
    }
    @media (max-width: 576px) {
        div[data-testid="column"] {
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }
    }
    </style>
""", unsafe_allow_html=True)

# Helper function to render the interactive Meerkat Search Animation
def render_meerkat_search_animation(status_label="Grounded search in progress..."):
    st.markdown(f"""
        <div class="meerkat-search-container">
            <div class="meerkat-anim-box">
                <svg class="meerkat-svg" width="60" height="90" viewBox="0 0 60 100" fill="#F2EDE3" xmlns="http://www.w3.org/2000/svg">
                    <!-- Sentry Head -->
                    <path d="M35 8c4 0 8 3 9 7 2-1 4 0 4 2s-2 4-5 4c-3 5-10 7-16 5-4-2-6-6-4-11 2-4 7-7 12-7z"/>
                    <!-- Eye -->
                    <circle cx="40" cy="12" r="1.5" fill="#14120F"/>
                    <!-- Torso -->
                    <path d="M28 22c2 7 2 17 1 30s-3 23-1 33c3 4 13 4 15 0-2-13-3-30-2-48 1-10-2-17-6-17z"/>
                    <!-- Folded Paws -->
                    <path d="M37 35c5 2 8 6 6 9-3 1-7-3-8-7z"/>
                    <!-- Tail -->
                    <path d="M27 75C18 79 8 85 1 91c-2 2 0 3 3 1 9-6 17-11 25-13z"/>
                    <!-- Planted Feet -->
                    <path d="M26 81l-6 4h9zM39 81l7 4h-10z"/>
                </svg>
            </div>
            <div style="font-family: 'Cormorant Garamond', serif; font-size: 1.3rem; color: #F2EDE3; margin-top: 8px;">
                Meerkat Standing to Attention
            </div>
            <div style="font-family: 'Inter', sans-serif; font-size: 0.75rem; letter-spacing: 0.15em; text-transform: uppercase; color: #C6BCA9;">
                {status_label}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============================================================================
# 2. AUTHENTICATION WALL (BLANK BY DEFAULT)
# ============================================================================
def render_login_wall():
    st.markdown("""
        <div style="text-align: center; padding: 40px 0px;">
            <svg width="60" height="100" viewBox="0 0 60 100" fill="#F2EDE3" xmlns="http://www.w3.org/2000/svg">
                <path d="M35 8c4 0 8 3 9 7 2-1 4 0 4 2s-2 4-5 4c-3 5-10 7-16 5-4-2-6-6-4-11 2-4 7-7 12-7z"/>
                <circle cx="40" cy="12" r="1.5" fill="#14120F"/>
                <path d="M28 22c2 7 2 17 1 30s-3 23-1 33c3 4 13 4 15 0-2-13-3-30-2-48 1-10-2-17-6-17z"/>
                <path d="M37 35c5 2 8 6 6 9-3 1-7-3-8-7z"/>
                <path d="M27 75C18 79 8 85 1 91c-2 2 0 3 3 1 9-6 17-11 25-13z"/>
                <path d="M26 81l-6 4h9zM39 81l7 4h-10z"/>
            </svg>
            <div style="font-family: 'Cormorant Garamond', serif; font-size: 3.0rem; color: #F2EDE3; margin-top: 10px;">
                Kat Intelligence Engine
            </div>
            <div style="font-family: 'Inter', sans-serif; font-size: 0.8rem; letter-spacing: 0.25em; text-transform: uppercase; color: #6B6B6B;">
                SOVEREIGN INTELLIGENCE PLATFORM • MEDIERKAT & MARKAT
            </div>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab1, tab2 = st.tabs(["🔒 Member Login", "📝 Free Sandbox Access"])
        with tab1:
            email_in = st.text_input("Email Address", value="", placeholder="name@company.com", key="login_email")
            pass_in = st.text_input("Password", type="password", value="", placeholder="••••••••", key="login_pass")
            if st.button("Authenticate", use_container_width=True):
                user = st.session_state.users_db.get(email_in)
                if user and user["password"] == pass_in:
                    st.session_state.authenticated_user = user
                    st.success(f"Access granted. Welcome {user['full_name']}")
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        with tab2:
            s_name = st.text_input("Full Name", value="", key="s_name")
            s_email = st.text_input("Email", value="", key="s_email")
            s_pass = st.text_input("Password", type="password", value="", key="s_pass")
            if st.button("Register Free Sandbox Account", use_container_width=True):
                if s_email in st.session_state.users_db:
                    st.warning("Account already exists.")
                elif s_email and s_pass:
                    st.session_state.users_db[s_email] = {
                        "email": s_email,
                        "password": s_pass,
                        "full_name": s_name,
                        "is_admin": False,
                        "current_plan": "Sandbox Unlimited (Free)",
                        "default_engine": "DuckDuckGo Search",
                        "api_key": None,
                        "total_searches": 0,
                        "created_at": datetime.datetime.now().strftime("%Y-%m-%d")
                    }
                    st.success("Account created! Please log in.")
                else:
                    st.error("Please fill in all fields.")

if st.session_state.authenticated_user is None:
    render_login_wall()
    st.stop()

# ============================================================================
# 3. LOGGED-IN WORKSPACE & BRAND SWITCHER
# ============================================================================
current_user = st.session_state.authenticated_user

# --- INITIALIZE PERSISTENT SESSION STATE ---
if "active_app" not in st.session_state:
    st.session_state.active_app = "Medierkat (PR & Media)"
if "cumulative_brief" not in st.session_state:
    st.session_state.cumulative_brief = None
if "executed_query" not in st.session_state:
    st.session_state.executed_query = ""
if "user_plan" not in st.session_state:
    st.session_state.user_plan = current_user["current_plan"]
if "search_balance" not in st.session_state:
    st.session_state.search_balance = 100 if current_user["is_admin"] else 10
if "saved_queries" not in st.session_state:
    st.session_state.saved_queries = []
if "report_library" not in st.session_state:
    st.session_state.report_library = []

def clear_all_searches():
    st.session_state.cumulative_brief = None
    st.session_state.executed_query = ""
    st.rerun()

# --- TOP PLATFORM CONTROL BAR ---
p_col1, p_col2, p_col3 = st.columns([2, 2, 1])
with p_col1:
    st.markdown(f"**Kat Engine Active Session:** `{current_user['full_name']}` ({current_user['email']})")
with p_col2:
    st.session_state.active_app = st.selectbox(
        "Select Platform App Layer:",
        ["Medierkat (PR & Media)", "Markat (Marketing & Competitors)"],
        index=0 if "Medierkat" in st.session_state.active_app else 1
    )
with p_col3:
    if st.button("🔒 Log Out", use_container_width=True):
        st.session_state.authenticated_user = None
        st.rerun()

st.divider()

# --- NAVIGATION CONTROLLER ---
main_mode = st.radio(
    "Select mode:",
    ["📊 Dashboard", "📄 Brief", "📚 Library"],
    horizontal=True
)

is_markat = "Markat" in st.session_state.active_app

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    if is_markat:
        st.markdown("### MARKAT")
        st.caption("COMPETITOR & CAMPAIGN INTELLIGENCE")
    else:
        st.markdown("### MEDIERKAT")
        st.caption("GLOBAL MEDIA INSIGHTS")
    st.divider()
    
    st.subheader("1. Intelligence engine")
    api_provider = st.selectbox(
        "AI engine provider",
        [
            "Google Gemini 3 (Native search grounding)",
            "OpenAI GPT-4o (Web grounded)",
            "Tavily Search + Gemini intelligence"
        ],
        index=0
    )
    
    default_key = current_user["api_key"] if current_user["api_key"] else ""
    gemini_key = st.text_input("Gemini API key", value=default_key, type="password", placeholder="AIzaSy...")

    st.divider()
    st.subheader("2. Objective and scope")
    
    if is_markat:
        report_purpose_selected = st.selectbox(
            "Primary objective",
            [
                "Benchmark campaign impact vs key competitors",
                "Audit competitor share of voice & customer feedback",
                "Evaluate narrative positioning for upcoming launch",
                "CMO strategic performance briefing",
                "Custom strategic objective"
            ],
            index=0
        )
    else:
        report_purpose_selected = st.selectbox(
            "Primary objective",
            [
                "Demonstrate long-term impact & track record",
                "Identify emerging issue / early warning radar",
                "Track ongoing issue / crisis management",
                "Institutional board briefing / executive reporting",
                "Custom strategic objective"
            ],
            index=0
        )
    
    custom_purpose_input = ""
    if "Custom" in report_purpose_selected:
        custom_purpose_input = st.text_input("Specify custom objective:", placeholder="Enter custom focus...")
        
    active_report_purpose = custom_purpose_input if custom_purpose_input.strip() else report_purpose_selected

    report_format_tier = st.selectbox(
        "Select report type",
        [
            "Executive leadership brief (Strict 1 page PDF — C-Suite and Board)",
            "Strategic advisory report (2 pages PDF — Subject experts)",
            "Comprehensive operations report (Up to 4 pages — Media/Marketing teams)",
            "Digital intelligence digest (Up to 2 pages — Digital teams)"
        ],
        index=0
    )

    output_language = st.selectbox(
        "Report output language",
        ["English", "French (Français)", "Spanish (Español)", "German (Deutsch)", "Mandarin Chinese (中文)", "Japanese (日本語)", "Indonesian (Bahasa Indonesia)", "Vietnamese (Tiếng Việt)", "Hindi (हिंदी)", "Arabic (العربية)"],
        index=0
    )
    
    st.divider()
    st.subheader("3. Media channels and horizon")
    
    date_window_option = st.selectbox(
        "Recency scope",
        [
            "Past 24 hours (Current cycle)",
            "Past 7 days (Past week)",
            "Past 30 days (Past month)",
            "Past 12 months (Past year)",
            "Past 5 years archive",
            "Custom time horizon"
        ],
        index=2 if is_markat else 3
    )

    date_window = date_window_option

    social_media_focus = st.selectbox(
        "Coverage scope",
        [
            "Include major news and verified social media combined",
            "Focus exclusively on major news and broadcast press",
            "Focus exclusively on high-reach social media channels"
        ],
        index=0
    )
    
    selected_sources = st.multiselect(
        "Target channels",
        [
            "Global tier-1 press & wires",
            "Australian press & national broadcasters",
            "Major social media channels (>10,000 followers)",
            "Southeast Asian press",
            "Official releases (.gov.au, .edu.au, ASX)"
        ],
        default=[
            "Global tier-1 press & wires",
            "Australian press & national broadcasters",
            "Official releases (.gov.au, .edu.au, ASX)"
        ]
    )

    st.divider()
    st.button("Reset brief buffer and clear all", on_click=clear_all_searches, key="sidebar_reset")

# --- BRANDED EXECUTIVE HEADER ---
app_title = "Markat" if is_markat else "Medierkat"
app_subtitle = "Strategic marketing performance, competitor benchmarking, and share of voice." if is_markat else "Strategic media intelligence, verified reach analytics, and cross-lingual reporting for leadership."
app_tagline = "COMPETITOR & CAMPAIGN INTELLIGENCE" if is_markat else "GLOBAL MEDIA INSIGHTS"
tooltip_text = "Build reports step by step: Run live web searches, add article links, or directly enter broadcast, print, and social media records."

st.markdown(f"""
    <div style="display: flex; align-items: center; background-color: #1A1814; border: 1px solid #2C2822; padding: 24px 30px; border-radius: 2px; margin-bottom: 24px;">
        <div style="margin-right: 24px; flex-shrink: 0;">
            <svg width="45" height="75" viewBox="0 0 60 100" fill="#F2EDE3" xmlns="http://www.w3.org/2000/svg">
                <path d="M35 8c4 0 8 3 9 7 2-1 4 0 4 2s-2 4-5 4c-3 5-10 7-16 5-4-2-6-6-4-11 2-4 7-7 12-7z"/>
                <circle cx="40" cy="12" r="1.5" fill="#14120F"/>
                <path d="M28 22c2 7 2 17 1 30s-3 23-1 33c3 4 13 4 15 0-2-13-3-30-2-48 1-10-2-17-6-17z"/>
                <path d="M37 35c5 2 8 6 6 9-3 1-7-3-8-7z"/>
                <path d="M27 75C18 79 8 85 1 91c-2 2 0 3 3 1 9-6 17-11 25-13z"/>
                <path d="M26 81l-6 4h9zM39 81l7 4h-10z"/>
            </svg>
        </div>
        <div>
            <div style="font-family: 'Inter', sans-serif; font-size: 0.75rem; letter-spacing: 0.25em; text-transform: uppercase; color: #6B6B6B; margin-bottom: 4px;">
                {app_tagline}
            </div>
            <div style="font-family: 'Cormorant Garamond', serif; font-size: 2.6rem; font-weight: 400; color: #F2EDE3; line-height: 1;">
                {app_title}
            </div>
            <div style="font-family: 'Cormorant Garamond', serif; font-size: 1.1rem; font-style: italic; color: #C6BCA9; margin-top: 6px;">
                {app_subtitle}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

control_col1, control_col2 = st.columns([3, 1])
with control_col1:
    st.markdown(f"##### Active Workspace <span title='{tooltip_text}' style='cursor: pointer; color: #C6BCA9; font-size: 1rem;'>ℹ️</span>", unsafe_allow_html=True)
with control_col2:
    st.markdown("<div class='reset-btn'>", unsafe_allow_html=True)
    st.button("🔄 Refresh", on_click=clear_all_searches, key="header_reset", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- STRICT AUSTRALIAN ENGLISH SCHEMAS ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher, broadcaster, major social channel, or competitor verbatim.")
    medium_type: str = Field(description="Media format(s) covering this story.")
    author_byline: str = Field(description="Author or handle. Write 'not stated' if absent.")
    publication_date: str = Field(description="Publication date verbatim.")
    original_language: str = Field(description="Original language.")
    canonical_source_url: str = Field(description="Direct resolving URL from grounding.")
    audience_reach_metrics: str = Field(description="Audience reach or follower counts.")
    verification_confidence: str = Field(description="Flag as '[Verified Tier-1 Source]' or '[Uncorroborated]'")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Factual title describing the event or campaign.")
    source_category: str = Field(description="Category of source.")
    prominence_depth: str = Field(description="Feature, Segment, or Mention.")
    representation_mode: str = Field(description="Framing or sentiment.")
    key_message_delivered: str = Field(description="Core key message delivered.")
    co_represented_entities: str = Field(description="Competitors or co-featured brands.")
    core_event_summary: str = Field(description="Summary of coverage.")
    covering_outlets: list[CoverageOutlet]

class WWMExecutiveAnalysisBrief(BaseModel):
    coverage_found: bool = Field(description="Set to False if no verified coverage matched.")
    verified_coverage_metric: str = Field(description="Count of retrieved records.")
    total_combined_audience_reach: str = Field(description="Summed aggregate reach.")
    headline_synthesis: str = Field(description="1-2 sentence executive overview.")
    sentiment_framing_read: str = Field(description="1-2 lines evaluating framing or competitor positioning.")
    subject_quoted_vs_reported: str = Field(description="Verbatim quotes vs reported speech.")
    engagement_opportunities: str = Field(description="Strategic commentary identifying opportunities.")
    items: list[EventCoverageItem]

# --- BRANDED PDF ENGINE ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(107, 107, 107)
        self.set_y(10)
        tag = "MARKAT" if "Markat" in st.session_state.active_app else "MEDIERKAT"
        self.cell(0, 5, f'{tag}  |  EXECUTIVE BRIEF', align='R')

    def footer(self):
        self.set_y(-14)
        self.set_font('Helvetica', '', 6.5)
        self.set_text_color(107, 107, 107)
        self.cell(0, 5, 'Generated with AI assistance via Kat Intelligence Engine. Confirm critical details against source.', align='C')

def clean_pdf_text(text):
    if not text: return ""
    replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-', '•': '*'}
    for orig, repl in replacements.items(): text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')

def is_valid_url(url):
    return url and url.strip().lower() not in ["none", "null", "", "direct record input"] and url.strip().startswith("http")

def generate_pdf_brief(brief, query, lang, purpose_text, tier_type, time_scope, cov_scope, channels_str, is_strict_one_page=False):
    pdf = PDFReport()
    pdf.set_fill_color(242, 237, 227)
    margin_side, top_margin, bottom_margin = 18, 22, 20
    pdf.set_margins(margin_side, top_margin, margin_side)
    pdf.add_page()
    pdf.set_auto_page_break(auto=not is_strict_one_page, margin=bottom_margin)
    epw = pdf.epw
    
    clean_query = query.strip()[:47] + "..." if len(query.strip()) > 50 else query.strip()
    pdf.set_font('Helvetica', 'B', 12 if is_strict_one_page else 14)
    pdf.set_text_color(35, 35, 35)
    pdf.cell(epw, 5.5 if is_strict_one_page else 7, clean_pdf_text(f'Executive Brief ({lang})'), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', 'B', 7 if is_strict_one_page else 7.5)
    pdf.set_text_color(107, 107, 107)
    pdf.cell(epw, 3.5, clean_pdf_text(f'OBJECTIVE: {purpose_text.upper()}'), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', 'I', 6.5 if is_strict_one_page else 7.5)
    pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f'Format: {tier_type}  |  Language: {lang}'))
    pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f'Scope: {clean_query}  |  Recency: {time_scope}'))
    pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f'{brief.get("verified_coverage_metric", "")}  |  {brief.get("total_combined_audience_reach", "")}'))
    
    pdf.set_draw_color(198, 188, 169)
    pdf.ln(2)
    pdf.line(margin_side, pdf.get_y(), margin_side + epw, pdf.get_y())
    pdf.ln(3)
    
    h_size, body_size, lh = (9, 8, 3.3) if is_strict_one_page else (10.5, 9, 4.2)
    
    pdf.set_font('Helvetica', 'B', h_size)
    pdf.cell(epw, 4, '1. Executive overview', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('headline_synthesis', '')))
    pdf.ln(2)
    
    pdf.set_font('Helvetica', 'B', h_size)
    pdf.cell(epw, 4, '2. Positioning & reputation', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('sentiment_framing_read', '')))
    pdf.ln(2)

    pdf.set_font('Helvetica', 'B', h_size)
    pdf.cell(epw, 4, '3. Strategic opportunities', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('engagement_opportunities', '')))
    pdf.ln(2)
    
    return bytes(pdf.output())

# --- REUSABLE EXECUTION ENGINE ---
def run_synthesis_engine(search_query_input, custom_urls_input, submit_manual, raw_outlets_batch, man_mediums, man_topic, man_framing, man_depth, man_co_represented, man_reach, man_byline, man_summary):
    if not search_query_input and not custom_urls_input and not submit_manual and not st.session_state.executed_query:
        st.error("Please enter a search query, paste article URLs, or complete the direct input form.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API key.")
    else:
        # Display the Animated Meerkat Search Container during execution
        anim_placeholder = st.empty()
        with anim_placeholder.container():
            render_meerkat_search_animation(f"Scanning horizon for {app_title} intelligence & threats...")
            
        current_date = datetime.datetime.now().strftime("%B %d, %Y")
        channels_str = ", ".join(selected_sources) if selected_sources else "All Global Channels"
        
        prompt = f"""
        Today is {current_date}.
        You are {app_title}'s Senior Strategic Intelligence Analyst.
        PRIMARY STRATEGIC OBJECTIVE: {active_report_purpose}. 
        REPORT OUTPUT LANGUAGE: Synthesise the entire executive brief in {output_language}.
        ACTIVE SCOPE QUERY: {search_query_input if search_query_input else st.session_state.executed_query}
        SPELLING MANDATE: Use strict AUSTRALIAN ENGLISH.
        """
        
        try:
            client = genai.Client(api_key=gemini_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{"google_search": {}}],
                    response_mime_type="application/json",
                    response_schema=WWMExecutiveAnalysisBrief,
                    temperature=0.0,
                )
            )
            st.session_state.cumulative_brief = json.loads(response.text)
            st.session_state.active_purpose = active_report_purpose
            st.session_state.active_tier_type = report_format_tier
            st.session_state.active_lang = output_language
            st.session_state.active_time_scope = date_window
            st.session_state.active_cov_scope = social_media_focus
            st.session_state.active_channels = channels_str
            
            st.session_state.report_library.append({
                "id": len(st.session_state.report_library) + 1,
                "date": datetime.datetime.now().strftime("%d %b %Y"),
                "query": search_query_input if search_query_input else st.session_state.executed_query,
                "objective": active_report_purpose,
                "reach": st.session_state.cumulative_brief.get("total_combined_audience_reach", "N/A"),
                "data": st.session_state.cumulative_brief
            })
            anim_placeholder.empty() # Clear search animation upon completion
            st.success("Executive synthesis complete!")
        except Exception as e:
            anim_placeholder.empty()
            st.error(f"Processing error: {str(e)}")

# --- VIEW 1: LIVE DASHBOARD ---
if "Dashboard" in main_mode:
    st.subheader(f"📊 {app_title} tracking dashboard")
    st.caption("Real-time monitoring view for market spikes, campaign reach, and competitor benchmarking.")
    
    with st.expander("⚡ Launch intelligence synthesis from dashboard", expanded=True):
        dash_search_query = st.text_input("Enter query terms:", placeholder="e.g. Enter brand, individual, or topic...")
        if st.button("⚡ Execute synthesis"):
            st.session_state.executed_query = dash_search_query
            run_synthesis_engine(dash_search_query, [], False, "", [], "", "", "", "", "", "", "")

    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.cumulative_brief:
        cb = st.session_state.cumulative_brief
        dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
        with dash_col1:
            st.markdown(f"<div class='metric-card'><h4>Volume</h4><h2>{len(cb.get('items', []))} Hits</h2><caption>{date_window}</caption></div>", unsafe_allow_html=True)
        with dash_col2:
            st.markdown(f"<div class='metric-card'><h4>Audience Reach</h4><h2>{cb.get('total_combined_audience_reach', '--')}</h2><caption>Verified press & social</caption></div>", unsafe_allow_html=True)
        with dash_col3:
            st.markdown("<div class='metric-card'><h4>Channel Share</h4><h2>Online Press</h2><caption>Dominant channel</caption></div>", unsafe_allow_html=True)
        with dash_col4:
            st.markdown("<div class='metric-card'><h4>Framing Score</h4><h2>Positive</h2><caption>Domain authority</caption></div>", unsafe_allow_html=True)

# --- VIEW 2: STRATEGIC BRIEF EXECUTION ---
elif "Brief" in main_mode:
    tab_search, tab_custom_urls = st.tabs(["🔍 Live search", "🔗 Added links"])
    with tab_search:
        search_query_input = st.text_input("Search terms (AND/OR/NOT supported):", placeholder="e.g. Enter target terms...")
    with tab_custom_urls:
        raw_urls_text = st.text_area("Paste URLs (Up to 100):", height=100, placeholder="https://www.example.com/article...")
        custom_urls_input = [line.strip() for line in raw_urls_text.split("\n") if line.strip().startswith("http")]

    if st.button("Generate executive brief"):
        st.session_state.executed_query = search_query_input
        run_synthesis_engine(search_query_input, custom_urls_input, False, "", [], "", "", "", "", "", "", "")

# --- VIEW 3: REPORT LIBRARY & ADMIN CONSOLE ---
else:
    st.subheader("📚 Saved 50-query deck & Admin Console")
    
    if current_user["is_admin"]:
        st.markdown("<div class='admin-card'>", unsafe_allow_html=True)
        st.markdown("### ⚙️ Admin User Overview")
        admin_rows = []
        for u in st.session_state.users_db.values():
            admin_rows.append({
                "Email": u["email"],
                "Full Name": u["full_name"],
                "Plan": u["current_plan"],
                "Total Searches": u["total_searches"],
                "Created At": u["created_at"]
            })
        st.table(admin_rows)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("#### Active 50-Query Deck")
    new_deck_query = st.text_input("Add new topic to 50-query deck:", placeholder="Enter brand, topic, or keyword...")
    if st.button("➕ Add topic to saved deck"):
        if new_deck_query.strip() and len(st.session_state.saved_queries) < 50:
            st.session_state.saved_queries.append(new_deck_query.strip())
            st.success("Topic added to deck!")
            st.rerun()

    for idx, q in enumerate(st.session_state.saved_queries, 1):
        st.markdown(f"**{idx}.** `{q}`")

# --- DELIVERABLE RENDER ---
if st.session_state.cumulative_brief and ("Dashboard" in main_mode or "Brief" in main_mode):
    brief = st.session_state.cumulative_brief
    st.markdown("---")
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    st.caption(f"CONFIDENTIAL | {app_title.upper()} EXECUTIVE BRIEF")
    st.header(f"Executive brief ({output_language})")
    st.info(brief.get("headline_synthesis", ""))
    st.markdown("</div>", unsafe_allow_html=True)
