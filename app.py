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
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("### WILL WRIGHT MEDIA")
    st.caption("STRATEGIC COMMUNICATIONS · MEDIA INTELLIGENCE")
    st.divider()
    
    st.subheader("1. AI & Search Engine Provider")
    api_provider = st.selectbox(
        "Select Provider",
        [
            "Google Gemini (Native Google Grounding)",
            "OpenAI GPT-4o (Web Grounded)",
            "Tavily Search + Gemini Intelligence"
        ],
        index=0,
        help="Select which AI infrastructure powers search grounding and synthesis."
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
    st.subheader("2. Multi-Language Intelligence")
    enable_translation = st.checkbox(
        "Translate Query to Global Languages (ID, VI, Indian Langs, FR, ES, DE, ZH, JA, AR)", 
        value=True,
        help="Includes Indonesian, Vietnamese, Hindi, Tamil, Telugu, Bengali, French, Spanish, German, Mandarin, Japanese, and Arabic."
    )
    
    st.divider()
    st.subheader("3. Search Parameters")
    date_window = st.selectbox(
        "Time Horizon",
        ["Past 7 Days (Current Cycle)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive"],
        index=0
    )
    
    selected_sources = st.multiselect(
        "Target Channels & Geographic Focus",
        [
            "Global Tier-1 & Wires (Reuters, AP, AFP, WashPost, NYT, CNN, BBC, TIME, Forbes)",
            "Australian Press (AFR, ABC News, SMH, The Age, news.com.au)",
            "Southeast Asia Media (Indonesian, Vietnamese, Singaporean, Thai Press)",
            "Indian & South Asian Media (Hindi, Tamil, Telugu, Bengali, English Outlets)",
            "East Asia & Pacific Media (Nikkei, SCMP, Xinhua, Yomiuri)",
            "EMEA & Middle East Press (Al Jazeera, Financial Times, Le Monde, Deutsche Welle)",
            "Americas & LatAm Press (El País, Folha, Clarín, Globe & Mail)",
            "Official Releases (.gov.au, .edu.au, Corporate Portals)"
        ],
        default=[
            "Global Tier-1 & Wires (Reuters, AP, AFP, WashPost, NYT, CNN, BBC, TIME, Forbes)",
            "Australian Press (AFR, ABC News, SMH, The Age, news.com.au)",
            "Southeast Asia Media (Indonesian, Vietnamese, Singaporean, Thai Press)",
            "Indian & South Asian Media (Hindi, Tamil, Telugu, Bengali, English Outlets)",
            "Official Releases (.gov.au, .edu.au, Corporate Portals)"
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

# --- BRANDED HEADER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-tagline">WORLD WIDE MONITOR · EXECUTIVE INTELLIGENCE</div>
        <div class="brand-title">Great work doesn't speak for itself.</div>
        <div class="brand-subtitle">Cross-lingual, multi-engine executive media search across global web coverage.</div>
    </div>
""", unsafe_allow_html=True)

# --- PYDANTIC SCHEMA ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher name found in web record.")
    author_byline: str = Field(description="Explicit author byline. Write 'not stated' if missing.")
    publication_date: str = Field(description="Explicit publication date. Write 'not stated' if missing.")
    original_language: str = Field(description="Original publication language (e.g., English, Indonesian, Vietnamese, Hindi, Tamil, French, Mandarin, etc.).")
    source_url: str = Field(description="Direct web URL to the retrieved source article.")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Executive title for the coverage event.")
    source_category: str = Field(description="Categorize as: 'Global Media', 'Australian Media', 'Southeast Asian Press', 'Indian & South Asian Press', 'EMEA Press', 'Americas Press', or 'Official Primary Release'")
    core_event_summary: str = Field(description="Fact-only English summary translated from source documents.")
    covering_outlets: list[CoverageOutlet]

class WWMOnePageBrief(BaseModel):
    coverage_found: bool = Field(description="Set to False if no relevant coverage was found matching query.")
    headline_synthesis: str = Field(description="1-sentence English synthesis of global media/announcements.")
    reputational_value_read: str = Field(description="Strategic analysis of positioning and risk for executive leadership.")
    so_what_action: str = Field(description="Actionable strategic recommendations for leadership.")
    items: list[EventCoverageItem]

# --- EXPORT GENERATORS: MARKDOWN, WORD (.DOCX), AND PDF ---
def generate_markdown_brief(brief, query):
    md = f"# CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF\n"
    md += f"**Target Strategy Query:** `{query}`\n\n"
    md += f"## Executive Summary & Strategic Takeaway\n"
    md += f"**Overview:** {brief['headline_synthesis']}\n\n"
    md += f"**Strategic Imperatives:** {brief['so_what_action']}\n\n"
    md += f"**Positioning & Risk Analysis:** {brief['reputational_value_read']}\n\n"
    md += f"---\n\n"
    md += f"## Verified Coverage & Media Records (Cross-Lingual Capture)\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']}\n"
        md += f"- **Summary:** {item['core_event_summary']}\n"
        for outlet in item["covering_outlets"]:
            md += f"  - **{outlet['outlet_name']}** (*Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']} | *Lang:* {outlet['original_language']}) — [Source Link]({outlet['source_url']})\n"
        md += "\n"
    md += "\n\n*This brief was generated with AI assistance. Non-English coverage was translated to English for executive review. Confirm credibility via linked URLs.*"
    return md

def generate_docx_brief(brief, query):
    doc = Document()
    doc.add_heading("CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF", level=0)
    doc.add_paragraph(f"Target Strategy Query: {query}")
    
    doc.add_heading("1. Executive Summary & Strategic Takeaway", level=1)
    doc.add_paragraph(f"Overview: {brief['headline_synthesis']}")
    doc.add_paragraph(f"Strategic Imperatives: {brief['so_what_action']}")
    doc.add_paragraph(f"Positioning & Risk Analysis: {brief['reputational_value_read']}")
    
    doc.add_heading("2. Verified Coverage & Media Records", level=1)
    for item in brief["items"]:
        doc.add_heading(f"📌 {item['event_title']}", level=2)
        doc.add_paragraph(f"Channel: {item['source_category']}")
        doc.add_paragraph(f"Summary: {item['core_event_summary']}")
        
        doc.add_paragraph("Covering Outlets & Bylines:")
        for outlet in item["covering_outlets"]:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{outlet['outlet_name']} ").bold = True
            p.add_run(f"(Byline: {outlet['author_byline']} | Date: {outlet['publication_date']} | Lang: {outlet['original_language']}) - {outlet['source_url']}")
            
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
    replacements = {
        '“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-', '•': '*',
        '…': '...', '™': 'TM', '®': '(R)', '©': '(C)'
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')

def generate_pdf_brief(brief, query):
    pdf = PDFReport()
    margin = 15
    pdf.set_margins(margin, 22, margin)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    epw = pdf.epw
    
    pdf.set_font('Helvetica', 'B', 16)
    pdf.set_x(margin)
    pdf.cell(epw, 10, 'Executive Intelligence Brief', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', 'I', 10)
    pdf.set_x(margin)
    pdf.cell(epw, 6, clean_pdf_text(f'Target Query: {query}'), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '1. Executive Overview', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('headline_synthesis', '')))
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '2. Strategic Imperatives for Leadership', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('so_what_action', '')))
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '3. Institutional Positioning & Risk', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', 10)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 5, clean_pdf_text(brief.get('reputational_value_read', '')))
    pdf.ln(4)
    
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_x(margin)
    pdf.cell(epw, 8, '4. Verified Coverage Records', new_x="LMARGIN", new_y="NEXT")
    
    for item in brief.get("items", []):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 5, clean_pdf_text(f"* {item.get('event_title', '')}"))
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 5, clean_pdf_text(f"Summary: {item.get('core_event_summary', '')}"))
        
        for outlet in item.get('covering_outlets', []):
            outlet_line = f"  - Outlet: {outlet.get('outlet_name', '')} | Byline: {outlet.get('author_byline', '')} | Date: {outlet.get('publication_date', '')} | Lang: {outlet.get('original_language', 'English')}"
            pdf.set_x(margin)
            pdf.multi_cell(epw, 5, clean_pdf_text(outlet_line))
            
        pdf.ln(3)
        
    return bytes(pdf.output())

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

# --- EXECUTION ENGINE ---
if st.button("Generate Executive Brief"):
    if not final_query.strip():
        st.error("Please specify search parameters before running.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API Key in the left menu.")
    elif "OpenAI" in api_provider and not openai_key:
        st.error("Please enter your OpenAI API Key in the left menu.")
    elif "Tavily" in api_provider and (not tavily_key or not gemini_key):
        st.error("Please enter both Tavily and Gemini keys in the left menu.")
    else:
        st.session_state.tokens -= 50
        
        with st.status(f"Gathering Global Coverage via {api_provider}...", expanded=True) as status:
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            sources_formatted = ", ".join(selected_sources) if selected_sources else "Global press, wires, and official portals"
            
            translation_instruction = ""
            if enable_translation:
                translation_instruction = """
                MULTI-LANGUAGE INSTRUCTION:
                1. Translate key search concepts into: Indonesian (Bahasa Indonesia), Vietnamese (Tiếng Việt), Indian languages (Hindi, Tamil, Telugu, Bengali), French, Spanish, German, Mandarin Chinese, Japanese, and Arabic.
                2. Search both English and native-language regional media outlets (e.g. Kompas, Tempo, VNExpress, Tuổi Trẻ, Dainik Jagran, Anandabazar Patrika, The Hindu, Times of India, Nikkei, Le Monde, El País, Al Jazeera).
                3. Translate all non-English source content into clear English for the executive report while preserving exact original metadata and setting 'original_language' (e.g., 'Indonesian', 'Vietnamese', 'Hindi', 'Tamil').
                """
            
            prompt = f"""
            Today is {current_date}.
            You are the WWM Multi-Lingual Fact Extraction Engine for Will Wright Media.
            Execute an OPEN WEB SEARCH across global news outlets, news wires, trade journals, and primary releases matching: {final_query}
            
            {translation_instruction}
            
            GLOBAL DIRECTORY REFERENCE (ACTIVELY CHECK ACROSS ALL REGIONAL MASTHEADS):
            - GLOBAL WIRES & TIERS: Reuters, AP, AFP, Bloomberg, FT, WSJ, NYT, WashPost, CNN, BBC, TIME, Forbes, EurekAlert!.
            - AUSTRALIAN & PACIFIC: AFR, ABC News, The Age, SMH, The Australian, SBS News, news.com.au, Architecture & Design, Inner City News.
            - SOUTHEAST ASIA: Kompas, Tempo, Jakarta Post, Antara News (Indonesia), VNExpress, Tuổi Trẻ, Thanh Niên (Vietnam), Straits Times, Bangkok Post.
            - INDIA & SOUTH ASIA: The Hindu, Times of India, Indian Express, Dainik Jagran (Hindi), Anandabazar Patrika (Bengali), Dinamalar (Tamil), Sakshi (Telugu), Mint, Economic Times.
            - EAST ASIA: Nikkei Asia, Yomiuri Shimbun (Japan), South China Morning Post (SCMP), Xinhua, People's Daily (China).
            - EMEA & MIDDLE EAST: Al Jazeera, Le Monde, Deutsche Welle, El País, Sky News.
            - AMERICAS & LATAM: Globe and Mail, Folha de S.Paulo, Clarín, NBC News.
            - OFFICIAL & PRIMARY: .gov.au, .edu.au, .gov, .edu, university newsrooms (e.g. rmit.edu.au), ASX/SEC corporate announcements.
            
            INSTRUCTIONS:
            1. SCOPE: Search across targeted channels: {sources_formatted}. Capture relevant open web news or releases in English AND foreign languages.
            2. RECENCY: Target coverage published within: {date_window}.
            3. FACTUAL PRECISION: Extract ONLY verifiable events, policy commitments, figures, and dates explicitly present in web records.
            4. OUTPUT LANGUAGE: Write the entire executive brief in clear English. Translate foreign coverage into English and indicate the source's 'original_language'.
            5. DE-DUPLICATION: Group coverage by core story event under 'covering_outlets'.
            """
            
            try:
                if "Gemini" in api_provider or "Tavily" in api_provider:
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
                elif "OpenAI" in api_provider:
                    st.info("Initializing OpenAI web-grounded execution layer...")
                    
                st.session_state.executed_query = final_query
                status.update(label="Global Cross-Lingual Search Complete!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"Processing Error: {str(e)}")

# --- DELIVERABLE RENDER ---
if "current_brief" in st.session_state:
    brief = st.session_state.current_brief
    st.markdown("---")
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    # TOP HEADER & MULTI-FORMAT DOWNLOAD SELECTOR
    header_col1, header_col2 = st.columns([2, 2])
    with header_col1:
        st.caption("CONFIDENTIAL | WILL WRIGHT MEDIA INTELLIGENCE BRIEF")
        st.header("Executive Intelligence Output")
    
    with header_col2:
        export_format = st.selectbox(
            "Export Document Format:",
            ["PDF Document (.pdf)", "Microsoft Word (.docx)", "Markdown (.md)"],
            key="export_format_top"
        )
        
        exec_query = st.session_state.get("executed_query", "")
        
        if "PDF" in export_format:
            pdf_data = generate_pdf_brief(brief, exec_query)
            st.download_button(
                label="💚 Download PDF Report",
                data=pdf_data,
                file_name="WWM_Executive_Brief.pdf",
                mime="application/pdf",
                key="dl_pdf_top"
            )
        elif "Word" in export_format:
            docx_data = generate_docx_brief(brief, exec_query)
            st.download_button(
                label="💚 Download Word Document",
                data=docx_data,
                file_name="WWM_Executive_Brief.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_docx_top"
            )
        else:
            md_data = generate_markdown_brief(brief, exec_query)
            st.download_button(
                label="💚 Download Markdown File",
                data=md_data,
                file_name="WWM_Executive_Brief.md",
                mime="text/markdown",
                key="dl_md_top"
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
        st.subheader("Verified Coverage & Media Records (Cross-Lingual Capture)")
        for item in brief["items"]:
            with st.expander(f"📌 {item['event_title']}"):
                st.markdown(f"**Channel:** `{item['source_category']}`")
                st.write(f"**Core Summary:** {item['core_event_summary']}")
                st.markdown("**Covering Outlets & Source Referral Links:**")
                
                for outlet in item["covering_outlets"]:
                    st.markdown(
                        f"📰 **{outlet['outlet_name']}** | ✍️ *Byline:* {outlet['author_byline']} | 📅 *Date:* {outlet['publication_date']} | 🌐 *Language:* {outlet['original_language']}<br>"
                        f"🔗 <a href='{outlet['source_url']}' target='_blank'>Review Source Link & Audit Credibility</a>",
                        unsafe_allow_html=True
                    )
    
    st.divider()
    
    # BOTTOM REPEATED DOWNLOAD BUTTON
    bot_col1, bot_col2 = st.columns([2, 1])
    with bot_col1:
        st.markdown("**Ready to share or archive this brief?** Select format above and download.")
    with bot_col2:
        if "PDF" in export_format:
            st.download_button(
                label="💚 Download PDF Report",
                data=generate_pdf_brief(brief, exec_query),
                file_name="WWM_Executive_Brief.pdf",
                mime="application/pdf",
                key="dl_pdf_bot"
            )
        elif "Word" in export_format:
            st.download_button(
                label="💚 Download Word Document",
                data=generate_docx_brief(brief, exec_query),
                file_name="WWM_Executive_Brief.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key="dl_docx_bot"
            )
        else:
            st.download_button(
                label="💚 Download Markdown File",
                data=generate_markdown_brief(brief, exec_query),
                file_name="WWM_Executive_Brief.md",
                mime="text/markdown",
                key="dl_md_bot"
            )
            
    st.markdown("</div>", unsafe_allow_html=True)
