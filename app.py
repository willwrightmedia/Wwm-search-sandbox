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
    .notice-box { background-color: #1a1a1a; border-left: 3px solid #3b82f6; padding: 10px 14px; font-size: 0.8rem; color: #d1d5db; margin-bottom: 16px; }
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
    st.subheader("2. Report Scope & Target Audience")
    report_format_tier = st.selectbox(
        "Select Report Type",
        [
            "Executive Leadership Brief (1 Page PDF — C-Suite & Board)",
            "Strategic Advisory Report (2 Pages PDF — Subject Experts)",
            "Comprehensive Media Operations Report (Up to 4 Pages — PR & Media Teams)",
            "Social Media Intelligence Digest (Up to 2 Pages — Digital & Engagement Teams)"
        ],
        index=0,
        help="Tailors report depth, formatting, and page target to your audience."
    )

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
    st.subheader("3. Media Channels & Social Focus")
    social_media_focus = st.selectbox(
        "Social Media Scope",
        [
            "Include News & Social Media Combined",
            "Focus Exclusively on Social Media Channels",
            "Focus Exclusively on News & Broadcast Press"
        ],
        index=0
    )

    date_window = st.selectbox(
        "Recency Scope",
        ["Past 7 Days (Current Cycle)", "Past 30 Days", "Past 12 Months", "Past 4 Years Archive"],
        index=3
    )
    
    selected_sources = st.multiselect(
        "Target Channels",
        [
            "Global Tier-1 & Wires (Reuters, AP, WashPost, NYT, CNN, BBC, TIME, Forbes)",
            "Australian Press (AFR, ABC News, SMH, The Age, news.com.au)",
            "Social Media Platforms (LinkedIn, X/Twitter, YouTube, Instagram, Reddit)",
            "Southeast Asia Press (Kompas, VNExpress, Jakarta Post)",
            "Indian & South Asian Press (The Hindu, Times of India, Dainik Jagran)",
            "Official Releases (.gov.au, .edu.au, Corporate Newsrooms, ASX)"
        ],
        default=[
            "Global Tier-1 & Wires (Reuters, AP, WashPost, NYT, CNN, BBC, TIME, Forbes)",
            "Australian Press (AFR, ABC News, SMH, The Age, news.com.au)",
            "Social Media Platforms (LinkedIn, X/Twitter, YouTube, Instagram, Reddit)",
            "Official Releases (.gov.au, .edu.au, Corporate Newsrooms, ASX)"
        ]
    )

    st.divider()
    if st.button("Reset Brief Buffer & Clear All"):
        st.session_state.cumulative_brief = None
        st.session_state.executed_query = ""
        st.rerun()

# --- BRANDED EXECUTIVE HEADER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-tagline">WORLD WIDE MONITOR · EXECUTIVE MEDIA INTELLIGENCE</div>
        <div class="brand-title">Great work doesn't speak for itself.</div>
        <div class="brand-subtitle">Strategic media analysis, verifiable audience reach metrics, and cross-lingual reporting for government, university, and corporate leadership.</div>
    </div>
""", unsafe_allow_html=True)

st.info(
    "ℹ️ **Sequential Report Building:** World Wide Monitor allows you to build complete media reports step by step. "
    "You can run live web searches, add specific article links, or directly enter mixed broadcast, print, social, and online outlet records. "
    "New inputs continuously expand and refine your report without losing previously analysed information.",
    icon="ℹ️"
)

# --- STRICT AUSTRALIAN ENGLISH SCHEMA ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher, broadcaster, social platform, or government newsroom name verbatim.")
    medium_type: str = Field(description="Media format(s) covering this story (e.g., Online, Radio, TV, Print, Social Media).")
    author_byline: str = Field(description="Author, journalist, or account handle verbatim. Write 'not stated' if absent.")
    publication_date: str = Field(description="Publication or post date verbatim. Write 'not stated' if absent.")
    original_language: str = Field(description="Original language of the coverage item.")
    canonical_source_url: str = Field(description="Direct, clean resolving canonical URL discovered on the web for this coverage piece.")
    audience_reach_metrics: str = Field(description="Audience reach or follower counts. Disclose if independently verified or marked '[Publisher Self-Reported / Unverified]'.")
    advertising_value_equivalent: str = Field(description="Estimated Advertising Value Equivalent (AVE) or PR value (e.g. '$14,500 AUD [Estimated AVE]').")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Factual title describing the coverage event.")
    source_category: str = Field(description="Categorize as: 'Global Tier-1', 'National Press', 'Social Media', 'Industry Trade Press', or 'Official Primary Release'")
    prominence_depth: str = Field(description="Categorize as: 'Main Focus of Story', 'Significant Segment', or 'Minor Mention'")
    representation_mode: str = Field(description="Categorize as: 'Positive Framing', 'Negative Framing', or 'Expert Commentator / Sector Authority'")
    co_represented_entities: str = Field(description="Other individuals, companies, or government agencies quoted or featured in the item.")
    core_event_summary: str = Field(description="Copyright-compliant summary restricted to lead paragraphs and 20-word context windows surrounding key terms.")
    covering_outlets: list[CoverageOutlet]

class WWMExecutiveAnalysisBrief(BaseModel):
    coverage_found: bool = Field(description="Set to False if no verified coverage matched parameters or direct inputs.")
    verified_coverage_metric: str = Field(description="Factual count of retrieved and manually entered records (e.g. 'Media Index: 8 primary tier-1 and national records analysed across scope').")
    total_combined_audience_reach: str = Field(description="Summed aggregate verifiable reach across all news and social channels (e.g., 'Total Combined Reach: 3.8M Audience').")
    total_advertising_value_equivalent: str = Field(description="Summed aggregate Advertising Value Equivalent (e.g., 'Total Estimated AVE: $125,000 AUD').")
    headline_synthesis: str = Field(description="1-2 sentence executive overview of overall coverage trajectory.")
    sentiment_framing_read: str = Field(description="1-2 concise lines evaluating framing. Recognize expert authority: if addressing difficult sector topics, frame this POSITIVELY as domain leadership.")
    subject_quoted_vs_reported: str = Field(description="Concise summary of direct subject quotes vs. what external parties, media, or social commentary reported about them.")
    engagement_opportunities: str = Field(description="Strategic commentary identifying public, media, social media, and policy channels for further outreach and impact.")
    items: list[EventCoverageItem]

# --- EXPORT GENERATORS ---
def generate_markdown_brief(brief, query, lang):
    md = f"# CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF ({lang.upper()})\n"
    md += f"**Scope / Target Strategy:** `{query}`\n"
    md += f"**Coverage Index:** {brief.get('verified_coverage_metric', 'Verified Scope')}\n"
    md += f"**Impact Valuation:** {brief.get('total_combined_audience_reach', '')} | {brief.get('total_advertising_value_equivalent', '')}\n\n"
    md += f"## 1. Executive Summary & Strategic Read\n"
    md += f"**Overview:** {brief['headline_synthesis']}\n\n"
    md += f"**Sentiment & Media Representation:** {brief['sentiment_framing_read']}\n\n"
    md += f"**Direct Quotes & External Commentary:** {brief['subject_quoted_vs_reported']}\n\n"
    md += f"**Strategic Engagement Opportunities:** {brief['engagement_opportunities']}\n\n"
    md += f"---\n\n"
    md += f"## 2. Key Media Records, Reach & Value Metrics\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']} | **Prominence:** {item['prominence_depth']}\n"
        md += f"- **Framing:** {item['representation_mode']} | **Co-Represented Entities:** {item['co_represented_entities']}\n"
        md += f"- **Summary:** {item['core_event_summary']}\n"
        for outlet in item["covering_outlets"]:
            md += f"  - **{outlet['outlet_name']}** ({outlet['medium_type']}) — *Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']} | *Lang:* {outlet['original_language']}\n"
            md += f"    - *Audience Reach:* {outlet['audience_reach_metrics']} | *Estimated AVE:* {outlet['advertising_value_equivalent']}\n"
            md += f"    - *Source Referral Link:* [{outlet['canonical_source_url']}]({outlet['canonical_source_url']})\n"
        md += "\n"
    md += f"\n\n*Copyright & Fair Use Protocol: Extracted under 20-word window bounds. Confirm details against linked canonical source URLs prior to distribution.*"
    return md

def generate_docx_brief(brief, query, lang):
    doc = Document()
    doc.add_heading(f"CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF ({lang.upper()})", level=0)
    doc.add_paragraph(f"Scope / Target Strategy: {query}")
    doc.add_paragraph(f"Coverage Index: {brief.get('verified_coverage_metric', 'Verified Scope')}")
    doc.add_paragraph(f"Audience Reach & AVE: {brief.get('total_combined_audience_reach', '')} | {brief.get('total_advertising_value_equivalent', '')}")
    
    doc.add_heading("1. Executive Summary & Strategic Read", level=1)
    doc.add_paragraph(f"Overview: {brief['headline_synthesis']}")
    doc.add_paragraph(f"Sentiment & Media Representation: {brief['sentiment_framing_read']}")
    doc.add_paragraph(f"Direct Quotes & External Commentary: {brief['subject_quoted_vs_reported']}")
    doc.add_paragraph(f"Strategic Engagement Opportunities: {brief['engagement_opportunities']}")
    
    doc.add_heading("2. Key Media Records & Verified Audience Reach", level=1)
    for item in brief["items"]:
        doc.add_heading(f"📌 {item['event_title']}", level=2)
        doc.add_paragraph(f"Category: {item['source_category']} | Prominence: {item['prominence_depth']}")
        doc.add_paragraph(f"Framing: {item['representation_mode']} | Co-Represented: {item['co_represented_entities']}")
        doc.add_paragraph(f"Summary: {item['core_event_summary']}")
        for outlet in item["covering_outlets"]:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{outlet['outlet_name']} ({outlet['medium_type']}) ").bold = True
            p.add_run(f"- Byline: {outlet['author_byline']} | Date: {outlet['publication_date']} | Reach: {outlet['audience_reach_metrics']} | AVE: {outlet['advertising_value_equivalent']} - {outlet['canonical_source_url']}")
            
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
    pdf.cell(epw, 6, clean_pdf_text(f'{brief.get("total_combined_audience_reach", "")} | {brief.get("total_advertising_value_equivalent", "")}'), new_x="LMARGIN", new_y="NEXT")
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
    pdf.cell(epw, 8, '5. Key Media Records & Audience Reach', new_x="LMARGIN", new_y="NEXT")
    
    for item in brief.get("items", []):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 5, clean_pdf_text(f"* {item.get('event_title', '')} ({item.get('representation_mode', '')})"))
        
        pdf.set_font('Helvetica', '', 9)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 5, clean_pdf_text(f"Summary: {item.get('core_event_summary', '')}"))
        
        for outlet in item.get('covering_outlets', []):
            outlet_line = f"  - Outlet: {outlet.get('outlet_name', '')} ({outlet.get('medium_type', 'Online')}) | Date: {outlet.get('publication_date', '')} | Reach: {outlet.get('audience_reach_metrics', 'Not stated')} | AVE: {outlet.get('advertising_value_equivalent', 'Not stated')}"
            pdf.set_x(margin)
            pdf.multi_cell(epw, 5, clean_pdf_text(outlet_line))
            
        pdf.ln(3)
        
    return bytes(pdf.output())

# --- TRIPLE INPUT TABS ---
tab_search, tab_custom_urls, tab_manual_entry = st.tabs([
    "🔍 Live Media Search", 
    "🔗 Add Specific Article Links", 
    "📝 Direct Media & Broadcast Record Input"
])

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
    st.markdown("##### Add Specific Article Links")
    st.caption("Paste additional article or post links below (up to 100 URLs, one per line). World Wide Monitor will analyse these documents and combine them into your report.")
    raw_urls_text = st.text_area(
        "Paste Article URLs:", 
        height=120, 
        placeholder="https://www.theguardian.com/science/2023/aug/23/full-of-beans-scientists-use-processed-coffee-grounds-to-make-stronger-concrete\nhttps://www.rmit.edu.au/news/all-news/2023/aug/coffee-concrete"
    )
    custom_urls_input = [line.strip() for line in raw_urls_text.split("\n") if line.strip().startswith("http")]

with tab_manual_entry:
    st.markdown("##### Direct Media & Broadcast Input")
    st.markdown(
        "<div class='notice-box'><b>User Data Responsibility Notice:</b> Information entered via Direct Input is maintained by the user. "
        "The analyst/user retains responsibility for ensuring the accuracy of manually submitted broadcast, print, or social media records.</div>", 
        unsafe_allow_html=True
    )
    
    with st.form("manual_ingestion_form"):
        st.caption("Enter up to 100 mixed media outlets, broadcast networks, social channels, or government bodies at once (one per line). Search will automatically look for matching online links.")
        
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            raw_outlets_batch = st.text_area(
                "Media Outlets / Broadcasters / Social Channels (Up to 100, one per line):",
                height=110,
                placeholder="ABC News\nThe Australian\n7.30 Report\n2GB Sydney\nLinkedIn Official Page\nDepartment of Infrastructure"
            )
            man_mediums = st.multiselect(
                "Selected Formats (Optional - leave blank for automatic detection or select all applicable):", 
                ["Online Press", "Print Newspaper / Magazine", "Radio Broadcast", "Television Broadcast", "Podcast", "Social Media Platform", "Government / Official Release"],
                default=[]
            )
            man_framing = st.selectbox("Representation / Framing Mode", ["Expert Commentator / Sector Authority", "Positive Framing", "Negative Framing"])
        
        with m_col2:
            man_topic = st.text_input("Story Title / Event Topic", placeholder="e.g., Commercialisation of Spent Coffee Biochar Infrastructure")
            man_depth = st.selectbox("Prominence / Story Depth", ["Main Focus of Story", "Significant Segment", "Minor Mention"])
            man_co_represented = st.text_input("Other Co-Represented Entities / Organisations", placeholder="e.g., Macedon Ranges Shire Council, BildGroup, VicRoads")
            man_reach = st.text_input("Audience Reach / Followers / Circulation (Optional)", placeholder="e.g., 1.2M Monthly Audience (Roy Morgan) or 450,000 [Publisher Self-Reported / Unverified]")
            man_ave = st.text_input("Estimated Advertising Value Equivalent / PR Value (Optional)", placeholder="e.g., $18,500 AUD [Estimated AVE]")
            man_byline = st.text_input("Author / Journalist / Account Handle (Optional)", placeholder="e.g., Sarah Martin")
            
        man_summary = st.text_area("Content Summary & Key Context Snippet", placeholder="Summarise core claims, key quotes, or context discussed during the segment/article...")
        submit_manual = st.form_submit_button("➕ Combine Direct Input Records Into Report")

# Active Scope Calculation
if search_query_input:
    st.session_state.executed_query = search_query_input

st.markdown("<br>", unsafe_allow_html=True)

# --- EXECUTION ENGINE ---
btn_label = "Generate Executive Brief" if st.session_state.cumulative_brief is None else "Update & Expand Executive Brief (Combine New Inputs)"

if st.button(btn_label) or submit_manual:
    if not search_query_input and not custom_urls_input and not submit_manual and not st.session_state.executed_query:
        st.error("Please enter a search query, paste article URLs, or complete the direct input form.")
    elif "Gemini" in api_provider and not gemini_key:
        st.error("Please enter your Gemini API Key in the sidebar.")
    else:
        with st.status("Synthesizing Executive Intelligence...", expanded=True) as status:
            current_date = datetime.datetime.now().strftime("%B %d, %Y")
            
            # Multi-Outlet Direct Input Buffer Construction
            manual_payload_prompt = ""
            if submit_manual and raw_outlets_batch.strip():
                outlets_list = [line.strip() for line in raw_outlets_batch.split("\n") if line.strip()]
                mediums_str = ", ".join(man_mediums) if man_mediums else "Mixed Formats (Online/Broadcast/Print)"
                outlets_str = ", ".join(outlets_list[:100])
                
                manual_payload_prompt = f"""
                EXPLICIT BATCH MEDIA OUTLETS ENTERED BY ANALYST ({len(outlets_list)} outlets submitted):
                - Outlets / Channels / Organisations: {outlets_str}
                - Formats Covered: {mediums_str}
                - Story Title / Topic: {man_topic}
                - Representation Framing: {man_framing}
                - Prominence Depth: {man_depth}
                - Co-Represented Entities: {man_co_represented}
                - Author / Handle: {man_byline if man_byline.strip() else 'not stated'}
                - Audience Reach / Followers: {man_reach if man_reach.strip() else 'Not stated'}
                - Advertising Value Equivalent (AVE): {man_ave if man_ave.strip() else 'Not stated'}
                - Content Summary: {man_summary}
                
                SEARCH TOOL TRIGGER INSTRUCTION: Perform an active web search for these specific media outlets ({outlets_str}) in relation to the topic '{man_topic}' or '{st.session_state.executed_query}'. Locate real, resolving web URLs, digital press releases, or broadcast summaries for these outlets and embed their canonical URLs in the 'canonical_source_url' field.
                """

            existing_brief_context = ""
            if st.session_state.cumulative_brief:
                existing_brief_context = f"""
                EXISTING REPORT BUFFER (ADDITIVE CUMULATIVE COMBINATION):
                - Headline Synthesis: {st.session_state.cumulative_brief.get('headline_synthesis', '')}
                - Current Items Analysed: {len(st.session_state.cumulative_brief.get('items', []))}
                INSTRUCTION: Synthesise the new search results, custom URLs, or direct input entries TOGETHER with this existing intelligence. Do NOT discard prior valid coverage cards.
                """
            
            urls_formatted = "\n".join([f"- {u}" for u in custom_urls_input[:100]]) if custom_urls_input else "None provided."
            active_q = search_query_input if search_query_input else st.session_state.executed_query
            
            prompt = f"""
            Today is {current_date}.
            You are WWM's Senior Strategic Intelligence Analyst preparing a brief for government ministers, university vice-chancellors, and corporate executive boards.
            
            REPORT TIER FORMAT: {report_format_tier}. Calibrate depth, page count, and detail level to match this report type.
            
            SPELLING MANDATE: Use strict AUSTRALIAN ENGLISH spelling throughout (e.g. organisation, summarise, characterise, licence, labelling).
            
            REPORT OUTPUT LANGUAGE: Synthesise the entire executive brief in {output_language}. Use clean, professional language appropriate for executive leadership.
            
            MEDIA & SOCIAL FOCUS MODE: {social_media_focus}.
            
            SCOPE & SOURCES:
            - Active Strategy Query: {active_q}
            - Custom Added URLs ({len(custom_urls_input)} provided): {urls_formatted}
            
            {manual_payload_prompt}
            {existing_brief_context}
            
            HIGH-VOLUME QUERY MANAGEMENT:
            Count the exact number of verified items analysed in this payload and state it factually in 'verified_coverage_metric' (e.g. "Media Index: 9 primary tier-1 and national media items analysed across scope").
            Do NOT output dozens of repetitive cards. Present ONLY the top 5 to 8 most influential items across Global Tier-1 Mastheads, National Press, Social Media Channels, Industry Trade Media, and Official Primary Releases.
            
            TOTAL AUDIENCE REACH & ADVERTISING VALUE EQUIVALENT (AVE):
            - Sum total aggregate reach across all news and social channels and output in 'total_combined_audience_reach' (e.g. "Total Combined Reach: 4.2M Audience").
            - Sum total aggregate Advertising Value Equivalent (AVE) / PR value and output in 'total_advertising_value_equivalent' (e.g. "Total Estimated AVE: $140,000 AUD").
            - For each coverage outlet, extract or estimate verifiable audience reach and AVE.
              - If sourced from official rating bodies (Roy Morgan, AMAA, OztAM, CRA, IAB Australia), present figures cleanly (e.g. "1.4M Monthly Unique Audience (Roy Morgan)").
              - If figures come from publisher media kits or self-disclosures, explicitly append the disclosure tag: "[Publisher Self-Reported / Unverified]".
            
            COPYRIGHT & FAIR USE PROTOCOL:
            Consume and extract ONLY headlines, bylines, dates, lead paragraphs (paras 1-2), and 20-word keyword context snippets.
            
            STRATEGIC ANALYSIS INSTRUCTIONS:
            1. sentiment_framing_read: Evaluate sentiment. Recognize expert authority: if a subject addresses challenging or negative sector topics (e.g. waste crisis or industrial risk), frame this POSITIVELY as domain expertise.
            2. subject_quoted_vs_reported: Summarise direct subject quotes vs. external commentary.
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
            st.caption(f"📈 **Impact Metrics:** {brief.get('total_combined_audience_reach', '')} | {brief.get('total_advertising_value_equivalent', '')}")
    
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
        st.subheader("1. Executive Summary & Strategic Read")
        st.info(brief["headline_synthesis"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("2. Sentiment & Media Representation")
            st.write(brief["sentiment_framing_read"])
            
            st.subheader("3. Direct Quotes vs. External Commentary")
            st.write(brief["subject_quoted_vs_reported"])
        with col2:
            st.subheader("4. Strategic Engagement Opportunities")
            st.warning(brief["engagement_opportunities"])
            
        st.divider()
        st.subheader("5. Key Media Records & Verified Audience Reach")
        for item in brief["items"]:
            with st.expander(f"📌 {item['event_title']}"):
                st.markdown(f"**Category:** `{item['source_category']}` | **Prominence:** `{item['prominence_depth']}`")
                st.markdown(f"**Framing:** `{item['representation_mode']}` | **Co-Represented:** `{item['co_represented_entities']}`")
                st.write(f"**Summary:** {item['core_event_summary']}")
                st.markdown("**Covering Outlets, Audience Reach & AVE Metrics:**")
                
                for outlet in item["covering_outlets"]:
                    st.markdown(
                        f"📰 **{outlet['outlet_name']}** ({outlet['medium_type']}) | ✍️ *Byline:* {outlet['author_byline']} | 📅 *Date:* {outlet['publication_date']}<br>"
                        f"📊 *Audience Reach:* **{outlet['audience_reach_metrics']}** | 💰 *Estimated AVE:* **{outlet['advertising_value_equivalent']}**<br>"
                        f"🔗 <a href='{outlet['canonical_source_url']}' target='_blank'>Review Original Canonical Source Link</a>",
                        unsafe_allow_html=True
                    )
    
    st.markdown(f"""
        <div class="disclaimer-box">
            <b>Executive Verification Note:</b> WWM extracts lead paragraphs and 20-word keyword context windows to comply with international fair-use copyright guidelines. Output language set to <b>{output_language}</b>. Always confirm critical details against canonical source URLs prior to executive distribution.
        </div>
    """, unsafe_allow_html=True)
            
    st.markdown("</div>", unsafe_allow_html=True)
