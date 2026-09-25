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
st.set_page_config(page_title="World Wide Monitor | Executive Intelligence", page_icon="📡", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    .stApp { background-color: #111111 !important; color: #e5e5e0 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #161616 !important; border-right: 1px solid #262626 !important; }
    [data-testid="stSidebar"] * { color: #d4d4d0 !important; }

    .brand-header { background-color: #161616; border: 1px solid #262626; padding: 36px 40px; border-radius: 4px; margin-bottom: 32px; }
    .brand-tagline { font-family: 'Inter', sans-serif; font-size: 0.75rem; letter-spacing: 0.25em; text-transform: uppercase; color: #a3a3a0; margin-bottom: 12px; }
    .brand-title { font-family: 'Cormorant Garamond', serif; font-size: 2.8rem; font-weight: 400; color: #ffffff; margin: 0; line-height: 1.1; }
    .brand-subtitle { font-family: 'Cormorant Garamond', serif; font-size: 1.2rem; font-style: italic; color: #d4d4d0; margin-top: 8px; }

    /* HIGH-CONTRAST WHITE INPUT FIELDS */
    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
        background-color: #ffffff !important; border: 1px solid #d1d5db !important; border-radius: 4px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input, div[data-baseweb="textarea"] textarea {
        background-color: #ffffff !important; color: #111827 !important; font-weight: 500 !important; font-size: 0.95rem !important;
    }
    div[data-baseweb="input"] input::placeholder, div[data-baseweb="textarea"] textarea::placeholder {
        color: #6b7280 !important; opacity: 1 !important;
    }
    div[data-baseweb="select"] * { color: #111827 !important; }

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
    .disclaimer-box { background-color: #1a1a1a; border-left: 3px solid #10b981; padding: 12px 16px; font-size: 0.82rem; color: #9ca3af; margin-top: 24px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE PERSISTENT SESSION STATE ---
if "cumulative_brief" not in st.session_state:
    st.session_state.cumulative_brief = None
if "executed_query" not in st.session_state:
    st.session_state.executed_query = ""

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("### WILL WRIGHT MEDIA")
    st.caption("STRATEGIC COMMUNICATIONS · MEDIA INTELLIGENCE")
    st.divider()
    
    st.subheader("1. Intelligence Engine")
    api_provider = st.selectbox(
        "AI Engine Provider",
        [
            "Google Gemini 3 (Native Search Grounding)",
            "OpenAI GPT-4o (Web Grounded)",
            "Tavily Search + Gemini Intelligence"
        ],
        index=0
    )
    
    gemini_key = ""
    openai_key = ""
    tavily_key = ""
    
    if "Gemini" in api_provider or "Tavily" in api_provider:
        gemini_key = st.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
    if "OpenAI" in api_provider:
        openai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
    if "Tavily" in api_provider:
        tavily_key = st.text_input("Tavily API Key", type="password", placeholder="tvly-...")

    st.divider()
    st.subheader("2. Language & Delivery")
    output_language = st.selectbox(
        "Report Output Language",
        [
            "English", "French (Français)", "Spanish (Español)", "German (Deutsch)", 
            "Mandarin Chinese (中文)", "Japanese (日本語)", "Indonesian (Bahasa Indonesia)", 
            "Vietnamese (Tiếng Việt)", "Hindi (हिंदी)", "Arabic (العربية)"
        ],
        index=0
    )
    
    st.divider()
    st.subheader("3. Time Scope & Outlets")
    date_window = st.selectbox(
        "Recency Window",
        ["Past 7 Days (Current Cycle)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive"],
        index=3
    )
    
    selected_sources = st.multiselect(
        "Target Channels",
        [
            "Global Tier-1 & Wires (Reuters, AP, WashPost, NYT, CNN, BBC, TIME, Forbes)",
            "Australian Press (AFR, ABC News, SMH, The Age, news.com.au)",
            "Southeast Asia Press (Kompas, VNExpress, Jakarta Post)",
            "Indian & South Asian Press (The Hindu, Times of India, Dainik Jagran)",
            "Official Releases (.gov.au, .edu.au, Corporate Newsrooms, ASX)"
        ],
        default=[
            "Global Tier-1 & Wires (Reuters, AP, WashPost, NYT, CNN, BBC, TIME, Forbes)",
            "Australian Press (AFR, ABC News, SMH, The Age, news.com.au)",
            "Official Releases (.gov.au, .edu.au, Corporate Newsrooms, ASX)"
        ]
    )

    st.divider()
    if st.button("Reset & Clear Brief Buffer"):
        st.session_state.cumulative_brief = None
        st.session_state.executed_query = ""
        st.rerun()

# --- BRANDED EXECUTIVE HEADER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-tagline">WORLD WIDE MONITOR · EXECUTIVE MEDIA INTELLIGENCE</div>
        <div class="brand-title">Great work doesn't speak for itself.</div>
        <div class="brand-subtitle">Executive media intelligence and strategic analysis for government, university, and corporate leadership.</div>
    </div>
""", unsafe_allow_html=True)

# --- STRICT SCHEMA FOR EXECUTIVE READ ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher or newsroom name verbatim from source.")
    author_byline: str = Field(description="Author byline verbatim. Write 'not stated' if absent.")
    publication_date: str = Field(description="Publication date verbatim. Write 'not stated' if absent.")
    original_language: str = Field(description="Original publication language.")
    canonical_source_url: str = Field(description="Direct, clean resolving canonical URL. Never return dead redirects.")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Factual headline describing the coverage event.")
    source_category: str = Field(description="Categorize as: 'Global Tier-1', 'National Media', 'Industry Press', or 'Official Primary Release'")
    core_event_summary: str = Field(description="Copyright-compliant summary restricted to lead paragraphs and 20-word context windows around keywords.")
    covering_outlets: list[CoverageOutlet]

class WWMExecutiveAnalysisBrief(BaseModel):
    coverage_found: bool = Field(description="Set to False if no verified coverage matched query or provided URLs.")
    verified_coverage_metric: str = Field(description="Factual count of retrieved media items (e.g. 'Media Index: 8 primary tier-1 and national records analyzed across time window').")
    headline_synthesis: str = Field(description="1-2 sentence executive overview of overall coverage trajectory.")
    sentiment_framing_read: str = Field(description="1-2 concise lines evaluating framing. Note if addressing difficult sector topics reflects positively on expert authority.")
    subject_quoted_vs_reported: str = Field(description="Concise summary of direct subject quotes vs. what external outlets reported about them.")
    engagement_opportunities: str = Field(description="Strategic commentary identifying public, media, and sector channels for further engagement and impact.")
    items: list[EventCoverageItem]

# --- EXPORT GENERATORS ---
def generate_markdown_brief(brief, query, lang):
    md = f"# CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF ({lang.upper()})\n"
    md += f"**Scope:** `{query}`\n"
    md += f"**Coverage Index:** {brief.get('verified_coverage_metric', 'Verified Scope')}\n\n"
    md += f"## 1. Executive Summary\n"
    md += f"**Overview:** {brief['headline_synthesis']}\n\n"
    md += f"**Sentiment & Media Representation:** {brief['sentiment_framing_read']}\n\n"
    md += f"**Direct Quotes & External Commentary:** {brief['subject_quoted_vs_reported']}\n\n"
    md += f"**Strategic Engagement Opportunities:** {brief['engagement_opportunities']}\n\n"
    md += f"---\n\n"
    md += f"## 2. Key Media Records\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']}\n"
        md += f"- **Summary:** {item['core_event_summary']}\n"
        for outlet in item["covering_outlets"]:
            md += f"  - **{outlet['outlet_name']}** (*Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']} | *Lang:* {outlet['original_language']}) — [Source Link]({outlet['canonical_source_url']})\n"
        md += "\n"
    md += f"\n\n*Copyright Protocol: Extracted under 20-word window bounds. Synthesized into {lang}. Confirm details against canonical source URLs prior to distribution.*"
    return md

def generate_docx_brief(brief, query, lang):
    doc = Document()
    doc.add_heading(f"CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF ({lang.upper()})", level=0)
    doc.add_paragraph(f"Scope: {query}")
    doc.add_paragraph(f"Coverage Index: {brief.get('verified_coverage_metric', 'Verified Scope')}")
    
    doc.add_heading("1. Executive Summary", level=1)
    doc.add_paragraph(f"Overview: {brief['headline_synthesis']}")
    doc.add_paragraph(f"Sentiment & Media Representation: {brief['sentiment_framing_read']}")
    doc.add_paragraph(f"Direct Quotes & External Commentary: {brief['subject_quoted_vs_reported']}")
    doc.add_paragraph(f"Strategic Engagement Opportunities: {brief['engagement_opportunities']}")
    
    doc.add_heading("2. Key Media Records", level=1)
    for item in brief["items"]:
        doc.add_heading(f"📌 {item['event_title']}", level=2)
        doc.add_paragraph(f"Category: {item['source_category']}")
        doc.add_paragraph(f"Summary: {item['core_event_summary']}")
        for outlet in item["covering_outlets"]:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{outlet['outlet_name']} ").bold = True
            p.add_run(f"(Byline: {outlet['author_byline']} | Date: {outlet['publication_date']} | Lang: {outlet['original_language']}) - {outlet['canonical_source_url']}")
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(120, 120, 120)
        self.set_y(10)
        self.cell(0, 5, 'CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF', align='R')

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def clean_pdf_text(text):
    if not text:
        return ""
    replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-', '•': '*'}
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_brief(brief, query, lang):
    pdf = PDFReport()
    margin = 15
    pdf.set_margins(margin, 22, margin)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    epw = pdf.epw
    
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_x(margin)
    pdf.cell(epw, 10, clean_pdf_text(f'Executive Intelligence Brief ({lang})'), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_x(margin)
    pdf.cell(epw, 6, clean_pdf_text(f'Scope: {query} | {brief.get("verified_coverage_metric", "")}'), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '1. Executive Overview', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('headline_synthesis', '')))
    pdf.ln(3)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '2. Sentiment & Media Representation', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('sentiment_framing_read', '')))
    pdf.ln(3)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '3. Direct Quotes & External Commentary', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('subject_quoted_vs_reported', '')))
    pdf.ln(3)

    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '4. Strategic Engagement Opportunities', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('engagement_opportunities', '')))
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '5. Key Media Records', new_x="LMARGIN", new_y="NEXT")
    
    for item in brief.get("items", []):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 5, clean_pdf_text(f"* {item.get('event_title', '')}"))
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 5, clean_pdf_text(f"Summary: {item.get('core_event_summary', '')}"))
        
        for outlet in item.get('covering_outlets', []):
            outlet_line = f"  - Outlet: {outlet.get('outlet_name', '')} | Byline: {outlet.get('author_byline', '')} | Date: {outlet.get('publication_date', '')}"
            pdf.set_x(margin)
            pdf.multi_cell(epw, 5, clean_pdf_text(outlet_line))
            
        pdf.ln(3)
        
    return bytes(pdf.output())

# --- DUAL INGESTION TABS ---
tab_search, tab_custom_urls = st.tabs(["🔍 Pass 1: Global Media Search", "🔗 Pass 2: Additive URL Ingestion (Up to 100 Links)"])

search_query_input = ""
custom_urls_input = []

with tab_search:
    col1, col2, col3 = st.columns(3)
    with col1:
        must_all = st.text_input("Must include (AND)", placeholder="e.g., Rajeev Roychand RMIT")
    with col2:
        any_one = st.text_input("Any of these (OR)", placeholder="e.g., Coffee Concrete Biochar")
    with col3:
        not_mention = st.text_input("Exclude (NOT)", placeholder="e.g., Sports")
        
    query_parts = []
    if must_all.strip():
        query_parts.append(" ".join([f'"{w.strip()}"' if " " in w.strip() else w.strip() for w in must_all.split(",") if w.strip()]))
    if any_one.strip():
        query_parts.append(f"({' OR '.join([f'\"{w.strip()}\"' if ' ' in w.strip() else w.strip() for w in any_one.split() if w.strip()])})")
    if not_mention.strip():
        query_parts.append(" ".join([f"-{w.strip()}" for w in not_mention.split() if w.strip()]))
    search_query_input = " ".join(query_parts)

with tab_custom_urls:
    st.markdown("##### Additive Bulk URL Ingestion")
    st.caption("Paste additional article links below (up to 100 URLs, one per line). WWM will ingest these documents and merge them directly into the current executive brief.")
    raw_urls_text = st.text_area(
        "Paste Article URLs:", 
        height=140, 
        placeholder="https://www.theguardian.com/science/2023/aug/23/full-of-beans-scientists-use-processed-coffee-grounds-to-make-stronger-concrete\nhttps://www.rmit.edu.au/news/all-news/2023/aug/coffee-concrete"
    )
    custom_urls_input = [line.strip() for line in raw_urls_text.split("\n") if line.strip().startswith("http")]

if search_query_input:
    st.session_state.executed_query = search_query_input

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
btn_label = "Generate Executive Brief" if st.session_state.cumulative_brief is None else "Update & Expand Executive Brief (Additive Ingestion)"

if st.button(btn_label):
    if not search_query_input and not custom_urls_input and not st.session_state.executed_query:
        st.error("Please enter a search query or paste article URLs.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    else:
        with st.status("Synthesizing Executive Intelligence...", expanded=True) as status:
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            existing_brief_context = ""
            if st.session_state.cumulative_brief:
                existing_brief_context = f"""
                EXISTING REPORT BUFFER:
                - Headline Synthesis: {st.session_state.cumulative_brief.get('headline_synthesis', '')}
                - Current Items Analyzed: {len(st.session_state.cumulative_brief.get('items', []))}
                INSTRUCTION: Merge the new search results or custom URLs with this existing intelligence. Do NOT discard prior valid coverage cards.
                """
            
            urls_formatted = "\n".join([f"- {u}" for u in custom_urls_input[:100]]) if custom_urls_input else "None provided."
            active_q = search_query_input if search_query_input else st.session_state.executed_query
            
            prompt = f"""
            Today is {current_date}.
            You are WWM's Senior Strategic Intelligence Analyst preparing a brief for government, university, and institutional leadership.
            
            REPORT OUTPUT LANGUAGE: Synthesize the entire executive brief in {output_language}.
            
            SCOPE:
            - Active Query: {active_q}
            - Custom Additive URLs ({len(custom_urls_input)} provided): {urls_formatted}
            
            {existing_brief_context}
            
            HIGH-VOLUME QUERY MANAGEMENT:
            Count the exact number of verified items analyzed in this payload and state it factually in 'verified_coverage_metric' (e.g. "Media Index: 6 primary tier-1 and national media items analyzed").
            Do NOT output dozens of repetitive cards. Present ONLY the top 5 to 8 most influential items across Global Tier-1 Mastheads, National Press, Industry Trade Media, and Official Primary Releases.
            
            COPYRIGHT & FAIR USE PROTOCOL:
            Consume and extract ONLY headlines, bylines, dates, lead paragraphs (paras 1-2), and 20-word keyword context snippets.
            
            STRATEGIC ANALYSIS INSTRUCTIONS:
            1. sentiment_framing_read: Evaluate sentiment. Recognize expert authority: if a subject addresses challenging or negative sector topics (e.g., waste crisis or clinical risk), frame this POSITIVELY as subject-matter expertise.
            2. subject_quoted_vs_reported: Summarize direct subject quotes vs. external commentary.
            3. engagement_opportunities: Identify prospective channels, unaddressed sector topics, and outreach targets.
            """
            
            try:
                client = genai.Client(api_key=gemini_key)
                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{"google_search": {}}],
                        response_mime_type="application/json",
                        response_schema=WWMExecutiveAnalysisBrief,
                        temperature=0.0,
                    )
                )
                st.session_state.cumulative_brief = json.loads(response.text)
                status.update(label="Executive Synthesis Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Processing Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if st.session_state.cumulative_brief:
    brief = st.session_state.cumulative_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    header_col1, header_col2 = st.columns([2, 2])
    with header_col1:
        st.caption("CONFIDENTIAL | WILL WRIGHT MEDIA INTELLIGENCE BRIEF")
        st.header(f"Executive Brief ({output_language})")
        if brief.get("verified_coverage_metric"):
            st.caption(f"📊 **Coverage Scope:** {brief['verified_coverage_metric']}")
    
    with header_col2:
        export_format = st.selectbox(
            "Export Document Format:",
            ["PDF Document (.pdf)", "Microsoft Word (.docx)", "Markdown (.md)"],
            key="export_format_top"
        )
        exec_query = st.session_state.get("executed_query", "Executive Media Intelligence Scope")
        
        if "PDF" in export_format:
            st.download_button("💚 Download PDF Report", generate_pdf_brief(brief, exec_query, output_language), f"WWM_Executive_Brief_{output_language}.pdf", "application/pdf", key="dl_pdf_top")
        elif "Word" in export_format:
            st.download_button("💚 Download Word Document", generate_docx_brief(brief, exec_query, output_language), f"WWM_Executive_Brief_{output_language}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx_top")
        else:
            st.download_button("💚 Download Markdown File", generate_markdown_brief(brief, exec_query, output_language), f"WWM_Executive_Brief_{output_language}.md", "text/markdown", key="dl_md_top")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not brief.get("coverage_found", True):
        st.warning("⚠️ **Limited Verified Coverage:** No high-confidence media records matched your criteria. Unverified claims have been suppressed to preserve factual integrity.")
    else:
        st.subheader("1. Executive Summary")
        st.info(brief["headline_synthesis"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("2. Sentiment & Representation Read")
            st.write(brief["sentiment_framing_read"])
            
            st.subheader("3. Direct Quotes vs. External Commentary")
            st.write(brief["subject_quoted_vs_reported"])
        with col2:
            st.subheader("4. Strategic Engagement Opportunities")
            st.warning(brief["engagement_opportunities"])
            
        st.divider()
        st.subheader("5. Key Media Records")
        for item in brief["items"]:
            with expander_title := st.expander(f"📌 {item['event_title']}"):
                st.markdown(f"**Category:** `{item['source_category']}`")
                st.write(f"**Summary:** {item['core_event_summary']}")
                st.markdown("**Covering Outlets & Source Links:**")
                
                for outlet in item["covering_outlets"]:
                    st.markdown(
                        f"📰 **{outlet['outlet_name']}** | ✍️ *Byline:* {outlet['author_byline']} | 📅 *Date:* {outlet['publication_date']} | 🌐 *Language:* {outlet['original_language']}<br>"
                        f"🔗 <a href='{outlet['canonical_source_url']}' target='_blank'>Review Original Canonical Source Link</a>",
                        unsafe_allow_html=True
                    )
    
    st.markdown(f"""
        <div class="disclaimer-box">
            <b>Executive Verification Note:</b> WWM extracts lead paragraphs and 20-word keyword context windows to comply with international fair-use copyright guidelines. Output language set to <b>{output_language}</b>. Always confirm critical details against canonical source URLs prior to executive distribution.
        </div>
    """, unsafe_allow_html=True)
            
    st.markdown("</div>", unsafe_allow_html=True)
