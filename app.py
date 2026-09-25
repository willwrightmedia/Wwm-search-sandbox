import json
import datetime
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- UI CONFIGURATION (WILL WRIGHT MEDIA BRANDING) ---
st.set_page_config(page_title="World Wide Monitor | Will Wright Media", page_icon="📡", layout="wide")

# CUSTOM CSS - DARK EDITORIAL THEME WITH HIGH-CONTRAST WHITE INPUT FIELDS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    /* Global Dark Background & Default Typography */
    .stApp {
        background-color: #111111 !important;
        color: #e5e5e0 !important;
        font-family: 'Inter', sans-serif !important;
    }
    
    /* Sidebar Dark Styling */
    [data-testid="stSidebar"] {
        background-color: #161616 !important;
        border-right: 1px solid #262626 !important;
    }
    [data-testid="stSidebar"] * {
        color: #d4d4d0 !important;
    }

    /* Editorial Brand Header Banner */
    .brand-header {
        background-color: #161616;
        border: 1px solid #262626;
        padding: 36px 40px;
        border-radius: 4px;
        margin-bottom: 32px;
    }
    .brand-tagline {
        font-family: 'Inter', sans-serif;
        font-size: 0.75rem;
        letter-spacing: 0.25em;
        text-transform: uppercase;
        color: #a3a3a0;
        margin-bottom: 12px;
    }
    .brand-title {
        font-family: 'Cormorant Garamond', serif;
        font-size: 2.8rem;
        font-weight: 400;
        color: #ffffff;
        margin: 0;
        line-height: 1.1;
    }
    .brand-subtitle {
        font-family: 'Cormorant Garamond', serif;
        font-size: 1.35rem;
        font-style: italic;
        color: #d4d4d0;
        margin-top: 8px;
    }

    /* =========================================================
       COMPREHENSIVE WHITE INPUT FIELDS FIX
       Targeting all text inputs, password fields, wrappers, & placeholders
       ========================================================= */
    
    /* Input Container & Outer Wrappers */
    div[data-baseweb="input"], 
    div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 4px !important;
    }

    /* Inner Input Element (Typed text) */
    div[data-baseweb="input"] input, 
    div[data-baseweb="base-input"] input {
        background-color: #ffffff !important;
        color: #111827 !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
    }

    /* Input Placeholder Text (Dark Charcoal for High Contrast) */
    div[data-baseweb="input"] input::placeholder, 
    div[data-baseweb="base-input"] input::placeholder {
        color: #6b7280 !important;
        opacity: 1 !important;
    }

    /* Password Eye Icon Button Wrapper */
    div[data-baseweb="input"] button {
        background-color: #ffffff !important;
        color: #374151 !important;
    }

    /* Select Dropdowns & Multiselect Field Contrast */
    div[data-baseweb="select"] * {
        color: #111827 !important;
    }

    /* Focus Highlight */
    div[data-baseweb="input"]:focus-within, 
    div[data-baseweb="select"]:focus-within {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2) !important;
    }

    /* Radio Label Typography */
    div[data-testid="stRadio"] label p {
        color: #e5e5e0 !important;
        font-weight: 500 !important;
    }

    /* Primary Outline Buttons (Matching 'START A CONVERSATION') */
    .stButton>button {
        background-color: transparent !important;
        color: #e5e5e0 !important;
        border: 1px solid #444444 !important;
        border-radius: 2px !important;
        padding: 0.75rem 1.8rem !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important;
        letter-spacing: 0.18em !important;
        text-transform: uppercase !important;
        transition: all 0.25s ease !important;
    }
    .stButton>button:hover {
        border-color: #ffffff !important;
        color: #ffffff !important;
        background-color: #1f1f1f !important;
    }

    /* Prominent Raised Emerald Green Download Buttons */
    .stDownloadButton>button {
        background-color: #10b981 !important;
        color: #ffffff !important;
        font-family: 'Inter', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        letter-spacing: 0.08em !important;
        text-transform: uppercase !important;
        padding: 0.8rem 1.8rem !important;
        border-radius: 2px !important;
        border: none !important;
        box-shadow: 0 4px 14px rgba(16, 185, 129, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stDownloadButton>button:hover {
        background-color: #059669 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(16, 185, 129, 0.45) !important;
    }

    /* Executive Report Card Containers */
    .report-card {
        background-color: #161616;
        border: 1px solid #262626;
        padding: 36px;
        border-radius: 4px;
    }
    
    /* Expander Container Styling */
    .streamlit-expanderHeader {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border-radius: 2px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("### WILL WRIGHT MEDIA")
    st.caption("STRATEGIC COMMUNICATIONS · MEDIA INTELLIGENCE")
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

    st.divider()
    st.subheader("Account Ledger")
    if "tokens" not in st.session_state:
        st.session_state.tokens = 1000
    st.metric("Token Balance", f"{st.session_state.tokens} WWM")
    if st.button("Top Up Credits (+500 WWM)"):
        st.session_state.tokens += 500
        st.rerun()

# --- BRANDED TOP HEADER BANNER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-tagline">WORLD WIDE MONITOR · EXECUTIVE INTELLIGENCE</div>
        <div class="brand-title">Great work doesn't speak for itself.</div>
        <div class="brand-subtitle">Actionable, high-margin media intelligence derived from public releases and global coverage.</div>
    </div>
""", unsafe_allow_html=True)

# --- PYDANTIC SCHEMA ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher or media house name (e.g., Washington Post, Reuters, ABC News).")
    author_byline: str = Field(description="Journalist or producer byline. Use 'Official Announcement' if uncredited.")
    publication_date: str = Field(description="Date published (e.g., Aug 23, 2024).")
    source_url: str = Field(description="Direct URL to article or official release.")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Clear executive title summarizing the story event.")
    source_category: str = Field(description="Categorize as: 'Global Media', 'Australian Media', 'Wire Service', or 'Official Primary Release'.")
    core_event_summary: str = Field(description="Fact-only summary stripping out promotional fluff, highlighting milestones, figures, and commitments.")
    covering_outlets: list[CoverageOutlet] = Field(description="De-duplicated list of all outlets that covered this story.")

class WWMOnePageBrief(BaseModel):
    headline_synthesis: str = Field(description="One-sentence executive synthesis of overall coverage.")
    reputational_value_read: str = Field(description="Strategic analysis of institutional positioning and media sentiment.")
    so_what_action: str = Field(description="Direct, actionable recommendations for executive leadership.")
    items: list[EventCoverageItem]

def generate_markdown_brief(brief, query):
    md = f"# CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF\n"
    md += f"**Target Strategy Query:** `{query}`\n\n"
    md += f"## Executive Summary & Strategic Takeaway\n"
    md += f"**Overview:** {brief['headline_synthesis']}\n\n"
    md += f"**Strategic Imperatives:** {brief['so_what_action']}\n\n"
    md += f"**Positioning & Risk Analysis:** {brief['reputational_value_read']}\n\n"
    md += f"---\n\n"
    md += f"## Verified Coverage & Media Records\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']}\n"
        md += f"- **Summary:** {item['core_event_summary']}\n"
        md += f"- **Media Outlets & Bylines:**\n"
        for outlet in item["covering_outlets"]:
            md += f"  - **{outlet['outlet_name']}** (*Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']}) — [Source Link]({outlet['source_url']})\n"
        md += "\n"
    return md

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
    st.markdown("**Active Strategy Query:**")
    st.code(final_query, language="text")

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
if st.button("Generate Executive Brief"):
    if not final_query.strip():
        st.error("Please specify search parameters before running.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API Key in the left menu.")
    elif st.session_state.tokens < 50:
        st.error("Insufficient credit balance.")
    else:
        st.session_state.tokens -= 50
        
        with st.status("Gathering & Synthesizing Global Coverage...", expanded=True) as status:
            st.write(f"🔍 Searching coverage across `{date_window}` window...")
            
            sources_formatted = ", ".join(selected_sources) if selected_sources else "All available sources"
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""
            Today is {current_date}.
            You are the WWM Executive Fact Engine for Will Wright Media. Execute a web search for media coverage, wire pickups, and primary announcements matching:
            Strategy Query: {final_query}
            
            CRITICAL INSTRUCTIONS:
            1. SCOPE: Search across these target channels: {sources_formatted}. Include major global publications, national press, and official announcements.
            2. RECENCY: Focus on stories published within: {date_window}.
            3. PUBLISHER & BYLINE: Identify the exact Publisher Name, Journalist Byline, and Date for every record found.
            4. DE-DUPLICATION: Group coverage by core story event under 'covering_outlets'.
            5. FACTUAL PRECISION: Extract ONLY verifiable events, policy statements, figures, and dates. Strip out PR fluff.
            """
            
            try:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}],
                        response_mime_type="application/json",
                        response_schema=WWMOnePageBrief,
                        temperature=0.1,
                    )
                )
                st.session_state.current_brief = json.loads(response.text)
                st.session_state.executed_query = final_query
                status.update(label="Synthesis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Processing Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    # TOP HEADER & GREEN DOWNLOAD BUTTON
    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.caption("CONFIDENTIAL | WILL WRIGHT MEDIA INTELLIGENCE BRIEF")
        st.header("Executive Intelligence Output")
    with header_col2:
        md_content = generate_markdown_brief(brief, st.session_state.get("executed_query", ""))
        st.download_button(
            label="💚 Download Executive Brief (.md)",
            data=md_content,
            file_name="WWM_Executive_Brief.md",
            mime="text/markdown",
            key="download_top"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Executive Overview")
        st.info(brief["headline_synthesis"])
    with col2:
        st.subheader("Strategic Imperatives for Leadership")
        st.warning(brief["so_what_action"])
        
    st.subheader("Institutional Positioning & Strategic Risk")
    st.write(brief["reputational_value_read"])
    
    st.divider()
    st.subheader("Verified Coverage & Media Records")
    for item in brief["items"]:
        with st.expander(f"📌 {item['event_title']}"):
            st.markdown(f"**Channel:** `{item['source_category']}`")
            st.write(f"**Core Summary:** {item['core_event_summary']}")
            st.markdown("**Covering Outlets & Bylines:**")
            
            for outlet in item["covering_outlets"]:
                st.info(
                    f"📰 **{outlet['outlet_name']}**  |  ✍️ *Byline:* {outlet['author_byline']}  |  📅 *Date:* {outlet['publication_date']}\n\n"
                    f"🔗 [Direct Source Referral Link]({outlet['source_url']})"
                )
    
    st.divider()
    
    # BOTTOM REPEATED DOWNLOAD BUTTON
    bot_col1, bot_col2 = st.columns([2, 1])
    with bot_col1:
        st.markdown("**Ready to share or archive this brief?** Download the full formatted Markdown report.")
    with bot_col2:
        st.download_button(
            label="💚 Download Executive Brief (.md)",
            data=md_content,
            file_name="WWM_Executive_Brief.md",
            mime="text/markdown",
            key="download_bottom"
        )
            
    st.markdown("</div>", unsafe_allow_html=True)
