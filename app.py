import json
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# --- UI CONFIGURATION (WWM BRANDING) ---
st.set_page_config(page_title="World Wide Monitor | Native Gemini Sandbox", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { background-color: #111827; color: white; border-radius: 4px; font-weight: bold; }
    .report-card { background-color: white; padding: 24px; border-radius: 8px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .query-preview { background-color: #e0f2fe; padding: 12px; border-radius: 6px; font-family: monospace; border-left: 4px solid #0284c7; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: CONTROL PANEL ---
with st.sidebar:
    st.title("📡 WWM Engine Control")
    st.caption("Native Gemini + Google Search Grounding")
    
    gemini_key = st.text_input("Gemini API Key", type="password", placeholder="Paste your AI Studio key here")
    
    st.divider()
    st.subheader("Account Tokens")
    if "tokens" not in st.session_state:
        st.session_state.tokens = 1000
    st.metric("Token Balance", f"{st.session_state.tokens} WWM")
    if st.button("Top Up (+500 Tokens)"):
        st.session_state.tokens += 500
        st.rerun()

# --- PYDANTIC SCHEMA: STRICT FACT EXTRACTION ---
class EntityMention(BaseModel):
    entity_name: str = Field(description="Individual or organization mentioned")
    positioning: str = Field(description="Policy position or action taken")
    key_statement: str = Field(description="Fact-only summary of the statement. Max 20 words.")

class ReleaseFactItem(BaseModel):
    source_title: str
    source_url: str
    core_event_summary: str = Field(description="Fact-only summary of the news item.")
    entities: list[EntityMention]

class WWMOnePageBrief(BaseModel):
    headline_synthesis: str = Field(description="1-sentence synthesis of media/announcements today.")
    reputational_value_read: str = Field(description="Deep reputational read.")
    so_what_action: str = Field(description="Strategic takeaway for executive leadership.")
    items: list[ReleaseFactItem]

# --- SEARCH ENGINE INTERFACE ---
st.title("World Wide Monitor")
st.subheader("Targeted Media Intelligence Search")

# Search Mode Selector
search_mode = st.radio("Search Interface Mode:", ["Structured Fields", "Advanced Boolean Mode"], horizontal=True)

final_query = ""

if search_mode == "Structured Fields":
    st.markdown("#### Structured Search Parameters")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        must_all = st.text_input("All of these words (AND)", placeholder="e.g., University Funding Policy")
    with col2:
        any_one = st.text_input("At least one of these words (OR)", placeholder="e.g., RMIT Unimelb Monash")
    with col3:
        not_mention = st.text_input("Must NOT mention (NOT)", placeholder="e.g., Sports Scandal")
        
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
        value='("Higher Education" OR "Research Grant") AND "RMIT"',
        placeholder='e.g., ("University Funding" OR "Accord") AND "Minister"'
    )

if final_query.strip():
    st.markdown("**Compiled Search String Sent to Gemini Swarm:**")
    st.markdown(f"<div class='query-preview'>{final_query}</div>", unsafe_allow_html=True)
else:
    st.info("Enter search criteria above to compile your query.")

st.markdown("<br>", unsafe_allow_html=True)

# --- SWARM EXECUTION ENGINE ---
if st.button("Run Intelligence Search (-50 Tokens)"):
    if not final_query.strip():
        st.error("Please enter a valid search query first.")
    elif not gemini_key:
        st.error("Please paste your Gemini API Key in the left sidebar.")
    elif st.session_state.tokens < 50:
        st.error("Insufficient Tokens!")
    else:
        st.session_state.tokens -= 50
        
        with st.status("Deploying Gemini Agent Swarm with Native Google Search...", expanded=True) as status:
            st.write("🔍 **Gemini Search Agent:** Searching live Australian media and extracting structured facts...")
            
            try:
                client = genai.Client(api_key=gemini_key)
                
                prompt = f"""
                You are the WWM Fact Engine. Perform a web search for current public media, press releases, and news regarding:
                Search Query: {final_query} Australia
                
                CRITICAL INSTRUCTIONS:
                1. Focus search primarily on Australian public media releases (.gov.au, .edu.au) and major news.
                2. Extract ONLY factual events, policy commitments, entity statements, and dates.
                3. Disregard PR fluff and promotional narrative.
                """
                
                # Gemini handles search and structured output natively
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}],  # Native Google Search Tool
                        response_mime_type="application/json",
                        response_schema=WWMOnePageBrief,
                        temperature=0.1,
                    )
                )
                
                st.session_state.current_brief = json.loads(response.text)
                status.update(label="Search & Fact Extraction Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Execution Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    st.caption("CONFIDENTIAL | WWM EXECUTIVE BRIEF")
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
    st.subheader("Fact-Only Coverage Breakdown")
    for item in brief["items"]:
        with st.expander(f"📌 {item['source_title']}"):
            st.write(f"**Core Event:** {item['core_event_summary']}")
            st.markdown("**Key Entities Mentioned:**")
            for entity in item["entities"]:
                st.markdown(f"- **{entity['entity_name']}** ({entity['positioning']}): {entity['key_statement']}")
            st.markdown(f"🔗 [View Source Announcement]({item['source_url']})")
            
    st.markdown("</div>", unsafe_allow_html=True)
