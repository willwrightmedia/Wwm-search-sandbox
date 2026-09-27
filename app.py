"""
Kat Intelligence Engine — Medierkat & Markat
Patched build: explicit Developer API routing, robust key sanitization, guest entry,
grounded-URL verification, per-campaign domain dedup, reach maths, and active dashboard metrics.
"""

import copy
import datetime
import html
import io
import json
import re
from collections import Counter
from urllib.parse import urlparse

import altair as alt
import pandas as pd
import requests
import streamlit as st
from docx import Document
from fpdf import FPDF
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

try:
    from importlib.metadata import version as _pkg_version
    GENAI_VERSION = _pkg_version("google-genai")
except Exception:
    GENAI_VERSION = "unknown"

st.set_page_config(page_title="Kat Intelligence Engine", page_icon="🦦", layout="wide")

# ============================================================================
# 0. CONSTANTS
# ============================================================================
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODEL = "gemini-flash-latest"
NUM_PASSES = 4

PASS_ANGLES = [
    "official institutional media releases, announcements and newsroom posts",
    "mainstream national and international news mastheads, broadcasters and wire services",
    "trade press, specialist outlets and peer-reviewed publications",
    "social media and Reddit community discussion",
]

RECENCY_OPTIONS = {
    "Past 24 hours (Current cycle)": 1,
    "Past 7 days (Past week)": 7,
    "Past 30 days (Past month)": 30,
    "Past 12 months (Past year)": 365,
    "Past 5 years archive": 1826,
    "Custom time horizon": None,
}

JOURNAL_DOMAINS = (
    "sciencedirect.com", "springer.com", "link.springer.com", "nature.com", "wiley.com",
    "onlinelibrary.wiley.com", "tandfonline.com", "mdpi.com", "sagepub.com", "cell.com",
    "science.org", "pnas.org", "plos.org", "frontiersin.org", "iopscience.iop.org",
    "acs.org", "rsc.org", "bmj.com", "thelancet.com", "doi.org",
)

UNIT_MULTIPLIERS = {"trillion": 1e12, "billion": 1e9, "b": 1e9, "million": 1e6, "m": 1e6, "k": 1e3}

TITLE_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "rmit", "university", "research", "new",
    "breakthrough", "study", "report", "news", "media", "release", "campaign", "coverage",
}


# ============================================================================
# 1. SECRETS & AUTHENTICATION
# ============================================================================
def secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def sanitize_api_key(raw_key: str) -> str:
    """Removes non-printable ASCII and hidden whitespace chars like non-breaking space."""
    if not raw_key:
        return ""
    return re.sub(r"[^\w\.\-]", "", str(raw_key).strip())


def create_gemini_client(api_key: str) -> genai.Client:
    """Forces use of Google AI Studio Developer API and bypasses Vertex AI env variables."""
    clean_key = sanitize_api_key(api_key)
    return genai.Client(api_key=clean_key, vertexai=False, enterprise=False)


SESSION_DEFAULTS = {
    "authenticated_user": None,
    "active_app": "Medierkat (PR & Media)",
    "main_mode": "📊 Dashboard",
    "cumulative_brief": None,
    "executed_query": "",
    "pending_query": None,
    "saved_queries": [],
    "report_library": [],
}
for _k, _v in SESSION_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = copy.deepcopy(_v)

