import json
import datetime
import io
import re
import streamlit as st
import pandas as pd
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from docx import Document
from fpdf import FPDF

# --- UI CONFIGURATION (WWM BRANDING & SINGLE-WORD RESPONSIVE METRICS) ---
st.set_page_config(page_title="World Wide Monitor", page_icon="📡", layout="wide")

# CUSTOM CSS - SINGLE-WORD CARD PADDING & HIGH-CONTRAST INK PALETTE
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    .stApp { background-color: #14120F !important; color: #F2EDE3 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #1A1814 !important; border-right: 1px solid #2C2822 !important; }
    [data-testid="stSidebar"] * { color: #C6BCA9 !important; }

    .brand-header { background-color: #1A1814; border: 1px solid #2C2822; padding: 24px 28px; border-radius: 2px; margin-bottom: 20px; }
    .brand-tagline { font-family: 'Inter', sans-serif; font-size: 0.75rem; letter-spacing: 0.25em; text-transform: uppercase; color: #6B6B6B; margin-bottom: 8px; }
    .brand-title { font-family: 'Cormorant Garamond', serif; font-size: clamp(1.8rem, 3.5vw, 2.6rem); font-weight: 400; color: #F2EDE3; margin: 0; line-height: 1.1; }
    .brand-subtitle { font-family: 'Cormorant Garamond', serif; font-size: clamp(0.95rem, 1.8vw, 1.15rem); font-style: italic; color: #C6BCA9; margin-top: 6px; }

    /* HIGH-CONTRAST BONE INPUT FIELDS */
    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
        background-color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important; border-radius: 2px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input, div[data-baseweb="textarea"] textarea, textarea {
        background-color: #F2EDE3 !important; color: #14120F !important; font-weight: 600 !important; font-size: 0.95rem !important; opacity: 1 !important;
    }
    div[data-baseweb="input"] input::placeholder, div[data-baseweb="textarea"] textarea::placeholder, textarea::placeholder {
        color: #555555 !important; opacity: 0.8 !important;
    }
    div[data-baseweb="select"] * { color: #14120F !important; font-weight: 600 !important; }

    /* RESPONSIVE METRIC CARDS - STRICT SINGLE-WORD OVERFLOW PROTECTION */
    .metric-card {
        background-color: #1A1814;
        border: 1px solid #2C2822;
        padding: 16px 8px;
        border-radius: 2px;
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        min-height: 110px;
        overflow: hidden;
    }
    .metric-card h4 {
        font-family: 'Inter', sans-serif;
        font-size: clamp(0.65rem, 1vw, 0.75rem);
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #C6BCA9;
        margin: 0 0 4px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }
    .metric-card h2 {
        font-family: 'Inter', sans-serif;
        font-size: clamp(1.1rem, 2vw, 1.5rem);
        font-weight: 600;
        color: #F2EDE3;
        margin: 0 0 4px 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }
    .metric-card caption {
        font-size: clamp(0.6rem, 0.85vw, 0.7rem);
        color: #6B6B6B;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
    }

    .stButton>button {
        background-color: transparent !important; color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        border-radius: 2px !important; padding: 0.65rem 1.4rem !important; font-family: 'Inter', sans-serif !important;
        font-size: 0.75rem !important; letter-spacing: 0.15em !important; text-transform: uppercase !important;
    }
    .stDownloadButton>button {
        background-color: #C6BCA9 !important; color: #14120F !important; font-weight: 600 !important;
        padding: 0.75rem 1.4rem !important; border-radius: 2px !important; border: none !important;
    }
    .reset-btn>button {
        background-color: #2C2822 !important; color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        font-weight: 600 !important; padding: 0.5rem 1rem !important;
    }
    .report-card { background-color: #1A1814; border: 1px solid #2C2822; padding: 28px; border-radius: 2px; }
    .disclaimer-box { background-color: #1A1814; border-left: 2px solid #C6BCA9; padding: 10px 14px; font-size: 0.8rem; color: #6B6B6B; margin-top: 20px; }
    .notice-box { background-color: #1A1814; border-left: 2px solid #6B6B6B; padding: 8px 12px; font-size: 0.78rem; color: #C6BCA9; margin-bottom: 14px; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZE PERSISTENT SESSION STATE ---
if "cumulative_brief" not in st.session_state:
    st.session_state.cumulative_brief = None
if "executed_query" not in st.session_state:
    st.session_state.executed_query = ""
if "user_plan" not in st.session_state:
    st.session_state.user_plan = "Pro tier ($29.99/mo)"
if "search_balance" not in st.session_state:
    st.session_state.search_balance = 84
if "saved_queries" not in st.session_state:
    st.session_state.saved_queries = [
        "\"Rajeev Roychand\" AND RMIT",
        "Spent coffee biochar concrete infrastructure",
        "Victoria Big Build sustainable materials",
        "Standards Australia biochar aggregate"
    ]
if "report_library" not in st.session_state:
    st.session_state.report_library = []

def clear_all_searches():
    st.session_state.cumulative_brief = None
    st.session_state.executed_query = ""
    st.rerun()

# --- NAVIGATION CONTROLLER (SINGLE-WORD TABS) ---
main_mode = st.radio(
    "Select mode:",
    ["📊 Dashboard", "📄 Brief", "📚 Library"],
    horizontal=True
)

# --- SIDEBAR CONTROL PANEL ---
with st.sidebar:
    st.markdown("### WWM")
    st.caption("GLOBAL MEDIA INSIGHTS")
    st.divider()
    
    st.subheader("1. Intelligence engine")
    api_provider = st.selectbox(
        "AI engine provider",
        [
            "Google Gemini 3 (Native search grounding)",
            "OpenAI GPT-4o (Web grounded)",
            "Tavily Search + Gemini intelligence"
        ],
        index=0
    )
    
    gemini_key = st.text_input("Gemini API key", type="password", placeholder="AIzaSy...")

    st.divider()
    st.subheader("2. Objective and scope")
    
    report_purpose_selected = st.selectbox(
        "Primary objective",
        [
            "Demonstrate long-term impact / career promotion & track record",
            "Identify emerging issue / early warning radar",
            "Track ongoing issue / crisis management",
            "Institutional board briefing / ministerial reporting",
            "Custom strategic objective"
        ],
        index=0
    )
    
    custom_purpose_input = ""
    if "Custom" in report_purpose_selected:
        custom_purpose_input = st.text_input("Specify custom objective:", placeholder="e.g. Funding application evidence dossier")
        
    active_report_purpose = custom_purpose_input if custom_purpose_input.strip() else report_purpose_selected

    report_format_tier = st.selectbox(
        "Select report type",
        [
            "Executive leadership brief (Strict 1 page PDF — C-Suite and Board)",
            "Strategic advisory report (2 pages PDF — Subject experts)",
            "Comprehensive media operations report (Up to 4 pages — PR and Media teams)",
            "Social media intelligence digest (Up to 2 pages — Digital teams)"
        ],
        index=0
    )

    output_language = st.selectbox(
        "Report output language",
        ["English", "French (Français)", "Spanish (Español)", "German (Deutsch)", "Mandarin Chinese (中文)", "Japanese (日本語)", "Indonesian (Bahasa Indonesia)", "Vietnamese (Tiếng Việt)", "Hindi (हिंदी)", "Arabic (العربية)"],
        index=0
    )
    
    st.divider()
    st.subheader("3. Media channels and horizon")
    
    date_window = st.selectbox(
        "Recency scope",
        ["Past 7 days (Current cycle)", "Past 30 days", "Past 12 months", "Past 4 years archive"],
        index=3
    )

    social_media_focus = st.selectbox(
        "Coverage scope",
        [
            "Include major news and verified social media combined",
            "Focus exclusively on major news and broadcast press",
            "Focus exclusively on high-reach social media channels"
        ],
        index=0
    )
    
    selected_sources = st.multiselect(
        "Target channels",
        [
            "Global tier-1 press & wires",
            "Australian press & national broadcasters",
            "Major social media channels (>10,000 followers)",
            "Southeast Asian press",
            "Indian & South Asian press",
            "Official releases (.gov.au, .edu.au, ASX)"
        ],
        default=[
            "Global tier-1 press & wires",
            "Australian press & national broadcasters",
            "Official releases (.gov.au, .edu.au, ASX)"
        ]
    )

    st.divider()
    st.button("Reset brief buffer and clear all", on_click=clear_all_searches, key="sidebar_reset")

# --- BRANDED EXECUTIVE HEADER ---
st.markdown("""
    <div class="brand-header">
        <div class="brand-tagline">GLOBAL MEDIA INSIGHTS</div>
        <div class="brand-title">World Wide Monitor</div>
        <div class="brand-subtitle">Strategic media intelligence, audience reach analytics, and cross-lingual reporting for leadership.</div>
    </div>
""", unsafe_allow_html=True)

# --- PROMINENT CONTROL TOOLBAR ---
control_col1, control_col2 = st.columns([3, 1])
with control_col1:
    st.info(
        "ℹ️ **Sequential report building:** World Wide Monitor allows you to build complete media reports step by step. "
        "You can run live web searches, add specific article links, or directly enter broadcast, print, social, and online outlet records.",
        icon="ℹ️"
    )
with control_col2:
    st.markdown("<div class='reset-btn'>", unsafe_allow_html=True)
    st.button("🔄 Start new search / Clear buffer", on_click=clear_all_searches, key="header_reset", use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- STRICT AUSTRALIAN ENGLISH SCHEMA ---
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher, broadcaster, major social channel, or government newsroom name verbatim.")
    medium_type: str = Field(description="Media format(s) covering this story (e.g., Online Press, Radio, TV, Print, Social Media).")
    author_byline: str = Field(description="Author, journalist, or account handle verbatim. Write 'not stated' if absent.")
    publication_date: str = Field(description="Publication or post date verbatim. Write 'not stated' if absent.")
    original_language: str = Field(description="Original language of the coverage item.")
    canonical_source_url: str = Field(description="Direct, clean resolving web URL verbatim from grounding. Write 'None' if unverified or broken.")
    audience_reach_metrics: str = Field(description="Audience reach or follower counts (Minimum threshold: 100,000 for press; 10,000 for social). Disclose if independently verified or marked '[Publisher Self-Reported / Unverified]'.")

class EventCoverageItem(BaseModel):
    event_title: str = Field(description="Factual title describing the coverage event.")
    source_category: str = Field(description="Categorize as: 'Global Tier-1', 'National Press', 'Major Social Media', 'Industry Trade Press', or 'Official Primary Release'")
    prominence_depth: str = Field(description="Categorize as: 'Lead Story / Feature', 'Significant Segment', or 'Passing Mention'")
    representation_mode: str = Field(description="Categorize as: 'Positive Framing', 'Negative Framing', or 'Expert Commentator / Sector Authority'")
    key_message_delivered: str = Field(description="Specific institutional key messages delivered in this item.")
    co_represented_entities: str = Field(description="Other individuals, companies, or government agencies quoted or featured in the item.")
    core_event_summary: str = Field(description="Copyright-compliant summary restricted to lead paragraphs and 20-word context windows surrounding key terms.")
    covering_outlets: list[CoverageOutlet]

class WWMExecutiveAnalysisBrief(BaseModel):
    coverage_found: bool = Field(description="Set to False if no verified coverage matched parameters.")
    verified_coverage_metric: str = Field(description="Factual count of retrieved records (e.g. 'Media Index: 7 tier-1 and national records analysed across scope').")
    total_combined_audience_reach: str = Field(description="Summed aggregate verifiable reach across major news and verified social channels (e.g., 'Total Combined Reach: 185.5 Million Audience').")
    headline_synthesis: str = Field(description="1-2 sentence executive overview of overall coverage trajectory.")
    sentiment_framing_read: str = Field(description="1-2 concise lines evaluating framing. Recognize expert authority: if addressing difficult sector topics, frame this POSITIVELY as domain leadership.")
    subject_quoted_vs_reported: str = Field(description="Concise summary of direct spokesperson quotes vs. what external media or social commentary reported about them.")
    engagement_opportunities: str = Field(description="Strategic commentary identifying public, media, social media, and policy channels for further outreach and impact.")
    items: list[EventCoverageItem]

# --- BRANDED PDF ENGINE ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Helvetica', 'B', 8)
        self.set_text_color(107, 107, 107)
        self.set_y(8)
        self.cell(0, 5, 'WORLD WIDE MONITOR  |  EXECUTIVE BRIEF', align='R')

    def footer(self):
        self.set_y(-10)
        self.set_font('Helvetica', '', 6.5)
        self.set_text_color(107, 107, 107)
        self.cell(0, 5, 'Generated with AI assistance and reviewed by WWM. Sources are linked where verified; confirm critical details against source before acting.', align='C')

def clean_pdf_text(text):
    if not text:
        return ""
    replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '-', '–': '-', '•': '*'}
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text.encode('latin-1', 'replace').decode('latin-1')

def is_valid_url(url):
    return url and url.strip().lower() not in ["none", "null", "", "direct record input"] and url.strip().startswith("http")

def generate_pdf_brief(brief, query, lang, purpose_text, time_scope, channels_str, is_strict_one_page=False):
    pdf = PDFReport()
    pdf.set_fill_color(242, 237, 227)
    margin = 12
    top_margin = 14
    pdf.set_margins(margin, top_margin, margin)
    pdf.add_page()
    
    if is_strict_one_page:
        pdf.set_auto_page_break(auto=False)
    else:
        pdf.set_auto_page_break(auto=True, margin=14)
        
    epw = pdf.epw
    
    clean_query = query.strip()
    if len(clean_query) > 55:
        clean_query = clean_query[:52] + "..."

    title_size = 12 if is_strict_one_page else 14
    pdf.set_font('Helvetica', 'B', title_size)
    pdf.set_text_color(35, 35, 35)
    pdf.set_x(margin)
    pdf.cell(epw, 5.5 if is_strict_one_page else 7, clean_pdf_text(f'Executive Brief ({lang})'), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', 'B', 7 if is_strict_one_page else 7.5)
    pdf.set_text_color(107, 107, 107)
    pdf.set_x(margin)
    pdf.cell(epw, 3.5, clean_pdf_text(f'OBJECTIVE: {purpose_text.upper()}'), new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font('Helvetica', 'I', 6.5 if is_strict_one_page else 7.5)
    pdf.set_x(margin)
    pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f'Scope: {clean_query}  |  Horizon: {time_scope}  |  Channels: {channels_str}'))
    pdf.set_x(margin)
    pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f'{brief.get("verified_coverage_metric", "")}  |  {brief.get("total_combined_audience_reach", "")}'))
    
    pdf.set_draw_color(198, 188, 169)
    pdf.set_line_width(0.2)
    pdf.ln(1.5 if is_strict_one_page else 2)
    pdf.line(margin, pdf.get_y(), margin + epw, pdf.get_y())
    pdf.ln(2.5 if is_strict_one_page else 3.5)
    
    h_size = 9 if is_strict_one_page else 10.5
    body_size = 8 if is_strict_one_page else 9
    lh = 3.4 if is_strict_one_page else 4.2
    gap = 1.8 if is_strict_one_page else 2.5
    
    pdf.set_font('Helvetica', 'B', h_size)
    pdf.set_text_color(20, 18, 15)
    pdf.set_x(margin)
    pdf.cell(epw, 4 if is_strict_one_page else 5.5, '1. Executive overview', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.set_text_color(35, 35, 35)
    pdf.set_x(margin)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('headline_synthesis', '')))
    pdf.ln(gap)
    
    pdf.set_font('Helvetica', 'B', h_size)
    pdf.set_text_color(20, 18, 15)
    pdf.set_x(margin)
    pdf.cell(epw, 4 if is_strict_one_page else 5.5, '2. Positioning and reputation', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.set_text_color(35, 35, 35)
    pdf.set_x(margin)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('sentiment_framing_read', '')))
    pdf.ln(gap)
    
    pdf.set_font('Helvetica', 'B', h_size)
    pdf.set_text_color(20, 18, 15)
    pdf.set_x(margin)
    pdf.cell(epw, 4 if is_strict_one_page else 5.5, '3. Spokesperson quotes and commentary', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.set_text_color(35, 35, 35)
    pdf.set_x(margin)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('subject_quoted_vs_reported', '')))
    pdf.ln(gap)

    pdf.set_font('Helvetica', 'B', h_size)
    pdf.set_text_color(20, 18, 15)
    pdf.set_x(margin)
    pdf.cell(epw, 4 if is_strict_one_page else 5.5, '4. Strategic engagement opportunities', new_x="LMARGIN", new_y="NEXT")
    pdf.set_font('Helvetica', '', body_size)
    pdf.set_text_color(35, 35, 35)
    pdf.set_x(margin)
    pdf.multi_cell(epw, lh, clean_pdf_text(brief.get('engagement_opportunities', '')))
    pdf.ln(gap)
    
    pdf.set_font('Helvetica', 'B', h_size)
    pdf.set_text_color(20, 18, 15)
    pdf.set_x(margin)
    pdf.cell(epw, 4 if is_strict_one_page else 5.5, '5. Tier-1 sourced media records and verified audience reach', new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1.2 if is_strict_one_page else 2)
    
    items_to_render = brief.get("items", [])
    if is_strict_one_page:
        items_to_render = items_to_render[:3]
    
    for item in items_to_render:
        if not is_strict_one_page and pdf.get_y() > 240:
            pdf.add_page()
            
        pdf.set_font('Helvetica', 'B', 8 if is_strict_one_page else 9)
        pdf.set_text_color(20, 18, 15)
        pdf.set_x(margin)
        title_text = f"• {item.get('event_title', '')} ({item.get('representation_mode', '')})"
        pdf.multi_cell(epw, 3.6 if is_strict_one_page else 4.2, clean_pdf_text(title_text))
        
        pdf.set_font('Helvetica', '', 7 if is_strict_one_page else 8)
        pdf.set_text_color(35, 35, 35)
        pdf.set_x(margin)
        pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f"Key messages: {item.get('key_message_delivered', 'Standard coverage')}"))
        pdf.set_x(margin)
        pdf.multi_cell(epw, 3.2 if is_strict_one_page else 3.8, clean_pdf_text(f"Summary: {item.get('core_event_summary', '')}"))
        
        for outlet in item.get('covering_outlets', []):
            pdf.set_font('Helvetica', 'I', 6.5 if is_strict_one_page else 7.5)
            pdf.set_text_color(107, 107, 107)
            outlet_line = f"  - {outlet.get('outlet_name', '')} ({outlet.get('medium_type', 'Online')}) | Date: {outlet.get('publication_date', '')} | Reach: {outlet.get('audience_reach_metrics', 'Not stated')}"
            pdf.set_x(margin)
            pdf.multi_cell(epw, 3 if is_strict_one_page else 3.5, clean_pdf_text(outlet_line))
            
        pdf.ln(1.2 if is_strict_one_page else 1.8)
        pdf.set_draw_color(220, 215, 205)
        pdf.line(margin, pdf.get_y(), margin + epw, pdf.get_y())
        pdf.ln(1.2 if is_strict_one_page else 2)
        
    return bytes(pdf.output())

# --- MARKDOWN & WORD EXPORTS ---
def generate_markdown_brief(brief, query, lang, purpose_text, time_scope, channels_str):
    md = f"# CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF ({lang.upper()})\n\n"
    md += f"**Strategic objective:** `{purpose_text}`  \n"
    md += f"**Query scope:** `{query}`  \n"
    md += f"**Time horizon:** `{time_scope}` | **Channels:** `{channels_str}`  \n"
    md += f"**Coverage index:** {brief.get('verified_coverage_metric', 'Verified scope')}  \n"
    md += f"**Reach metric:** {brief.get('total_combined_audience_reach', '')}\n\n"
    md += f"## 1. Executive summary and strategic read\n"
    md += f"**Overview:** {brief['headline_synthesis']}\n\n"
    md += f"**Positioning and reputation:** {brief['sentiment_framing_read']}\n\n"
    md += f"**Spokesperson quotes and commentary:** {brief['subject_quoted_vs_reported']}\n\n"
    md += f"**Strategic engagement opportunities:** {brief['engagement_opportunities']}\n\n"
    md += f"---\n\n"
    md += f"## 2. Key media records and verified audience reach\n\n"
    for item in brief["items"]:
        md += f"### 📌 {item['event_title']}\n"
        md += f"- **Category:** {item['source_category']} | **Prominence:** {item['prominence_depth']}\n"
        md += f"- **Framing:** {item['representation_mode']} | **Key messages delivered:** {item['key_message_delivered']}\n"
        md += f"- **Summary:** {item['core_event_summary']}\n"
        for outlet in item["covering_outlets"]:
            url = outlet.get('canonical_source_url', '')
            link_str = f" — [Source link]({url})" if is_valid_url(url) else ""
            md += f"  - **{outlet['outlet_name']}** ({outlet['medium_type']}) — *Byline:* {outlet['author_byline']} | *Date:* {outlet['publication_date']} | *Lang:* {outlet['original_language']}{link_str}\n"
            md += f"    - *Audience reach:* {outlet['audience_reach_metrics']}\n"
        md += "\n"
    md += f"\n\n*Generated with AI assistance and reviewed by WWM. Confirm critical details against source before acting.*"
    return md

def generate_docx_brief(brief, query, lang, purpose_text, time_scope, channels_str):
    doc = Document()
    doc.add_heading(f"CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF ({lang.upper()})", level=0)
    
    p_meta = doc.add_paragraph()
    p_meta.add_run("Strategic objective: ").bold = True
    p_meta.add_run(f"{purpose_text}\n")
    p_meta.add_run("Query scope: ").bold = True
    p_meta.add_run(f"{query}\n")
    p_meta.add_run("Time horizon: ").bold = True
    p_meta.add_run(f"{time_scope} | ")
    p_meta.add_run("Channels: ").bold = True
    p_meta.add_run(f"{channels_str}\n")
    p_meta.add_run("Coverage index: ").bold = True
    p_meta.add_run(f"{brief.get('verified_coverage_metric', 'Verified scope')}\n")
    p_meta.add_run("Audience reach: ").bold = True
    p_meta.add_run(f"{brief.get('total_combined_audience_reach', '')}")
    
    doc.add_heading("1. Executive summary and strategic read", level=1)
    doc.add_paragraph(f"Overview: {brief['headline_synthesis']}")
    doc.add_paragraph(f"Positioning and reputation: {brief['sentiment_framing_read']}")
    doc.add_paragraph(f"Spokesperson quotes and commentary: {brief['subject_quoted_vs_reported']}")
    doc.add_paragraph(f"Strategic engagement opportunities: {brief['engagement_opportunities']}")
    
    doc.add_heading("2. Key media records and verified audience reach", level=1)
    for item in brief["items"]:
        doc.add_heading(f"📌 {item['event_title']}", level=2)
        doc.add_paragraph(f"Category: {item['source_category']} | Prominence: {item['prominence_depth']}")
        doc.add_paragraph(f"Framing: {item['representation_mode']} | Key messages delivered: {item['key_message_delivered']}")
        doc.add_paragraph(f"Summary: {item['core_event_summary']}")
        for outlet in item["covering_outlets"]:
            p = doc.add_paragraph(style='List Bullet')
            p.add_run(f"{outlet['outlet_name']} ({outlet['medium_type']}) ").bold = True
            url = outlet.get('canonical_source_url', '')
            url_str = f" - {url}" if is_valid_url(url) else ""
            p.add_run(f"- Byline: {outlet['author_byline']} | Date: {outlet['publication_date']} | Reach: {outlet['audience_reach_metrics']}{url_str}")
            
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer

# --- VIEW 1: LIVE DASHBOARD (SINGLE-WORD METRIC COLUMNS) ---
if "Dashboard" in main_mode:
    st.subheader("📊 Media tracking dashboard")
    st.caption("Real-time monitoring view for emerging issues, crisis tracking, and volume spike detection.")
    
    dash_col1, dash_col2, dash_col3, dash_col4 = st.columns(4)
    with dash_col1:
        st.markdown("<div class='metric-card'><h4>Volume</h4><h2>184</h2><caption>▲ +24% vs past cycle</caption></div>", unsafe_allow_html=True)
    with dash_col2:
        st.markdown("<div class='metric-card'><h4>Reach</h4><h2>308.2M</h2><caption>Verified press & social</caption></div>", unsafe_allow_html=True)
    with dash_col3:
        st.markdown("<div class='metric-card'><h4>Medium</h4><h2>Online</h2><caption>62% Share of voice</caption></div>", unsafe_allow_html=True)
    with dash_col4:
        st.markdown("<div class='metric-card'><h4>Framing</h4><h2>Authority</h2><caption>100% Expert alignment</caption></div>", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.subheader("Media volume spike trajectory (Past 30 days)")
    
    dates = pd.date_range(end=datetime.datetime.today(), periods=30)
    spike_data = pd.DataFrame({
        "Date": dates,
        "Tier-1 Press": [5, 4, 6, 8, 4, 3, 2, 5, 8, 42, 85, 31, 14, 8, 6, 4, 5, 7, 3, 2, 4, 6, 5, 4, 3, 2, 4, 5, 3, 2],
        "Social Channels": [2, 3, 1, 4, 2, 1, 0, 2, 4, 18, 45, 12, 6, 4, 2, 1, 3, 2, 1, 0, 2, 3, 1, 2, 1, 0, 1, 2, 1, 0]
    }).set_index("Date")
    
    st.line_chart(spike_data)

# --- VIEW 2: STRATEGIC BRIEF EXECUTION ---
elif "Brief" in main_mode:
    tab_search, tab_custom_urls, tab_manual_entry = st.tabs([
        "🔍 Live search", 
        "🔗 Added links", 
        "📝 Direct input"
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
        st.markdown("##### Add specific article links")
        st.caption("Paste additional article or post links below (up to 100 URLs, one per line). World Wide Monitor will analyse these documents and combine them into your report.")
        raw_urls_text = st.text_area(
            "Paste article URLs:", 
            height=120, 
            placeholder="https://www.theguardian.com/science/2023/aug/23/full-of-beans-scientists-use-processed-coffee-grounds-to-make-stronger-concrete\nhttps://www.rmit.edu.au/news/all-news/2023/aug/coffee-concrete"
        )
        custom_urls_input = [line.strip() for line in raw_urls_text.split("\n") if line.strip().startswith("http")]

    with tab_manual_entry:
        st.markdown("##### Direct media and broadcast input")
        st.markdown(
            "<div class='notice-box'><b>User data responsibility notice:</b> Information entered via direct input is maintained by the user. "
            "The analyst/user retains responsibility for ensuring the accuracy of manually submitted broadcast, print, or social media records.</div>", 
            unsafe_allow_html=True
        )
        
        with st.form("manual_ingestion_form"):
            st.caption("Enter up to 100 mixed media outlets, broadcast networks, social channels, or government bodies at once (one per line). Search will automatically look for matching online links.")
            
            m_col1, m_col2 = st.columns(2)
            with m_col1:
                raw_outlets_batch = st.text_area(
                    "Media outlets / Broadcasters / Social channels (Up to 100, one per line):",
                    height=110,
                    placeholder="ABC News\nThe Australian\n7.30 Report\n2GB Sydney\nLinkedIn Official Page\nDepartment of Infrastructure"
                )
                man_mediums = st.multiselect(
                    "Selected formats (Optional - leave blank for automatic detection or select all applicable):", 
                    ["Online Press", "Print Newspaper / Magazine", "Radio Broadcast", "Television Broadcast", "Podcast", "Social Media Platform", "Government / Official Release"],
                    default=[]
                )
                man_framing = st.selectbox("Representation / framing mode", ["Expert Commentator / Sector Authority", "Positive Framing", "Negative Framing"])
            
            with m_col2:
                man_topic = st.text_input("Story title / event topic", placeholder="e.g., Commercialisation of Spent Coffee Biochar Infrastructure")
                man_depth = st.selectbox("Prominence / story depth", ["Lead Story / Feature", "Significant Segment", "Passing Mention"])
                man_co_represented = st.text_input("Other co-represented entities / organisations", placeholder="e.g., Macedon Ranges Shire Council, BildGroup, VicRoads")
                man_reach = st.text_input("Audience reach / followers / circulation (Optional)", placeholder="e.g., 1.2 Million Monthly Audience (Roy Morgan) or 450,000 [Publisher Self-Reported / Unverified]")
                man_byline = st.text_input("Author / journalist / account handle (Optional)", placeholder="e.g., Sarah Martin")
                
            man_summary = st.text_area("Content summary and key context snippet", placeholder="Summarise core claims, key quotes, or context discussed during the segment/article...")
            submit_manual = st.form_submit_button("➕ Combine direct input records into report")

    if search_query_input:
        st.session_state.executed_query = search_query_input

    st.markdown("<br>", unsafe_allow_html=True)

    # --- EXECUTION ENGINE ---
    btn_label = "Generate executive brief" if st.session_state.cumulative_brief is None else "Update and expand executive brief (Combine new inputs)"

    if st.button(btn_label) or submit_manual:
        if not search_query_input and not custom_urls_input and not submit_manual and not st.session_state.executed_query:
            st.error("Please enter a search query, paste article URLs, or complete the direct input form.")
        elif "Gemini" in api_provider and not gemini_key:
            st.error("Please enter your Gemini API key in the sidebar.")
        else:
            with st.status("Synthesizing executive intelligence...", expanded=True) as status:
                current_date = datetime.datetime.now().strftime("%B %d, %Y")
                channels_str = ", ".join(selected_sources) if selected_sources else "All Global Channels"
                
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
                    - Content Summary: {man_summary}
                    
                    SEARCH TOOL TRIGGER INSTRUCTION: Perform an active web search for these specific media outlets ({outlets_str}) in relation to the topic '{man_topic}' or '{st.session_state.executed_query}'. Locate real, resolving web URLs for these outlets. If no exact deep URL is found, pass 'None'.
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
                
                PRIMARY STRATEGIC OBJECTIVE: {active_report_purpose}. 
                INSTRUCTION: Frame the 'headline_synthesis', 'sentiment_framing_read', and 'engagement_opportunities' specifically to address this objective. 
                - If objective is 'Demonstrate long-term impact / career promotion & track record', emphasize sustained track record, international authority, cumulative reach, and long-term research translation rather than immediate short-term PR actions.
                
                REPORT TIER FORMAT: {report_format_tier}. Calibrate depth, page count, and detail level to match this report type.
                
                SPELLING MANDATE: Use strict AUSTRALIAN ENGLISH spelling throughout (e.g. organisation, summarise, characterise, licence, labelling).
                
                REPORT OUTPUT LANGUAGE: Synthesise the entire executive brief in {output_language}. Use clean, professional language appropriate for executive leadership.
                
                MEDIA & TIME SCOPE:
                - Recency Scope: {date_window}
                - Channel Scope: {channels_str}
                - Media & Social Focus: {social_media_focus}
                
                STRICT COMPREHENSIVE SEARCH & MINIMUM THRESHOLDS INSTRUCTION:
                1. MULTI-PASS COMPREHENSIVE GROUNDING: Perform a thorough search across global press corridors to ensure tier-1 outlets (e.g. The Washington Post, CNN, BBC, Reuters, The Guardian, AFR, ABC News) and major university press releases are consistently captured.
                2. MINIMUM AUDIENCE THRESHOLDS:
                   - Traditional Press / Broadcast / Online News: Include ONLY outlets with an audience of at least 100,000 readers, viewers, or listeners. Strictly suppress low-value blogs, personal websites, and unverified content aggregators.
                   - Social Media Platforms: Include ONLY verified accounts or creators with at least 10,000 subscribers or followers.
                3. CLEAN URL PROTOCOL: For 'canonical_source_url', pass ONLY exact, verbatim resolving URLs provided in grounding metadata or custom URLs. IF A DIRECT ARTICLE URL IS NOT PRESENT IN GROUNDING RESULTS, WRITE 'None'.
                
                SCOPE & SOURCES:
                - Active Strategy Query: {active_q}
                - Custom Added URLs ({len(custom_urls_input)} provided): {urls_formatted}
                
                {manual_payload_prompt}
                {existing_brief_context}
                
                HIGH-VOLUME QUERY MANAGEMENT:
                Count the exact number of verified items analysed in this payload and state it factually in 'verified_coverage_metric' (e.g. "Media Index: 7 tier-1 and national records analysed; low-value sources below reach thresholds suppressed").
                Do NOT output dozens of repetitive cards. Present ONLY the top 5 to 8 most influential items across Global Tier-1 Mastheads, National Press, Industry Trade Media, and Official Primary Releases.
                
                AUDIENCE REACH & KEY MESSAGES DELIVERED:
                - Sum total aggregate reach across all news and social channels meeting minimum thresholds and output in 'total_combined_audience_reach' (e.g. "Total Combined Reach: 185.5 Million Audience").
                - For each coverage outlet, extract or estimate verifiable audience reach.
                  - If sourced from official rating bodies (Roy Morgan, AMAA, OztAM, CRA, IAB Australia), present figures cleanly (e.g. "1.4 Million Monthly Unique Audience (Roy Morgan)").
                  - If figures come from publisher media kits or self-disclosures, explicitly append the disclosure tag: "[Publisher Self-Reported / Unverified]".
                
                COPYRIGHT & FAIR USE PROTOCOL:
                Consume and extract ONLY headlines, bylines, dates, lead paragraphs (paras 1-2), and 20-word keyword context snippets.
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
                    st.session_state.active_purpose = active_report_purpose
                    st.session_state.active_time_scope = date_window
                    st.session_state.active_channels = channels_str
                    
                    st.session_state.report_library.append({
                        "id": len(st.session_state.report_library) + 1,
                        "date": datetime.datetime.now().strftime("%d %b %Y"),
                        "query": active_q,
                        "objective": active_report_purpose,
                        "reach": st.session_state.cumulative_brief.get("total_combined_audience_reach", "N/A"),
                        "data": st.session_state.cumulative_brief
                    })
                    
                    status.update(label="Executive synthesis complete!", state="complete", expanded=False)
                    
                except Exception as e:
                    st.error(f"Processing error: {str(e)}")

# --- VIEW 3: REPORT LIBRARY & SAVED 50-QUERY DECK ---
else:
    st.subheader("📚 Saved 50-query deck & Report library")
    st.caption("Manage your persistent monitoring deck, search generated reports, and view subscription details.")
    
    lib_col1, lib_col2 = st.columns([2, 1])
    
    with lib_col1:
        st.markdown("#### Saved search deck (Up to 50 queries)")
        
        new_deck_query = st.text_input("Add new topic to 50-query deck:", placeholder="e.g. \"Tom Oxley\" OR Synchron Stentrode")
        if st.button("➕ Add topic to saved deck"):
            if new_deck_query.strip() and len(st.session_state.saved_queries) < 50:
                st.session_state.saved_queries.append(new_deck_query.strip())
                st.success("Topic added to persistent deck!")
                st.rerun()
                
        st.markdown("**Active deck topics:**")
        for idx, q in enumerate(st.session_state.saved_queries, 1):
            q_col1, q_col2 = st.columns([4, 1])
            with q_col1:
                st.markdown(f"**{idx}.** `{q}`")
            with q_col2:
                if st.button("Run", key=f"run_deck_{idx}"):
                    st.session_state.executed_query = q
                    st.info(f"Loaded `{q}` into active scope. Switch to Brief tab to execute.")
                    
        st.divider()
        st.markdown("#### Archive report search engine")
        lib_search_kw = st.text_input("Search generated briefs by keyword, topic, or date:", placeholder="e.g. Coffee Concrete or Sep 2026")
        
        if st.session_state.report_library:
            for rep in st.session_state.report_library:
                if not lib_search_kw or lib_search_kw.lower() in rep["query"].lower() or lib_search_kw.lower() in rep["objective"].lower():
                    with st.expander(f"📄 Report #{rep['id']} — {rep['query']} ({rep['date']})"):
                        st.markdown(f"**Objective:** {rep['objective']}")
                        st.markdown(f"**Audience reach:** {rep['reach']}")
                        st.write(rep["data"]["headline_synthesis"])
        else:
            st.caption("No generated reports saved in library yet. Run an Executive Brief to archive reports.")

    with lib_col2:
        st.markdown("#### User profile & Subscription")
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.markdown(f"### Plan: **{st.session_state.user_plan}**")
        st.markdown(f"**Remaining searches:** `{st.session_state.search_balance} / 100`")
        st.caption("Renewal date: 12 October 2026")
        st.markdown("</div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### Commercial tiers")
        st.markdown("""
        - **Free plan:** 10 lifetime searches
        - **Starter ($9.99/mo):** 10 searches/month
        - **Pro plan ($29.99/mo):** 100 searches/month + Live Dashboard & 50-Query Deck
        - **Master plan ($199.99/mo):** Unlimited searches + Multi-seat export
        """)

# --- DELIVERABLE RENDER (SHARED ACROSS VIEWS) ---
if st.session_state.cumulative_brief and ("Dashboard" in main_mode or "Brief" in main_mode):
    brief = st.session_state.cumulative_brief
    st.markdown("---")
    
    active_purpose = st.session_state.get("active_purpose", active_report_purpose)
    active_time = st.session_state.get("active_time_scope", date_window)
    active_chans = st.session_state.get("active_channels", ", ".join(selected_sources))
    exec_query = st.session_state.get("executed_query", "Executive Media Intelligence Scope")
    is_strict_1page = "Strict 1 page PDF" in report_format_tier
    
    st.markdown("<div class='report-card'>", unsafe_allow_html=True)
    
    header_col1, header_col2 = st.columns([2, 2])
    with header_col1:
        st.caption("CONFIDENTIAL | WORLD WIDE MONITOR EXECUTIVE BRIEF")
        st.header(f"Executive brief ({output_language})")
        st.markdown(f"🎯 **Objective:** `{active_purpose}`")
        st.markdown(f"⏳ **Horizon:** `{active_time}` | 📡 **Channels:** `{active_chans}`")
        if brief.get("verified_coverage_metric"):
            st.caption(f"📊 **Coverage scope:** {brief['verified_coverage_metric']}")
            st.caption(f"📈 **Audience reach:** {brief.get('total_combined_audience_reach', '')}")
    
    with header_col2:
        export_format = st.selectbox(
            "Export document format:",
            ["PDF Document (.pdf)", "Microsoft Word (.docx)", "Markdown (.md)"],
            key="export_format_top"
        )
        
        if "PDF" in export_format:
            st.download_button("💚 Download PDF report", generate_pdf_brief(brief, exec_query, output_language, active_purpose, active_time, active_chans, is_strict_1page), f"WWM_Executive_Brief_{output_language}.pdf", "application/pdf", key="dl_pdf_top")
        elif "Word" in export_format:
            st.download_button("💚 Download Word document", generate_docx_brief(brief, exec_query, output_language, active_purpose, active_time, active_chans), f"WWM_Executive_Brief_{output_language}.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="dl_docx_top")
        else:
            st.download_button("💚 Download Markdown file", generate_markdown_brief(brief, exec_query, output_language, active_purpose, active_time, active_chans), f"WWM_Executive_Brief_{output_language}.md", "text/markdown", key="dl_md_top")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not brief.get("coverage_found", True):
        st.warning("⚠️ **Limited verified coverage:** No high-confidence media records matched your criteria. Unverified claims have been suppressed to preserve factual integrity.")
    else:
        st.subheader("1. Executive summary and strategic read")
        st.info(brief["headline_synthesis"])
        
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("2. Positioning and reputation")
            st.write(brief["sentiment_framing_read"])
            
            st.subheader("3. Spokesperson quotes and commentary")
            st.write(brief["subject_quoted_vs_reported"])
        with col2:
            st.subheader("4. Strategic engagement opportunities")
            st.warning(brief["engagement_opportunities"])
            
        st.divider()
        st.subheader("5. Key media records and verified audience reach")
        for item in brief["items"]:
            with st.expander(f"📌 {item['event_title']}"):
                st.markdown(f"**Category:** `{item['source_category']}` | **Prominence:** `{item['prominence_depth']}`")
                st.markdown(f"**Framing:** `{item['representation_mode']}` | **Key messages delivered:** `{item['key_message_delivered']}`")
                st.write(f"**Summary:** {item['core_event_summary']}")
                st.markdown("**Covering outlets and audience reach metrics:**")
                
                for outlet in item["covering_outlets"]:
                    url = outlet.get('canonical_source_url', '')
                    link_html = f"<br>🔗 <a href='{url}' target='_blank'>Review original canonical source link</a>" if is_valid_url(url) else ""
                    st.markdown(
                        f"📰 **{outlet['outlet_name']}** ({outlet['medium_type']}) | ✍️ *Byline:* {outlet['author_byline']} | 📅 *Date:* {outlet['publication_date']}<br>"
                        f"📊 *Audience reach:* **{outlet['audience_reach_metrics']}**{link_html}",
                        unsafe_allow_html=True
                    )
    
    st.markdown(f"""
        <div class="disclaimer-box">
            <b>Executive verification note:</b> Generated with AI assistance and reviewed by WWM. Sources are linked where verified; confirm critical details against source before acting. Output language set to <b>{output_language}</b>.
        </div>
    """, unsafe_allow_html=True)
            
    st.markdown("</div>", unsafe_allow_html=True)
