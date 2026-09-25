import json
import datetime
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- UI CONFIGURATION ---
st.set_page_config(page_title="World Wide Monitor | Executive Intelligence", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #111827; color: white; border-radius: 4px; font-weight: bold; }
    .report-card { background-color: white; padding: 24px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .query-preview { background-color: #e0f2fe; padding: 12px; border-radius: 6px; font-family: monospace; border-left: 4px solid #0284c7; }
    .type-primary { background-color: #dbeafe; color: #1e40af; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    .type-secondary { background-color: #f3f4f6; color: #374151; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("📡 WWM Engine Control")
    st.caption("Native Gemini + Multi-Layer Grounding")
    
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="Paste AI Studio key here")
    
    st.divider()
    st.subheader("1. Time Horizon Filter")
    date_window = st.selectbox(
        "Coverage Recency Window",
        ["Past 7 Days (Breaking)", "Past 30 Days", "Past 12 Months", "4-Year Archive (2022-2026)"],
        index=0
    )
    
    st.divider()
    st.subheader("2. Source Layer Toggles")
    layer_global = st.checkbox("Global Media (CNN, WashPost, Reuters)", value=True)
    layer_aus = st.checkbox("Australian Media (ABC, AFR, SMH, Age)", value=True)
    layer_official = st.checkbox("Official & Primary (.gov.au, .edu.au, Releases)", value=True)
    
    st.divider()
    st.subheader("Account Tokens")
    if "tokens" not in st.session_state:
        st.session_state.tokens = 1000
    st.metric("Token Balance", f"{st.session_state.tokens} WWM")
    if st.button("Top Up (+500 Tokens)"):
        st.session_state.tokens += 500
        st.rerun()

# --- PYDANTIC SCHEMA WITH DE-DUPLICATION & SOURCE TYPES ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Name of media publisher or official site")
    byline: str = Field(description="Journalist name or 'Official Release'")
    source_url: str = Field(description="Direct URL to article/release")
    publication_date: str = Field(description="Date published (e.g., Sep 24, 2026)")

class CollapsedEventItem(BaseModel):
    event_title: str = Field(description="Core headline/event title")
    source_type: str = Field(description="'Primary Source / Official' OR 'Secondary Media Coverage'")
    core_event_summary: str = Field(description="Fact-only summary of the story.")
    outlets_and_syndication: list[CoverageOutlet] = Field(description="List of all unique outlets covering this single event")

class WWMOnePageBrief(BaseModel):
    headline_synthesis: str = Field(description="1-sentence executive synthesis.")
    reputational_value_read: str = Field(description="Strategic reputational analysis.")
    so_what_action: str = Field(description="Actionable takeaway for C-suite leadership.")
    items: list[CollapsedEventItem]

# --- MAIN INTERFACE ---
st.title("World Wide Monitor")
st.subheader("Multi-Source Executive Media Search")

search_mode = st.radio("Search Interface Mode:", ["Structured Fields", "Advanced Boolean Mode"], horizontal=True)

final_query = ""

if search_mode == "Structured Fields":
    col1, col2, col3 = st.columns(3)
    with col1:
        must_all = st.text_input("All of these words (AND)", placeholder="e.g., Coffee Concrete")
    with col2:
        any_one = st.text_input("At least one of these words (OR)", placeholder="e.g., RMIT Roychand")
    with col3:
        not_mention = st.text_input("Must NOT mention (NOT)", placeholder="e.g., Sports")
        
    query_parts = []
    if must_all.strip():
        query_parts.append(" ".join([f'"{w.strip()}"' if " " in w.strip() else w.strip() for w in must_all.split(",") if w.strip()]))
    if any_one.strip():
        query_parts.append(f"({' OR '.join([f'\"{w.strip()}\"' if ' ' in w.strip() else w.strip() for w in any_one.split() if w.strip()])})")
    if not_mention.strip():
        query_parts.append(" ".join([f"-{w.strip()}" for w in not_mention.split() if w.strip()]))
    final_query = " ".join(query_parts)

else:
    final_query = st.text_input("Enter Raw Boolean Query", value='("Coffee Biochar" OR "Sustainable Concrete") AND "RMIT"')

if final_query.strip():
    st.markdown("**Compiled Query Execution:**")
    st.markdown(f"<div class='query-preview'>{final_query}</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
if st.button("Run Multi-Layer Intelligence Search (-50 Tokens)"):
    if not final_query.strip():
        st.error("Please enter a search query.")
    elif not gemini_key:
        st.error("Please paste your Gemini API Key in the sidebar.")
    else:
        st.session_state.tokens -= 50
        
        with st.status("Deploying Multi-Layer Search Engine...", expanded=True) as status:
            # Build domain & target constraints
            layers = []
            if layer_official:
                layers.append("Official/Primary sources (.gov.au, .edu.au, official press portals)")
            if layer_aus:
                layers.append("Australian domestic news outlets (ABC, AFR, SMH, The Age)")
            if layer_global:
                layers.append("Global international media (Reuters, Washington Post, CNN, BBC)")
                
            layers_text = ", ".join(layers) if layers else "General Web"
            current_date_str = datetime.datetime.now().strftime("%B %d, %Y")
            
            prompt = f"""
            Today is {current_date_str}.
            You are the WWM Fact Engine. Perform a web search for media and press announcements matching:
            Search Query: {final_query}
            
            STRICT CONSTRAINTS:
            1. TIME WINDOW: Filter strictly for stories published within: {date_window}. Reject stories outside this date range unless explicitly looking at archival.
            2. SOURCE LAYERS: Prioritize results from these targeted source sets: {layers_text}.
            3. DE-DUPLICATION: If multiple newsrooms or releases cover the exact same announcement, COLLAPSE them into a single event card and list all covering outlets under 'outlets_and_syndication'.
            4. FACT-ONLY EXTRACTION: Strip out PR adjectives and fluff. Focus on dates, names, policy/commercial commitments, and real-world deployments.
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
                status.update(label="Multi-Layer Extraction Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    st.caption("CONFIDENTIAL | WWM MULTI-LAYER EXECUTIVE BRIEF")
    st.header("Executive Intelligence Output")
    
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
    st.subheader("De-Duplicated Event & Coverage Breakdown")
    
    for item in brief["items"]:
        badge_class = "type-primary" if "Primary" in item["source_type"] else "type-secondary"
        with st.expander(f"📌 {item['event_title']}"):
            st.markdown(f"**Source Class:** `<span class='{badge_class}'>{item['source_type']}</span>`", unsafe_allow_html=True)
            st.write(f"**Core Event:** {item['core_event_summary']}")
            
            st.markdown("**Covering Outlets & Syndication:**")
            for outlet in item["outlets_and_syndication"]:
                st.markdown(f"- **{outlet['outlet_name']}** (*Byline: {outlet['byline']}* | *Date: {outlet['publication_date']}*) — [View Source]({outlet['source_url']})")
                
    st.markdown("</div>", unsafe_allow_html=True)