# ============================================================================
# 2. STYLES
# ============================================================================
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    .stApp { background-color: #14120F !important; color: #F2EDE3 !important; font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #1A1814 !important; border-right: 1px solid #2C2822 !important; }
    [data-testid="stSidebar"] * { color: #C6BCA9 !important; }

    div[data-baseweb="input"], div[data-baseweb="base-input"], div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
        background-color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important; border-radius: 2px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input, div[data-baseweb="textarea"] textarea, textarea {
        background-color: #F2EDE3 !important; color: #14120F !important; font-weight: 600 !important; font-size: 0.95rem !important; opacity: 1 !important;
    }
    div[data-baseweb="input"] input::placeholder, textarea::placeholder { color: #777777 !important; opacity: 0.8 !important; }
    div[data-baseweb="select"] * { color: #14120F !important; font-weight: 600 !important; }

    .st-key-prominent_search input {
        font-size: 1.35rem !important; padding: 14px 18px !important; height: 56px !important; font-weight: 600 !important;
    }
    .st-key-prominent_search button {
        height: 56px !important; font-size: 1.1rem !important; font-weight: 700 !important; letter-spacing: 0.15em !important;
        background-color: #C6BCA9 !important; color: #14120F !important; border: none !important; border-radius: 2px !important;
    }

    .metric-card {
        background-color: #1A1814; border: 1px solid #2C2822; padding: 18px 12px; border-radius: 2px; text-align: center;
        height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: center;
        min-height: 125px; box-sizing: border-box; overflow: hidden;
    }
    .metric-card h4 { font-size: clamp(0.65rem, 0.9vw, 0.75rem); letter-spacing: 0.12em; text-transform: uppercase; color: #C6BCA9; margin: 0 0 6px 0; }
    .metric-card h2 { font-size: clamp(0.95rem, 1.4vw, 1.25rem); font-weight: 600; color: #F2EDE3; line-height: 1.2; margin: 0 0 6px 0; word-break: break-word; }
    .metric-card .cap { font-size: clamp(0.6rem, 0.8vw, 0.7rem); color: #8A8275; margin: 0; }

    .stButton>button {
        background-color: transparent !important; color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        border-radius: 2px !important; padding: 0.65rem 1.4rem !important; font-size: 0.75rem !important;
        letter-spacing: 0.15em !important; text-transform: uppercase !important;
    }
    .stDownloadButton>button {
        background-color: #C6BCA9 !important; color: #14120F !important; font-weight: 600 !important;
        padding: 0.75rem 1.4rem !important; border-radius: 2px !important; border: none !important;
    }
    .disclaimer-box { background-color: #1A1814; border-left: 2px solid #C6BCA9; padding: 10px 14px; font-size: 0.8rem; color: #8A8275; margin-top: 20px; }

    [data-testid="stStatusWidget"] svg { display: none !important; }
    [data-testid="stStatusWidget"]::before { content: "🦦"; font-size: 1.2rem; }
    </style>
""", unsafe_allow_html=True)


def render_brand_meerkat_svg(width=45, height=75, fill_color="#F2EDE3"):
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 60 100" fill="{fill_color}" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M35 8c4 0 8 3 9 7 2-1 4 0 4 2s-2 4-5 4c-3 5-10 7-16 5-4-2-6-6-4-11 2-4 7-7 12-7z"/>'
        '<circle cx="40" cy="12" r="1.5" fill="#14120F"/>'
        '<path d="M28 22c2 7 2 17 1 30s-3 23-1 33c3 4 13 4 15 0-2-13-3-30-2-48 1-10-2-17-6-17z"/>'
        '<path d="M37 35c5 2 8 6 6 9-3 1-7-3-8-7z"/>'
        '<path d="M27 75C18 79 8 85 1 91c-2 2 0 3 3 1 9-6 17-11 25-13z"/>'
        '<path d="M26 81l-6 4h9zM39 81l7 4h-10z"/></svg>'
    )


# ============================================================================
# 3. LOGIN WALL
# ============================================================================
def render_login_wall():
    svg = render_brand_meerkat_svg(60, 100)
    st.markdown(
        f'<div style="text-align:center;padding:40px 0 24px 0;">{svg}'
        '<div style="font-family:\'Cormorant Garamond\',serif;font-size:3rem;color:#F2EDE3;margin-top:10px;">Kat Intelligence Engine</div>'
        '<div style="font-size:0.8rem;letter-spacing:0.25em;text-transform:uppercase;color:#8A8275;">MEDIERKAT &amp; MARKAT · TESTER SANDBOX</div></div>',
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1, 1])
    with col:
        if st.button("Enter as guest", width="stretch"):
            st.session_state.authenticated_user = {"username": "guest", "email": "guest", "full_name": "Guest tester"}
            st.rerun()
        st.caption("Prototype for invited testers. Please share feedback on anything confusing or incorrect.")


if st.session_state.authenticated_user is None:
    render_login_wall()
    st.stop()

current_user = st.session_state.authenticated_user


# ============================================================================
# 4. GENERAL HELPERS
# ============================================================================
def esc(value):
    return html.escape(str(value if value is not None else ""))


def normalize_str(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def is_valid_url(url):
    u = str(url or "").strip()
    return u.lower() not in {"none", "null", "", "n/a", "direct record input"} and u.startswith("http")


def normalize_url(url):
    if not is_valid_url(url):
        return ""
    p = urlparse(url.strip())
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}"


def domain_of(url):
    return urlparse(url.strip()).netloc.lower().removeprefix("www.") if is_valid_url(url) else ""


MONTH_OR_DAY_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\b\d{4}-\d{1,2}\b|\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",
    re.I,
)


def parse_date(value):
    if not value or str(value).strip().lower() in {"not stated", "unknown", "n/a", "none"}:
        return None
    if not MONTH_OR_DAY_RE.search(str(value)):
        return None
    try:
        d = pd.to_datetime(str(value), errors="coerce", dayfirst=True)
    except Exception:
        return None
    if d is None or pd.isna(d):
        return None
    if d.tzinfo is not None:
        d = d.tz_localize(None)
    return d


def extract_year_month_tuple(date_str):
    d = parse_date(date_str)
    if d is not None:
        return (d.year, d.month)
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", str(date_str))
    return (int(year_match.group(1)), 0) if year_match else (0, 0)


def parse_headline_reach(reach_str):
    head = str(reach_str or "").split("[")[0].lower()
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(trillion|billion|million|k|m|b)?\b", head)
    if not m:
        return 0.0
    try:
        return float(m.group(1).replace(",", "")) * UNIT_MULTIPLIERS.get(m.group(2) or "", 1)
    except ValueError:
        return 0.0


def format_audience(total):
    if total >= 1e9:
        return f"{total / 1e9:.2f} billion"
    if total >= 1e6:
        return f"{total / 1e6:.1f} million"
    if total > 0:
        return f"{total:,.0f}"
    return "Not available"


def calculate_header_metrics(items):
    outlets = [o for it in items for o in it.get("covering_outlets", [])]
    total = sum(parse_headline_reach(o.get("audience_reach_metrics")) for o in outlets)
    uncorroborated = sum(1 for o in outlets if "Uncorroborated" in o.get("verification_confidence", ""))
    metric = (
        f"Media index: {len(outlets)} media records across {len(items)} campaign milestones"
        f" ({uncorroborated} uncorroborated)"
        if outlets else "Media index: 0 media records found in the selected window"
    )
    reach = f"Potential audience (sum of outlet audiences, not deduplicated): {format_audience(total)}"
    return metric, reach, total


def is_official(out):
    return "official" in str(out.get("medium_type", "")).lower() or "release" in str(out.get("medium_type", "")).lower()


# ============================================================================
# 5. DEDUPLICATION & CAMPAIGN MERGING
# ============================================================================
DOMAIN_SUFFIXES = {"com", "net", "org", "edu", "gov", "co", "ac", "au", "uk", "nz", "io", "info", "id", "sg", "us", "ca", "in", "my", "vn"}
EMPTY_VALUES = {"", "none", "null", "n/a", "not stated", "not available", "unknown"}


def light_stem(word):
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def text_tokens(*texts):
    words = re.findall(r"[a-z0-9]+", " ".join(str(t or "") for t in texts).lower())
    return {light_stem(w) for w in words if len(w) > 2 and w not in TITLE_STOPWORDS}


def token_overlap(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def is_empty(value):
    return str(value if value is not None else "").strip().lower() in EMPTY_VALUES


def canon_outlet_name(name):
    s = re.sub(r"\(.*?\)|\[.*?\]", "", str(name or "").lower())
    s = re.sub(r"[^a-z0-9]", "", s)
    return s.removeprefix("the")


def domain_root(url):
    dom = domain_of(url)
    for prefix in ("m.", "amp.", "mobile.", "edition."):
        dom = dom.removeprefix(prefix)
    labels = [label for label in dom.split(".") if label and label not in DOMAIN_SUFFIXES]
    return labels[-1].removeprefix("the") if labels else ""


def outlet_identities(out):
    ids = {canon_outlet_name(out.get("outlet_name")), domain_root(out.get("canonical_source_url", ""))}
    return {i for i in ids if i}


def same_outlet(a, b):
    ua, ub = normalize_url(a.get("canonical_source_url")), normalize_url(b.get("canonical_source_url"))
    if ua and ua == ub:
        return True
    ia, ib = outlet_identities(a), outlet_identities(b)
    if ia & ib:
        return True
    for x in ia:
        for y in ib:
            short, long_ = sorted((x, y), key=len)
            if len(short) >= 3 and long_.startswith(short):
                return True
    return False


def article_urls(item):
    return {normalize_url(o.get("canonical_source_url")) for o in item.get("covering_outlets", [])
            if is_valid_url(o.get("canonical_source_url"))}


def month_gap(date_a, date_b):
    ya, ma = extract_year_month_tuple(date_a)
    yb, mb = extract_year_month_tuple(date_b)
    if not ya or not yb:
        return None, False
    if not ma or not mb:
        return (0 if ya == yb else 99), False
    return abs((ya * 12 + ma) - (yb * 12 + mb)), True


def items_match(a, b):
    if article_urls(a) & article_urls(b):
        return True
    gap, precise = month_gap(a.get("campaign_milestone_date"), b.get("campaign_milestone_date"))
    title_sim = token_overlap(text_tokens(a.get("event_title")), text_tokens(b.get("event_title")))
    if gap is None:
        return title_sim >= 0.6
    if gap > 1:
        return False
    body_sim = token_overlap(
        text_tokens(a.get("event_title"), a.get("key_message_delivered"), a.get("core_event_summary")),
        text_tokens(b.get("event_title"), b.get("key_message_delivered"), b.get("core_event_summary")),
    )
    shared_outlets = sum(1 for oa in a.get("covering_outlets", []) for ob in b.get("covering_outlets", []) if same_outlet(oa, ob))
    if not precise:
        return title_sim >= 0.4 or shared_outlets >= 2
    return title_sim >= 0.25 or body_sim >= 0.35 or shared_outlets >= 2


def merge_outlet_record(existing, new):
    if not is_valid_url(existing.get("canonical_source_url")) and is_valid_url(new.get("canonical_source_url")):
        existing["canonical_source_url"] = new["canonical_source_url"]
        existing["verification_confidence"] = new.get("verification_confidence", existing.get("verification_confidence"))
    for field in ("author_byline", "publication_date", "audience_reach_metrics", "doi", "medium_type"):
        if is_empty(existing.get(field)) and not is_empty(new.get(field)):
            existing[field] = new[field]
    if new.get("is_peer_reviewed_journal"):
        existing["is_peer_reviewed_journal"] = True


def add_outlets(target, outlets, used_urls=None):
    own_urls = article_urls(target)
    for o in outlets:
        url = normalize_url(o.get("canonical_source_url"))
        if used_urls is not None and url and url in used_urls and url not in own_urls:
            continue
        match = next((ex for ex in target["covering_outlets"] if same_outlet(ex, o)), None)
        if match:
            merge_outlet_record(match, o)
        else:
            target["covering_outlets"].append(o)
        if url:
            own_urls.add(url)
            if used_urls is not None:
                used_urls.add(url)


def merge_items(target, src, used_urls=None):
    add_outlets(target, src.get("covering_outlets", []), used_urls)
    ta = extract_year_month_tuple(target.get("campaign_milestone_date"))
    sa = extract_year_month_tuple(src.get("campaign_milestone_date"))
    if (not ta[0] and sa[0]) or (not ta[1] and sa[1]) or (ta[1] and sa[1] and sa < ta):
        target["campaign_milestone_date"] = src.get("campaign_milestone_date")
    for field in ("key_message_delivered", "core_event_summary", "co_represented_entities", "source_category"):
        if is_empty(target.get(field)) and not is_empty(src.get(field)):
            target[field] = src[field]
    if is_empty(target.get("reddit_community_sentiment_summary")) and not is_empty(src.get("reddit_community_sentiment_summary")):
        target["reddit_community_sentiment_summary"] = src["reddit_community_sentiment_summary"]


def next_campaign_id(items):
    nums = [int(m.group(1)) for it in items if (m := re.fullmatch(r"C(\d+)", str(it.get("campaign_id", ""))))]
    return f"C{max(nums, default=0) + 1}"


def merge_and_deduplicate_campaigns(existing_items, incoming_items):
    merged = copy.deepcopy(existing_items)
    for it in merged:
        it.setdefault("campaign_id", next_campaign_id(merged))
    used_urls = set().union(*(article_urls(it) for it in merged)) if merged else set()

    for new_item in copy.deepcopy(incoming_items):
        claimed = str(new_item.pop("existing_campaign_id", "NEW") or "NEW").strip().upper()
        target = next((m for m in merged if m.get("campaign_id") == claimed), None)
        if target is not None:
            gap, _ = month_gap(target.get("campaign_milestone_date"), new_item.get("campaign_milestone_date"))
            if gap is not None and gap > 12:
                target = None
        if target is None:
            target = next((m for m in merged if items_match(m, new_item)), None)

        if target is not None:
            merge_items(target, new_item, used_urls)
        else:
            outlets = new_item.get("covering_outlets", [])
            new_item["covering_outlets"] = []
            new_item["campaign_id"] = next_campaign_id(merged)
            add_outlets(new_item, outlets, used_urls)
            if new_item["covering_outlets"]:
                merged.append(new_item)

    changed = True
    while changed:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if items_match(merged[i], merged[j]):
                    merge_items(merged[i], merged[j])
                    del merged[j]
                    changed = True
                    break
            if changed:
                break

    for m in merged:
        m["covering_outlets"].sort(key=lambda o: 0 if is_official(o) else 1)
    merged.sort(key=lambda x: extract_year_month_tuple(x.get("campaign_milestone_date")), reverse=True)
    return merged


def existing_campaigns_block(items):
    rows = []
    for it in items[:60]:
        outlets = ", ".join(o.get("outlet_name", "") for o in it.get("covering_outlets", [])[:10])
        rows.append(f"{it.get('campaign_id')} | {it.get('campaign_milestone_date', '')} | {it.get('event_title', '')} | already listed: {outlets}")
    return "\n".join(rows) or "(none yet)"


# ============================================================================
# 6. NETWORK HELPERS
# ============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def resolve_redirect(uri):
    headers = {"User-Agent": "Mozilla/5.0 (KatIntelligenceEngine link check)"}
    try:
        r = requests.head(uri, allow_redirects=True, timeout=6, headers=headers)
        if r.status_code in (403, 405) or r.status_code >= 500:
            r = requests.get(uri, allow_redirects=True, timeout=8, headers=headers, stream=True)
            r.close()
        return r.url if r.status_code < 400 else ""
    except requests.RequestException:
        return ""


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_altmetric_score(doi):
    doi = str(doi or "").strip()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi, flags=re.I)
    if not doi.startswith("10."):
        return None
    try:
        r = requests.get(f"https://api.altmetric.com/v1/doi/{doi}", timeout=6)
        if r.status_code == 200:
            score = r.json().get("score")
            return round(float(score)) if score is not None else None
    except (requests.RequestException, ValueError):
        pass
    return None


def altmetric_allowed(out):
    dom = domain_of(out.get("canonical_source_url", ""))
    return bool(out.get("is_peer_reviewed_journal")) and dom.endswith(JOURNAL_DOMAINS)


def grounded_sources(response):
    sources = []
    try:
        for cand in response.candidates or []:
            gm = getattr(cand, "grounding_metadata", None)
            for chunk in (getattr(gm, "grounding_chunks", None) or []) if gm else []:
                web = getattr(chunk, "web", None)
                if web and getattr(web, "uri", None):
                    resolved = resolve_redirect(web.uri)
                    if resolved:
                        sources.append((getattr(web, "title", "") or "", resolved))
    except AttributeError:
        pass
    seen, unique = set(), []
    for title, url in sources:
        k = normalize_url(url)
        if k and k not in seen:
            seen.add(k)
            unique.append((title, url))
    return unique


def parse_json(text):
    clean = re.sub(r"^```(?:json)?\s*|\s*
