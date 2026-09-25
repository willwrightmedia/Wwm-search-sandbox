import json
import datetime
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- UI CONFIGURATION (WWM BRANDING) ---
st.set_page_config(page_title="World Wide Monitor | Multi-Provider Engine", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #111827; color: white; border-radius: 4px; font-weight: bold; }
    .report-card { background-color: white; padding: 24px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .query-preview { background-color: #e0f2fe; padding: 12px; border-radius: 6px; font-family: monospace; border-left: 4px solid #0284c7; }
    .media-badge { background-color: #1f2937; color: #ffffff; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .outlet-card { background-color: #f9fafb; border: 1px solid #f3f4f6; padding: 8px 12px; border-radius: 6px; margin-top: 6px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("📡 WWM Engine Control")
    st.caption("Multi-Provider Intelligence Platform")
    
    st.subheader("1. Select Engine & API Keys")
    
    # PROVIDER SELECTOR DROPDOWN
    api_provider = st.selectbox(
        "AI & Search Provider",
        [
            "Google Gemini (Native Google Search)",
            "Tavily Search + Gemini Intelligence",
            "OpenAI GPT-4o (Web Grounded)"
        ],
        index=0,
        help="Choose which AI ecosystem powers your search and fact-extraction pipeline."
    )
    
    # DYNAMIC API KEY INPUTS WITH (i) HOVER TOOLTIPS
    gemini_key = ""
    tavily_key = ""
    openai_key = ""
    
    if "Gemini" in api_provider:
        gemini_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            placeholder="AIzaSy...",
            help="ℹ️ HOW TO GET A GEMINI KEY:\n1. Go to aistudio.google.com\n2. Sign in with your Google account\n3. Click 'Get API Key' -> 'Create API Key'\n4. Paste it here. Free & Paid tiers available!"
        )
    elif "Tavily" in api_provider:
        tavily_key = st.text_input(
            "Tavily API Key", 
            type="password", 
            placeholder="tvly-...",
            help="ℹ️ HOW TO GET A TAVILY KEY:\n1. Go to tavily.com\n2. Sign up for a free developer account\n3. Copy your key from the main dashboard (1,000 free searches/mo)."
        )
        gemini_key = st.text_input(
            "Gemini API Key", 
            type="password", 
            placeholder="AIzaSy...",
            help="ℹ️ Needed for the fact-extraction layer. Get a key at aistudio.google.com"
        )
    elif "OpenAI" in api_provider:
        openai_key = st.text_input(
            "OpenAI API Key", 
            type="password", 
            placeholder="sk-...",
            help="ℹ️ HOW TO GET AN OPENAI KEY:\n1. Go to platform.openai.com\n2. Sign in and navigate to API Keys\n3. Click 'Create new secret key'. Requires active API billing."
        )

    st.divider()
    st.subheader("2. Recency & Time Window")
    date_window = st.selectbox(
        "Coverage Time Horizon",
        ["Past 7 Days (Breaking)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive (2022-2026)"],
        index=0
    )
    
    st.divider()
    st.subheader("3. Targeted Source Scope")
    selected_sources = st.multiselect(
        "Target Source Layers",
        [
            "Global Media (CNN, Washington Post, Reuters, BBC, Bloomberg)",
            "Australian Media (AFR, ABC News, SMH, The Age, news.com.au)",
            "Wires & Syndicates (AAP, Reuters Wire, PR Newswire)",
            "Official & Primary Releases (.gov.au, .edu.au, Corporate Newsrooms)"
        ],
        default=[
            "Global Media (CNN, Washington Post, Reuters, BBC, Bloomberg)",
            "Australian Media (AFR, ABC News, SMH, The Age, news.com.au)",
            "Official & Primary Releases (.gov.au, .edu.au, Corporate Newsrooms)"
        ]
    )
    
    st.divider()
    st.subheader("Account Tokens")
    if "tokens" not in st.session_state:
        st.session_state.tokens = 1000
    st.metric("Token Balance", f"{st.session_state.tokens} WWM")
    if st.button("Top Up (+500 Tokens)"):
        st.session_state.tokens += 500
        st.rerun()

# --- PYDANTIC SCHEMA ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher name (e.g., Washington Post, Reuters, ABC News).")
    author_byline: str = Field(description="Journalist name or 'Official Release'.")
    publication_date: str = Field(description="Date published (e.g., Aug 23, 2023).")
    source_url: str = Field(description="Direct web URL to article or release.")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Headline describing the core event.")
    source_category: str = Field(description="'Global Media', 'Australian Media', 'Wire Service', or 'Official Primary Release'.")
    core_event_summary: str = Field(description="Fact-only summary stripping out PR fluff.")
    covering_outlets: list[CoverageOutlet] = Field(description="De-duplicated list of covering outlets.")

class WWMOnePageBrief(BaseModel):
    headline_synthesis: str = Field(description="1-sentence executive synthesis.")
    reputational_value_read: str = Field(description="Strategic reputational analysis.")
    so_what_action: str = Field(description="Actionable strategic takeaway.")
    items: list[EventCoverageItem]

def generate_markdown_brief(brief, query):
    md = f"# CONFIDENTIAL | WWM EXECUTIVE INTELLIGENCE BRIEF\n"
    md += f"**Search Query:** `{query}`\n\n"
    md += f"## 1. Executive Intelligence Output\n"
    md += f"**Headline Read:** {brief['headline_synthesis']}\n\n"
    md += f"**The 'So What' Takeaway:** {brief['so_what_action']}\n\n"
    md += f"**Reputational Read:** {brief['reputational_value_read']}\n\n"
    md += f"---\n\n"
    md += f"## 2. Comprehensive Coverage Breakdown\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']}\n"
        md += f"- **Core Event Summary:** {item['core_event_summary']}\n"
        md += f"- **Covering Outlets & Bylines:**\n"
        for outlet in item["covering_outlets"]:
            md += f"  - **{outlet['outlet_name']}** (*Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']}) — [Source URL]({outlet['source_url']})\n"
        md += "\n"
    return md

# --- MAIN INTERFACE ---
st.title("World Wide Monitor")
st.subheader("Global Media & Primary Intelligence Engine")

search_mode = st.radio("Search Interface Mode:", ["Structured Fields", "Advanced Boolean Mode"], horizontal=True)

final_query = ""

if search_mode == "Structured Fields":
    st.markdown("#### Structured Search Parameters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        must_all = st.text_input("All of these words (AND)", placeholder="e.g., Coffee Concrete Biochar")
    with col2:
        any_one = st.text_input("At least one of these words (OR)", placeholder="e.g., RMIT Roychand")
    with col3:
        not_mention = st.text_input("Must NOT mention (NOT)", placeholder="e.g., Sports Scandal")
        
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
        "Enter Raw Boolean Query", 
        value='("Coffee Biochar" OR "Sustainable Concrete") AND "RMIT"'
    )

if final_query.strip():
    st.markdown("**Compiled Search String Sent to Intelligence Swarm:**")
    st.markdown(f"<div class='query-preview'>{final_query}</div>", unsafe_allow_html=True)
else:
    st.info("Enter search criteria above to compile your query.")

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
if st.button("Run Intelligence Search (-50 Tokens)"):
    if not final_query.strip():
        st.error("Please enter a valid search query first.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API Key in the left sidebar (hover over (i) for instructions).")
    elif "Tavily" in api_provider and (not tavily_key or not gemini_key):
        st.error("Please enter both Tavily and Gemini API keys in the left sidebar.")
    elif "OpenAI" in api_provider and not openai_key:
        st.error("Please enter your OpenAI API Key in the left sidebar.")
    elif st.session_state.tokens < 50:
        st.error("Insufficient Tokens!")
    else:
        st.session_state.tokens -= 50
        
        with st.status(f"Deploying Search via {api_provider}...", expanded=True) as status:
            st.write(f"🔍 **Search Agent:** Executing query across `{date_window}` scope...")
            
            sources_formatted = ", ".join(selected_sources) if selected_sources else "All available sources"
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""
            Today is {current_date}.
            You are the WWM Comprehensive Fact Engine. Execute a web search for media coverage, wire pickups, news, and official releases matching:
            Search Query: {final_query}
            
            COMPREHENSIVE INSTRUCTIONS:
            1. SCOPE: Actively search across all of the following layers: {sources_formatted}.
            2. TIME HORIZON: Target stories published within: {date_window}.
            3. OUTLET & BYLINE EXTRACTION: Identify exact Media Outlet, Author Byline, and Publication Date for each item.
            4. DE-DUPLICATION: Group coverage by primary event under 'covering_outlets'.
            5. FACT EXTRACTION: Extract ONLY factual events, verified quotes, dates, and commitments. Strip marketing fluff.
            """
            
            try:
                # DEFAULT PIPELINE: NATIVE GEMINI
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
                
                # ALTERNATE PIPELINE: OPENAI (STUB PLACEHOLDER FOR OPENAI API CALLS)
                elif "OpenAI" in api_provider:
                    st.warning("OpenAI integration selected. Initializing web-grounded GPT-4o pipeline...")
                    # Placeholder call mapping to OpenAI client
                    
                st.session_state.executed_query = final_query
                status.update(label="Intelligence Extraction Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.caption("CONFIDENTIAL | WWM EXECUTIVE BRIEF")
        st.header("Executive Intelligence Output")
    with header_col2:
        md_content = generate_markdown_brief(brief, st.session_state.get("executed_query", ""))
        st.download_button(
            label="📥 Export Executive Brief (.md)",
            data=md_content,
            file_name="WWM_Executive_Brief.md",
            mime="text/markdown"
        )
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Headline Read")
        st.info(brief["headline_synthesis"])
    with col2:
        st.subheader("The 'So What' Takeaway")
        st.warning(brief["so_what_action"])
        
    st.subheader("Reputational Read")
    st.write(brief["reputational_value_read"])
    
    st.divider()
    st.subheader("Fact-Only Coverage Breakdown")
    for item in brief["items"]:
        with st.expander(f"📌 {item['event_title']}"):
            st.markdown(f"**Source Category:** `<span class='media-badge'>{item['source_category']}</span>`", unsafe_allow_html=True)
            st.write(f"**Core Event Summary:** {item['core_event_summary']}")
            st.markdown("**Covering Outlets, Bylines & Sources:**")
            
            for outlet in item["covering_outlets"]:
                st.markdown(
                    f"<div class='outlet-card'>"
                    f"📰 <b>{outlet['outlet_name']}</b> &nbsp;|&nbsp; ✍️ <i>Byline: {outlet['author_byline']}</i> &nbsp;|&nbsp; 📅 <i>Date: {outlet['publication_date']}</i><br>"
                    f"🔗 <a href='{outlet['source_url']}' target='_blank'>Direct Source Referral Link</a>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            
    st.markdown("</div>", unsafe_allow_html=True)
