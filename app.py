import json
import datetime
import io
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from docx import Document
from fpdf import FPDF

# --- UI CONFIGURATION (WILL WRIGHT MEDIA BRANDING) ---
st.set_page_config(page_title="World Wide Monitor | Will Wright Media", page_icon="📡", layout="wide")

# CUSTOM CSS - DARK EDITORIAL THEME WITH HIGH-CONTRAST WHITE INPUT FIELDS & GREEN DOWNLOAD BUTTONS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    .stApp { background-color: #111111 !important; color: #e5e5e0 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #161616 !important; border-right: 1px solid #262626 !important; }
    [data-testid="stSidebar"] * { color: #d4d4d0 !important; }

    .brand-header { background-color: #161616; border: 1px solid #262626; padding: 36px 40px; border-radius: 4px; margin-bottom: 32px; }
    .brand-tagline { font-family: 'Inter', sans-serif; font-size: 0.75rem; letter-spacing: 0.25em; text-transform: uppercase; color: #a3a3a0; margin-bottom: 12px; }
    .brand-title { font-family: 'Cormorant Garamond', serif; font-size: 2.8rem; font-weight: 400; color: #ffffff; margin: 0; line-height: 1.1; }
    .brand-subtitle { font-family: 'Cormorant Garamond', serif; font-size: 1.35rem; font-style: italic; color: #d4d4d0; margin-top: 8px; }

    /* HIGH-CONTRAST WHITE INPUT FIELDS */
    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div {
        background-color: #ffffff !important; border: 1px solid #d1d5db !important; border-radius: 4px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input {
        background-color: #ffffff !important; color: #111827 !important; font-weight: 500 !important; font-size: 0.95rem !important;
    }
    div[data-baseweb="input"] input::placeholder, div[data-baseweb="base-input"] input::placeholder {
        color: #6b7280 !important; opacity: 1 !important;
    }
    div[data-baseweb="select"] * { color: #111827 !important; }

    /* VERIFICATION BADGES */
    .badge-confirmed { background-color: #065f46; color: #34d399; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .badge-unconfirmed { background-color: #78350f; color: #fcd34d; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }

    .stButton>button {
        background-color: transparent !important; color: #e5e5e0 !important; border: 1px solid #444444 !important;
        border-radius: 2px !important; padding: 0.75rem 1.8rem !important; font-family: 'Inter', sans-serif !important;
        font-size: 0.8rem !important; letter-spacing: 0.18em !important; text-transform: uppercase !important;
    }
    .stDownloadButton>button {
        background-color: #10b981 !important; color: #ffffff !important; font-weight: 600 !important;
        padding: 0.8rem 1.8rem !important; border-radius: 2px !important; border: none !important;
    }
    .report-card { background-color: #161616; border: 1px solid #262626; padding: 36px; border-radius: 4px; }
    .disclaimer-box { background-color: #1a1a1a; border-left: 3px solid #6b7280; padding: 12px 16px; font-size: 0.82rem; color: #9ca3af; margin-top: 24px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("### WILL WRIGHT MEDIA")
    st.caption("STRATEGIC COMMUNICATIONS · MEDIA INTELLIGENCE")
    st.divider()
    
    st.subheader("1. API Configuration")
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    
    st.divider()
    st.subheader("2. Unlimited Search Horizon")
    date_window = st.selectbox(
        "Search Recency Scope",
        ["Past 7 Days (Current Cycle)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive"],
        index=0
    )

    st.divider()
    st.subheader("Account Ledger")
    if "tokens" not in st.session_state:
        st.session_state.tokens = 1000
    st.metric("Token Balance", f"{st.session_state.tokens} WWM")

# --- BRANDED HEADER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-tagline">WORLD WIDE MONITOR · EXECUTIVE INTELLIGENCE</div>
        <div class="brand-title">Great work doesn't speak for itself.</div>
        <div class="brand-subtitle">Actionable, unconstrained media intelligence derived from comprehensive web searches.</div>
    </div>
""", unsafe_allow_html=True)

# --- STRICT PYDANTIC SCHEMA ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher or media house name found in web record.")
    author_byline: str = Field(description="Explicit author byline. Write 'not stated' if missing.")
    publication_date: str = Field(description="Explicit publication date. Write 'not stated' if missing.")
    source_url: str = Field(description="Direct web URL to the retrieved source article.")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Executive title for the coverage event.")
    source_category: str = Field(description="Categorize as: 'Global Media', 'Australian Media', 'Trade / Sector Press', or 'Official Primary Release'")
    core_event_summary: str = Field(description="Fact-only summary strictly derived from source documents.")
    covering_outlets: list[CoverageOutlet]

class WWMOnePageBrief(BaseModel):
    coverage_found: bool = Field(description="Set to False if no relevant coverage was found matching query.")
    headline_synthesis: str = Field(description="1-sentence synthesis of media/announcements.")
    reputational_value_read: str = Field(description="Strategic analysis of positioning and risk (analyst interpretation).")
    so_what_action: str = Field(description="Actionable strategic recommendations for leadership.")
    items: list[EventCoverageItem]

# --- EXPORT GENERATORS ---
def generate_markdown_brief(brief, query):
    md = f"# CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF\n"
    md += f"**Target Strategy Query:** `{query}`\n\n"
    md += f"## Executive Summary & Strategic Takeaway\n"
    md += f"**Overview:** {brief['headline_synthesis']}\n\n"
    md += f"**Strategic Imperatives:** {brief['so_what_action']}\n\n"
    md += f"**Positioning & Risk Analysis:** {brief['reputational_value_read']}\n\n"
    md += f"---\n\n"
    md += f"## Unrestricted Coverage & Media Records\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']}\n"
        md += f"- **Summary:** {item['core_event_summary']}\n"
        for outlet in item["covering_outlets"]:
            md += f"  - **{outlet['outlet_name']}** (*Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']}) — [Source Link]({outlet['source_url']})\n"
        md += "\n"
    md += "\n\n*This brief was generated with AI assistance. Review and confirm source credibility via linked URLs before strategic distribution.*"
    return md

# --- SEARCH INTERFACE ---
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

# --- EXECUTION ENGINE (UNRESTRICTED OPEN WEB SEARCH) ---
if st.button("Generate Executive Brief"):
    if not final_query.strip():
        st.error("Please specify search parameters before running.")
    elif not gemini_key:
        st.error("Please enter your Gemini API Key in the left menu.")
    else:
        st.session_state.tokens -= 50
        
        with st.status("Gathering & Processing Open Web Coverage...", expanded=True) as status:
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""
            Today is {current_date}.
            You are the WWM Fact Extraction Engine.
            Execute an open web search across all news sources, official announcements, trade journals, and global press matching: {final_query}
            
            INSTRUCTIONS:
            1. Search broadly across open web media, wires, regional publications, and official portals.
            2. Extract ONLY factual events, quotes, and milestone commitments present in the retrieved web content.
            3. If a date, author, or publisher name is absent, write 'not stated'. Do NOT invent metadata values.
            4. Group coverage by core story event under 'covering_outlets'.
            5. Present 'reputational_value_read' clearly as strategic interpretation for executive leadership.
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
                        temperature=0.0,
                    )
                )
                st.session_state.current_brief = json.loads(response.text)
                st.session_state.executed_query = final_query
                status.update(label="Open Web Search & Synthesis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Processing Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.caption("CONFIDENTIAL | WILL WRIGHT MEDIA INTELLIGENCE BRIEF")
        st.header("Executive Intelligence Output")
    with header_col2:
        md_data = generate_markdown_brief(brief, st.session_state.get("executed_query", ""))
        st.download_button(
            label="💚 Download Executive Brief (.md)",
            data=md_data,
            file_name="WWM_Executive_Brief.md",
            mime="text/markdown",
            key="dl_top"
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not brief.get("coverage_found", True):
        st.warning("⚠️ No relevant coverage was returned matching your query.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Executive Overview")
            st.info(brief["headline_synthesis"])
        with col2:
            st.subheader("Strategic Imperatives for Leadership")
            st.warning(brief["so_what_action"])
            
        st.subheader("Institutional Positioning & Risk Analysis")
        st.write(brief["reputational_value_read"])
        
        st.divider()
        st.subheader("Unrestricted Coverage & Media Records")
        for item in brief["items"]:
            with st.expander(f"📌 {item['event_title']}"):
                st.markdown(f"**Channel:** `{item['source_category']}`")
                st.write(f"**Core Summary:** {item['core_event_summary']}")
                st.markdown("**Covering Outlets & Source Referral Links:**")
                
                for outlet in item["covering_outlets"]:
                    st.markdown(
                        f"📰 **{outlet['outlet_name']}** | ✍️ *Byline:* {outlet['author_byline']} | 📅 *Date:* {outlet['publication_date']}<br>"
                        f"🔗 <a href='{outlet['source_url']}' target='_blank'>Review Source Link & Audit Credibility</a>",
                        unsafe_allow_html=True
                    )
    
    # DISCLAIMER NOTE
    st.markdown("""
        <div class="disclaimer-box">
            <b>Analyst Verification Note:</b> This brief captures open web coverage across global and regional outlets. All records link directly to original source URLs so analysts can audit publisher credibility and confirm details prior to client distribution.
        </div>
    """, unsafe_allow_html=True)
            
    st.markdown("</div>", unsafe_allow_html=True)
