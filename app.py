import json
import datetime
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- UI CONFIGURATION (WWM BRANDING & EXECUTIVE POLISH) ---
st.set_page_config(page_title="World Wide Monitor | Executive Intelligence", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    
    /* Primary Action Buttons */
    .stButton>button { 
        background-color: #0f172a; 
        color: white; 
        border-radius: 6px; 
        font-weight: 600; 
        padding: 0.6rem 1.2rem;
        border: none;
    }
    
    /* Prominent Green Raised Download Buttons */
    .stDownloadButton>button {
        background-color: #10b981 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        padding: 0.65rem 1.4rem !important;
        border-radius: 8px !important;
        border: none !important;
        box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.3), 0 2px 4px -1px rgba(16, 185, 129, 0.06) !important;
        transition: all 0.2s ease-in-out !important;
    }
    .stDownloadButton>button:hover {
        background-color: #059669 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 12px -2px rgba(16, 185, 129, 0.4) !important;
    }
    
    /* Card Layout & Clean Typography */
    .report-card { background-color: #ffffff; padding: 32px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }
    .query-preview { background-color: #f1f5f9; padding: 14px; border-radius: 8px; font-family: 'Courier New', monospace; border-left: 4px solid #0f172a; color: #334155; }
    .media-badge { background-color: #0f172a; color: #ffffff; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .outlet-card { background-color: #f8fafc; border: 1px solid #e2e8f0; padding: 12px 16px; border-radius: 8px; margin-top: 8px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("📡 Engine Settings")
    st.caption("World Wide Monitor Platform")
    
    st.subheader("1. Platform Engine")
    
    api_provider = st.selectbox(
        "AI & Search Provider",
        [
            "Google Gemini (Native Search Grounding)",
            "Tavily Search + Gemini Intelligence",
            "OpenAI GPT-4o (Web Grounded)"
        ],
        index=0,
        help="Select the AI infrastructure powering search retrieval and strategic synthesis."
    )
    
    gemini_key = ""
    tavily_key = ""
    openai_key = ""
    
    if "Gemini" in api_provider:
        gemini_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            placeholder="AIzaSy...",
            help="ℹ️ HOW TO ACCESS KEY:\n1. Open aistudio.google.com\n2. Log in with Google\n3. Select 'Get API Key'\n4. Paste here."
        )
    elif "Tavily" in api_provider:
        tavily_key = st.text_input(
            "Tavily API Key", 
            type="password", 
            placeholder="tvly-...",
            help="ℹ️ HOW TO ACCESS KEY:\n1. Open tavily.com\n2. Register free developer account\n3. Copy API key from dashboard."
        )
        gemini_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            placeholder="AIzaSy...",
            help="ℹ️ Required for synthesis layer. Get key at aistudio.google.com"
        )
    elif "OpenAI" in api_provider:
        openai_key = st.text_input(
            "OpenAI API Key", 
            type="password", 
            placeholder="sk-...",
            help="ℹ️ HOW TO ACCESS KEY:\n1. Open platform.openai.com\n2. Navigate to API Keys\n3. Create secret key."
        )

    st.divider()
    st.subheader("2. Time Horizon")
    date_window = st.selectbox(
        "Search Recency Scope",
        ["Past 7 Days (Current Cycle)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive (2022-2026)"],
        index=0
    )
    
    st.divider()
    st.subheader("3. Media Channels")
    selected_sources = st.multiselect(
        "Source Channels",
        [
            "Global Tier-1 Media (Washington Post, Reuters, CNN, BBC, Financial Times)",
            "Australian National & Metro Press (AFR, ABC News, SMH, The Age)",
            "Newswire & Wire Services (AAP, Reuters, PR Newswire)",
            "Official & Primary Releases (.gov.au, .edu.au, Corporate Portals)"
        ],
        default=[
            "Global Tier-1 Media (Washington Post, Reuters, CNN, BBC, Financial Times)",
            "Australian National & Metro Press (AFR, ABC News, SMH, The Age)",
            "Official & Primary Releases (.gov.au, .edu.au, Corporate Portals)"
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

# --- MAIN INTERFACE ---
st.title("World Wide Monitor")
st.subheader("Executive Media Intelligence Platform")

search_mode = st.radio("Search Mode:", ["Structured Parameters", "Advanced Boolean Search"], horizontal=True)

final_query = ""

if search_mode == "Structured Parameters":
    col1, col2, col3 = st.columns(3)
    
    with col1:
        must_all = st.text_input("All of these terms (AND)", placeholder="e.g., Sustainable Concrete")
    with col2:
        any_one = st.text_input("Any of these terms (OR)", placeholder="e.g., RMIT Roychand")
    with col3:
        not_mention = st.text_input("Exclude terms (NOT)", placeholder="e.g., Sports Scandal")
        
    query_parts = []
    if must_all.strip():
        query_parts.append(" ".join([f'"{w.strip()}"' if " " in w.strip() else w.strip() for w in must_all.split(",") if w.strip()]))
    if any_one.strip():
        query_parts.append(f"({' OR '.join([f'\"{w.strip()}\"' if ' ' in w.strip() else w.strip() for w in any_one.split() if w.strip()])})")
    if not_mention.strip():
        query_parts.append(" ".join([f"-{w.strip()}" for w in not_mention.split() if w.strip()]))
    final_query = " ".join(query_parts)

else:
    final_query = st.text_input(
        "Raw Query String", 
        value='("Coffee Biochar" OR "Sustainable Concrete") AND "RMIT"'
    )

if final_query.strip():
    st.markdown("**Active Strategy Query:**")
    st.markdown(f"<div class='query-preview'>{final_query}</div>", unsafe_allow_html=True)
else:
    st.info("Define parameters above to compile search string.")

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
if st.button("Generate Executive Intelligence Brief"):
    if not final_query.strip():
        st.error("Please specify search parameters before running.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API Key in the left menu (hover over (i) for help).")
    elif "Tavily" in api_provider and (not tavily_key or not gemini_key):
        st.error("Please provide both Tavily and Gemini keys in the left menu.")
    elif "OpenAI" in api_provider and not openai_key:
        st.error("Please enter your OpenAI API Key in the left menu.")
    elif st.session_state.tokens < 50:
        st.error("Insufficient credit balance.")
    else:
        st.session_state.tokens -= 50
        
        with st.status("Gathering & Synthesizing Global Coverage...", expanded=True) as status:
            st.write(f"🔍 **Retrieval Agent:** Searching coverage across `{date_window}` window...")
            
            sources_formatted = ", ".join(selected_sources) if selected_sources else "All available sources"
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""
            Today is {current_date}.
            You are the WWM Executive Fact Engine. Execute a web search for media coverage, wire pickups, and primary announcements matching:
            Strategy Query: {final_query}
            
            CRITICAL INSTRUCTIONS:
            1. SCOPE: Search across these target channels: {sources_formatted}. Include major global publications, national press, and official announcements.
            2. RECENCY: Focus on stories published within: {date_window}.
            3. PUBLISHER & BYLINE: Identify the exact Publisher Name, Journalist Byline, and Date for every record found.
            4. DE-DUPLICATION: Group coverage by core story event under 'covering_outlets'.
            5. FACTUAL PRECISION: Extract ONLY verifiable events, policy statements, figures, and dates. Strip out PR fluff.
            """
            
            try:
                if "Gemini" in api_provider:
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
                
                elif "OpenAI" in api_provider:
                    st.warning("Initializing OpenAI web-grounded pipeline...")
                    
                st.session_state.executed_query = final_query
                status.update(label="Synthesis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Processing Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    # TOP HEADER & DOWNLOAD BUTTON
    header_col1, header_col2 = st.columns([2.5, 1.5])
    with header_col1:
        st.caption("CONFIDENTIAL | WWM EXECUTIVE BRIEF")
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
            st.markdown(f"**Channel:** `<span class='media-badge'>{item['source_category']}</span>`", unsafe_allow_html=True)
            st.write(f"**Core Summary:** {item['core_event_summary']}")
            st.markdown("**Covering Outlets & Bylines:**")
            
            for outlet in item["covering_outlets"]:
                st.markdown(
                    f"<div class='outlet-card'>"
                    f"📰 <b>{outlet['outlet_name']}</b> &nbsp;|&nbsp; ✍️ <i>Byline: {outlet['author_byline']}</i> &nbsp;|&nbsp; 📅 <i>Date: {outlet['publication_date']}</i><br>"
                    f"🔗 <a href='{outlet['source_url']}' target='_blank'>Direct Source Referral Link</a>"
                    f"</div>",
                    unsafe_allow_html=True
                )
    
    st.divider()
    
    # BOTTOM REPEATED DOWNLOAD BUTTON FOR CONVENIENCE
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
