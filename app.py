import json
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
    .media-badge { background-color: #f3f4f6; color: #1f2937; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.title("📡 WWM Engine Control")
    st.caption("Native Gemini + Global Search Grounding")
    
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="Paste your AI Studio key here")
    
    st.divider()
    st.subheader("Search Scope Controls")
    
    # TIME HORIZON SELECTOR
    time_horizon = st.selectbox(
        "Time Range Horizon",
        ["Past 4 Years Archive (2022-2026)", "Past 12 Months", "Past 30 Days", "Breaking News (Past 7 Days)"],
        index=0
    )
    
    # MEDIA SCOPE SELECTOR
    media_scope = st.selectbox(
        "Media Geography Scope",
        ["Global Media & Official Releases (CNN, WashPost, Reuters, etc.)", "Australia Domestic Focus Only"],
        index=0
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
class EntityMention(BaseModel):
    entity_name: str = Field(description="Individual or organization mentioned")
    positioning: str = Field(description="Policy position or action taken")
    key_statement: str = Field(description="Fact-only summary of statement. Max 20 words.")

class ReleaseFactItem(BaseModel):
    source_title: str
    source_url: str
    media_outlet: str = Field(description="Publisher/Outlet name (e.g. CNN, Washington Post, Reuters, ABC News, RMIT Release).")
    author_byline: str = Field(description="Journalist or producer byline. Use 'Official Release' or 'Uncredited' if absent.")
    publication_date: str = Field(description="Approximate or exact publication date (e.g. Aug 2023).")
    core_event_summary: str = Field(description="Fact-only summary of the story.")
    entities: list[EntityMention]

class WWMOnePageBrief(BaseModel):
    headline_synthesis: str = Field(description="1-sentence synthesis of media/announcements.")
    reputational_value_read: str = Field(description="Deep reputational read.")
    so_what_action: str = Field(description="Strategic takeaway for executive leadership.")
    items: list[ReleaseFactItem]

def generate_markdown_brief(brief, query):
    md = f"# CONFIDENTIAL | WWM EXECUTIVE BRIEF\n"
    md += f"**Search Query:** `{query}`\n\n"
    md += f"## 1. Executive Intelligence Output\n"
    md += f"**Headline Read:** {brief['headline_synthesis']}\n\n"
    md += f"**The 'So What' Takeaway:** {brief['so_what_action']}\n\n"
    md += f"**Reputational Read:** {brief['reputational_value_read']}\n\n"
    md += f"---\n\n"
    md += f"## 2. Fact-Only Coverage Breakdown\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['source_title']}\n"
        md += f"- **Outlet:** {item['media_outlet']} | **Date:** {item['publication_date']}\n"
        md += f"- **Byline:** {item['author_byline']}\n"
        md += f"- **Core Event:** {item['core_event_summary']}\n"
        md += f"- **Key Entities:**\n"
        for entity in item["entities"]:
            md += f"  - **{entity['entity_name']}** ({entity['positioning']}): {entity['key_statement']}\n"
        md += f"- **Source URL:** {item['source_url']}\n\n"
    return md

# --- MAIN INTERFACE ---
st.title("World Wide Monitor")
st.subheader("Global Media Intelligence & Archival Search")

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
        not_mention = st.text_input("Must NOT mention (NOT)", placeholder="e.g., Masks Sports")
        
    query_parts = []
    
    if must_all.strip():
        all_words = " ".join([f'"{w.strip()}"' if " " in w.strip() else w.strip() for w in must_all.split(",") if w.strip()])
        query_parts.append(all_words)
        
    if any_one.strip():
        or_words = " OR ".join([f'"{w.strip()}"' if " " in w.strip() else w.strip() for w in any_one.split() if w.strip()])
        query_parts.append(f"({or_words})")
        
    if not_mention.strip():
        not_words = " ".join([f"-{w.strip()}" for w in not_mention.split() if w.strip()])
        query_parts.append(not_words)
        
    final_query = " ".join(query_parts)

else:
    st.markdown("#### Advanced Boolean Search Query")
    final_query = st.text_input(
        "Enter Raw Boolean Query", 
        value='("Coffee Biochar" OR "Sustainable Concrete") AND "RMIT"',
        placeholder='e.g., ("University Funding" OR "Accord") AND "Minister"'
    )

if final_query.strip():
    st.markdown("**Compiled Search String Sent to Gemini Swarm:**")
    st.markdown(f"<div class='query-preview'>{final_query}</div>", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
if st.button("Run Global Intelligence Search (-50 Tokens)"):
    if not final_query.strip():
        st.error("Please enter a valid search query first.")
    elif not gemini_key:
        st.error("Please paste your Gemini API Key in the left sidebar.")
    elif st.session_state.tokens < 50:
        st.error("Insufficient Tokens!")
    else:
        st.session_state.tokens -= 50
        
        with st.status("Executing Global Archival Search...", expanded=True) as status:
            st.write(f"🔍 **Gemini Search Agent:** Querying index across `{time_horizon}` scope...")
            
            # Construct geographical scope instruction
            scope_prompt = "Include major global news outlets (CNN, Washington Post, BBC, Reuters, Bloomberg, etc.) and trade press." if "Global" in media_scope else "Focus primarily on Australian domestic media and releases (.gov.au, .edu.au)."
            
            try:
                client = genai.Client(api_key=gemini_key)
                
                prompt = f"""
                You are the WWM Fact Engine. Perform a deep web search for media coverage, press releases, and news matching:
                Search Query: {final_query}
                
                SEARCH CONSTRAINTS:
                1. TIME HORIZON: Target stories and media published within: {time_horizon}. Look back across archival news if required.
                2. GEOGRAPHIC & PUBLISHER SCOPE: {scope_prompt}
                3. EXTRACTION STRICTNESS: Extract ONLY factual events, policy commitments, dates, and entity statements. Disregard PR fluff.
                4. BYLINE & PUBLISHER: You must explicitly identify the exact Media Outlet (e.g., CNN, Washington Post, ABC News) and Author Byline for each coverage item found.
                """
                
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
                status.update(label="Global Search & Fact Extraction Complete!", state="complete", expanded=False)
                
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
        with st.expander(f"📌 {item['source_title']}"):
            st.markdown(
                f"**Media Outlet:** `<span class='media-badge'>{item['media_outlet']}</span>` &nbsp;|&nbsp; "
                f"**Date:** *{item.get('publication_date', 'N/A')}* &nbsp;|&nbsp; "
                f"**Byline:** *{item['author_byline']}*", 
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)
            st.write(f"**Core Event:** {item['core_event_summary']}")
            st.markdown("**Key Entities Mentioned:**")
            for entity in item["entities"]:
                st.markdown(f"- **{entity['entity_name']}** ({entity['positioning']}): {entity['key_statement']}")
            st.markdown(f"🔗 [View Source Announcement]({item['source_url']})")
            
    st.markdown("</div>", unsafe_allow_html=True)
