"""
Kat Intelligence Engine — Medierkat & Markat
Patched build: one-click guest entry, grounded-URL verification, no fabricated fallback,
per-campaign domain dedup, corrected reach maths, real dashboard data.
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
DEFAULT_MODEL = "gemini-3.8-flash"
FALLBACK_MODEL = "gemini-flash-latest"
NUM_PASSES = 4

# Each pass searches from a different angle so passes add coverage rather than repeat it.
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

    /* PROMINENT SEARCH BOX — st.container(key="prominent_search") renders with class st-key-prominent_search */
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
    """Returns a Timestamp only when the value includes at least a month; a bare year is not treated as 1 January."""
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
    """Parse only the headline figure, ignoring any [country: breakdown] that follows."""
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
    """Same article URL, same outlet name, or a name that matches the other's web domain."""
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
    """Months between two milestone dates. None if either has no year; month-less dates count as same-year matches."""
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
    """Add outlets to a campaign, merging any that are already listed. used_urls stops one article appearing in two campaigns."""
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
                target = None  # model's link is implausible; fall back to our own matching
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

    # Final sweep: merge campaigns that only became recognisable as the same event after later passes added detail.
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
# 6. NETWORK HELPERS (grounding redirect resolution, Altmetric lookup)
# ============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def resolve_redirect(uri):
    """Grounding URIs are often redirect links; resolve to the final article URL."""
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
    """Return [(title, resolved_url)] from the grounding metadata of a Gemini response."""
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
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip())
    return json.loads(clean) if clean else {}


# ============================================================================
# 6b. GEMINI CONNECTION HELPERS
# ============================================================================
def is_model_not_found(error):
    low = str(error).lower()
    return ("404" in low or "not_found" in low or "not found" in low) and "model" in low


def explain_gemini_error(error, model):
    low = str(error).lower()
    if "api key not valid" in low or "api_key_invalid" in low or "invalid api key" in low or "api key expired" in low:
        return "The Gemini API key isn't valid. Copy it again from Google AI Studio, making sure there are no spaces before or after it."
    if "401" in low or "unauthenticated" in low or "access_token_type" in low or "oauth" in low:
        return ("Google rejected the API key (401 unauthenticated). With the newer 'AQ.' keys from AI Studio this is usually "
                f"an outdated Gemini library (this app is running version {GENAI_VERSION}; it needs 2.25.0 or later), "
                "or a key that has been disabled. Reboot the app so it installs the latest library, and if it still fails, "
                "create a new key in AI Studio.")
    if is_model_not_found(error):
        return f"The model '{model}' isn't available to this API key. Try 'gemini-flash-latest' in the sidebar's Gemini model box."
    if "permission" in low or "403" in low:
        return "This API key isn't allowed to make the request. Check that the Gemini API is enabled for the key and that any restrictions on the key allow it."
    if "resource_exhausted" in low or "429" in low or "quota" in low or "rate limit" in low:
        return "Gemini's usage limit has been reached. Wait a minute and try again, or check your quota and billing in Google AI Studio."
    if "timed out" in low or "timeout" in low or "deadline" in low or "connection" in low or "unavailable" in low or "503" in low:
        return "Gemini didn't respond in time or is temporarily unavailable. Try again in a moment."
    if "validation error" in low or "json" in low or "expecting" in low:
        return "Gemini replied in an unexpected format. Trying again usually fixes this."
    return "Gemini returned an unexpected error. The technical detail below shows the exact message."


def ping_gemini(client, model):
    client.models.generate_content(model=model, contents="Reply with the single word OK.")


def test_gemini_connection(api_key, model):
    if not str(api_key or "").strip():
        return False, "No API key entered."
    try:
        client = genai.Client(api_key=str(api_key).strip())
        ping_gemini(client, model.strip())
        return True, f"Connected. The model '{model.strip()}' is working."
    except Exception as e:
        return False, explain_gemini_error(e, model.strip())


# ============================================================================
# 7. SCHEMAS
# ============================================================================
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(description="Publisher, broadcaster, social channel or institution, verbatim.")
    medium_type: str = Field(description="Media format, e.g. 'Official Primary Release', 'Online Press', 'Broadcast', 'Peer-Reviewed Journal', 'Reddit'.")
    author_byline: str = Field(default="not stated", description="Author or handle, or 'not stated'.")
    publication_date: str = Field(default="not stated", description="Publication date as stated in the source, e.g. '22 August 2023'.")
    original_language: str = Field(default="English")
    canonical_source_url: str = Field(default="None", description="MUST be copied exactly from the verified source list, otherwise 'None'.")
    audience_reach_metrics: str = Field(default="Not available", description="Published masthead audience figure, or 'Not available'. Never estimate.")
    country_domain_code: str = Field(default="Global")
    is_peer_reviewed_journal: bool = Field(default=False)
    doi: str = Field(default="None", description="DOI of the paper if this is a peer-reviewed journal article and the DOI appears in the research notes, else 'None'.")
    verification_confidence: str = Field(default="[Uncorroborated]", description="'[Verified Source]' only if the URL is in the verified list, else '[Uncorroborated]'.")


class EventCoverageItem(BaseModel):
    existing_campaign_id: str = Field(default="NEW", description="ID of the existing campaign this is the same news event as (e.g. 'C2'), or 'NEW'.")
    event_title: str
    campaign_milestone_date: str = Field(description="Month and year of the milestone, e.g. 'August 2023'.")
    source_category: str = ""
    prominence_depth: str = Field(default="Mention", description="Feature, Segment or Mention.")
    representation_mode: str = Field(default="Neutral", description="One or two words: Positive, Neutral, Negative, Mixed.")
    key_message_delivered: str = ""
    reddit_community_sentiment_summary: str = "N/A"
    co_represented_entities: str = ""
    core_event_summary: str = ""
    covering_outlets: list[CoverageOutlet] = []


class CoverageExtraction(BaseModel):
    coverage_found: bool = False
    items: list[EventCoverageItem] = []


class BriefSummary(BaseModel):
    headline_synthesis: str = Field(description="1-2 sentence executive overview.")
    sentiment_framing_read: str = Field(description="1-2 sentences on framing and positioning.")
    subject_quoted_vs_reported: str = Field(description="Direct quotes vs reported speech, only as evidenced in the items.")
    engagement_opportunities: str = Field(description="Strategic opportunities grounded in the items.")
    demographic_audience_profile: str = Field(description="Likely audience profile of the covering outlets.")


# ============================================================================
# 8. TOP BAR, SIDEBAR & HEADER
# ============================================================================
def clear_all_searches():
    st.session_state.cumulative_brief = None
    st.session_state.executed_query = ""


p_col1, p_col2, p_col3 = st.columns([2, 2, 1])
with p_col1:
    st.markdown(f"**Active session:** `{current_user['full_name']}` ({current_user['email']})")
with p_col2:
    st.selectbox("Platform app layer:", ["Medierkat (PR & Media)", "Markat (Marketing & Competitors)"], key="active_app")
with p_col3:
    if st.button("🔒 Log out", width="stretch"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

st.divider()
st.radio("Select mode:", ["📊 Dashboard", "📄 Brief", "📚 Library"], horizontal=True, key="main_mode")
main_mode = st.session_state.main_mode
is_markat = "Markat" in st.session_state.active_app
app_title = "Markat" if is_markat else "Medierkat"

with st.sidebar:
    st.markdown(f"### {app_title.upper()}")
    st.caption("COMPETITOR & CAMPAIGN INTELLIGENCE" if is_markat else "GLOBAL MEDIA INSIGHTS")
    st.divider()

    st.subheader("1. Intelligence engine")
    gemini_key = secret("GEMINI_API_KEY", "") or st.text_input("Gemini API key", type="password", placeholder="AIzaSy...")
    if secret("GEMINI_API_KEY"):
        st.caption("Using the API key from secrets.")
    model_name = st.text_input("Gemini model", value=secret("GEMINI_MODEL", DEFAULT_MODEL))
    st.caption(f"Gemini library version: {GENAI_VERSION}")
    if st.button("Test connection", key="test_connection"):
        ok, message = test_gemini_connection(gemini_key, model_name)
        (st.success if ok else st.error)(message)

    st.divider()
    st.subheader("2. Objective and scope")
    purposes = (
        ["Benchmark campaign impact vs key competitors", "Audit competitor share of voice & customer feedback",
         "Evaluate narrative positioning for upcoming launch", "CMO strategic performance briefing", "Custom strategic objective"]
        if is_markat else
        ["Demonstrate long-term impact & track record", "Identify emerging issue / early warning radar",
         "Track ongoing issue / crisis management", "Institutional board briefing / executive reporting", "Custom strategic objective"]
    )
    report_purpose_selected = st.selectbox("Primary objective", purposes)
    custom_purpose_input = ""
    if "Custom" in report_purpose_selected:
        custom_purpose_input = st.text_input("Specify custom objective:")
    active_report_purpose = custom_purpose_input.strip() or report_purpose_selected

    report_format_tier = st.selectbox("Report type", [
        "Executive leadership brief (1 page — C-Suite and Board)",
        "Strategic advisory report (2 pages — Subject experts)",
        "Comprehensive media operations report (up to 4 pages — PR and Media teams)",
        "Digital intelligence digest (up to 2 pages — Digital teams)",
    ])
    output_language = st.selectbox("Report output language", [
        "English", "French (Français)", "Spanish (Español)", "German (Deutsch)", "Mandarin Chinese (中文)",
        "Japanese (日本語)", "Indonesian (Bahasa Indonesia)", "Vietnamese (Tiếng Việt)", "Hindi (हिंदी)", "Arabic (العربية)",
    ])

    st.divider()
    st.subheader("3. Media channels and horizon")
    date_window = st.selectbox("Recency scope", list(RECENCY_OPTIONS.keys()), index=1)
    custom_range = None
    if RECENCY_OPTIONS[date_window] is None:
        today = datetime.date.today()
        custom_range = st.date_input("Custom range", value=(today - datetime.timedelta(days=90), today))

    social_media_focus = st.selectbox("Coverage scope", [
        "Include major news, verified social media, and Reddit forums combined",
        "Focus exclusively on major news and broadcast press",
        "Focus exclusively on high-reach social media channels & Reddit forums",
    ])
    selected_sources = st.multiselect(
        "Target channels",
        ["Global tier-1 press & wires", "Australian press & national broadcasters", "Major social media & Reddit discussions",
         "Southeast Asian press", "Official releases (.gov.au, .edu.au, ASX)"],
        default=["Global tier-1 press & wires", "Australian press & national broadcasters",
                 "Major social media & Reddit discussions", "Official releases (.gov.au, .edu.au, ASX)"],
    )
    st.divider()
    st.checkbox("Add repeat searches to current results", value=False, key="accumulate_results",
                help="Off: each search starts fresh. On: searching the same terms again adds new finds to the current brief, without duplicates.")
    st.button("Reset brief and clear all", on_click=clear_all_searches, key="sidebar_reset")


def window_bounds():
    today = datetime.date.today()
    days = RECENCY_OPTIONS.get(date_window)
    if days is None:
        if isinstance(custom_range, (tuple, list)) and len(custom_range) == 2:
            return custom_range[0], custom_range[1]
        return today - datetime.timedelta(days=90), today
    return today - datetime.timedelta(days=days), today


def window_label():
    start, end = window_bounds()
    return f"{start:%d %b %Y} to {end:%d %b %Y}"


header_svg = render_brand_meerkat_svg(45, 75)
subtitle = ("Strategic marketing performance, competitor benchmarking, and share of voice." if is_markat
            else "Strategic media intelligence, verified reach analytics, and cross-lingual reporting for leadership.")
st.markdown(
    f'<div style="display:flex;align-items:center;background-color:#1A1814;border:1px solid #2C2822;padding:24px 30px;border-radius:2px;margin-bottom:18px;">'
    f'<div style="margin-right:24px;flex-shrink:0;">{header_svg}</div><div>'
    f'<div style="font-size:0.75rem;letter-spacing:0.25em;text-transform:uppercase;color:#8A8275;margin-bottom:4px;">'
    f'{"COMPETITOR & CAMPAIGN INTELLIGENCE" if is_markat else "GLOBAL MEDIA INSIGHTS"}</div>'
    f'<div style="font-family:\'Cormorant Garamond\',serif;font-size:2.6rem;color:#F2EDE3;line-height:1;">{app_title}</div>'
    f'<div style="font-family:\'Cormorant Garamond\',serif;font-size:1.1rem;font-style:italic;color:#C6BCA9;margin-top:6px;">{subtitle}</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)


# ============================================================================
# 9. SYNTHESIS ENGINE (grounded search -> structured extraction -> verify -> merge)
# ============================================================================
def build_search_prompt(query, angle, custom_urls):
    start, end = window_bounds()
    channels = ", ".join(selected_sources) if selected_sources else "all channels"
    url_hint = ("\nAlso review these user-supplied URLs if relevant:\n" + "\n".join(custom_urls[:100])) if custom_urls else ""
    return f"""Today is {datetime.date.today():%d %B %Y}.
You are {app_title}'s senior media intelligence analyst. Use Google Search to find real coverage of: "{query}".
Focus this search on: {angle}.
Only include coverage published between {start:%d %B %Y} and {end:%d %B %Y}.
Channels of interest: {channels}. Coverage scope: {social_media_focus}.
For each item found, report: outlet name, headline, publication date, author if stated, the article URL,
what it said, whether spokespeople were quoted directly, and any DOI for journal articles.
Group coverage by the underlying news event or milestone (e.g. an official media release and the stories that followed it).
Report only what the search results show. If nothing is found in the window, say so plainly.{url_hint}"""


def build_extraction_prompt(query, research_text, sources, custom_urls, existing_items):
    src_lines = "\n".join(f"- {url}  ({title})" for title, url in sources)
    src_lines += "\n" + "\n".join(f"- {u}  (user supplied)" for u in custom_urls[:100]) if custom_urls else ""
    return f"""Convert the research notes below into JSON matching the schema, for the query "{query}".

RULES
1. canonical_source_url must be copied EXACTLY from the VERIFIED SOURCES list. If the matching article is not in that list, write 'None'.
2. verification_confidence is '[Verified Source]' only when canonical_source_url is from the list; otherwise '[Uncorroborated]'.
3. audience_reach_metrics: use only a published masthead audience figure you are confident of (headline figure first, optional
   country breakdown in square brackets). If unsure, write 'Not available'. Never estimate or invent.
4. is_peer_reviewed_journal is true only for articles in peer-reviewed journals. Put the DOI in 'doi' only if it appears in the notes.
5. Group outlets under the campaign milestone (news event) they covered. List the official release first.
6. {'Summarise Reddit/community discussion in reddit_community_sentiment_summary only if the notes describe it; otherwise N/A.' if is_markat else "Set reddit_community_sentiment_summary to 'N/A'."}
7. Exclude login, support, search-results and homepage URLs.
8. If the notes contain no real coverage, return coverage_found=false and an empty items list.
9. EXISTING CAMPAIGNS below were found in earlier passes. If an item is the same news event as one of them, set
   existing_campaign_id to that ID (e.g. 'C2') and list only outlets not already listed for it. Otherwise use 'NEW'.
   Never create a second campaign for an event that already exists, even if you would word its title differently.
10. Within one campaign, list each outlet only once. Group all coverage of the same event under one campaign.

EXISTING CAMPAIGNS
{existing_campaigns_block(existing_items)}

VERIFIED SOURCES
{src_lines or '(none)'}

RESEARCH NOTES
{research_text[:30000]}"""


def verify_and_filter(items, allowed_keys):
    start, end = window_bounds()
    kept_items = []
    for item in items:
        outlets = []
        for o in item.get("covering_outlets", []):
            url = o.get("canonical_source_url", "")
            if is_valid_url(url) and normalize_url(url) in allowed_keys:
                o["verification_confidence"] = "[Verified Source]"
            else:
                o["canonical_source_url"] = "None"
                o["verification_confidence"] = "[Uncorroborated]"
            d = parse_date(o.get("publication_date"))
            if d is not None and not (start <= d.date() <= end):
                continue  # outside the selected recency window
            if not altmetric_allowed(o):
                o["doi"] = "None"
            if not is_markat and "reddit" in str(o.get("outlet_name", "")).lower():
                continue  # Medierkat suppresses Reddit entirely
            outlets.append(o)
        if outlets:
            item["covering_outlets"] = outlets
            if not is_markat:
                item["reddit_community_sentiment_summary"] = "N/A"
            kept_items.append(item)
    return kept_items


def enrich_altmetric(items):
    for item in items:
        for o in item.get("covering_outlets", []):
            o["altmetric_score"] = fetch_altmetric_score(o.get("doi")) if altmetric_allowed(o) and o.get("doi") not in (None, "", "None") else None


def summarise(client, query, items, active_model):
    compact = [
        {k: it.get(k) for k in ("event_title", "campaign_milestone_date", "representation_mode", "key_message_delivered", "core_event_summary")}
        | {"outlets": [o.get("outlet_name") for o in it.get("covering_outlets", [])]}
        for it in items[:40]
    ]
    prompt = f"""Write an executive media brief summary in {output_language} for the query "{query}".
Objective: {active_report_purpose}. Report type: {report_format_tier}.
Base every statement strictly on these campaign milestones; do not add facts, dates or figures that are not present:
{json.dumps(compact, ensure_ascii=False)}"""
    resp = client.models.generate_content(
        model=active_model, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=BriefSummary, temperature=0.2),
    )
    return BriefSummary.model_validate(parse_json(resp.text) or {}).model_dump()


def run_synthesis_engine(query, custom_urls=None):
    custom_urls = custom_urls or []
    query = (query or "").strip()
    if not query and not custom_urls:
        st.error("Please enter a search query or paste article URLs.")
        return
    if not gemini_key.strip():
        st.error("No Gemini API key found. Enter it in the sidebar under '1. Intelligence engine', or add GEMINI_API_KEY to the app's secrets.")
        return

    keep_previous = st.session_state.get("accumulate_results", False) and query == st.session_state.get("brief_query")
    existing = (st.session_state.cumulative_brief or {}).get("items", []) if keep_previous else []
    accumulated = list(existing)
    allowed_keys = {normalize_url(u) for u in custom_urls if is_valid_url(u)}
    failures = []      # (pass label, plain-English reason, technical detail)
    fatal = None       # stops the search before any passes run
    notice = None
    active_model = model_name.strip()

    with st.status("Grounded search active", expanded=False) as status:
        # 1. Quick connection check, so a bad key or model name fails once with a clear reason
        status.update(label="Checking Gemini connection")
        client, error = None, None
        try:
            client = genai.Client(api_key=gemini_key.strip())
            ping_gemini(client, active_model)
        except Exception as e:
            error = e
        if error is not None and client is not None and is_model_not_found(error) and active_model != FALLBACK_MODEL:
            try:
                ping_gemini(client, FALLBACK_MODEL)
                notice = (f"The model '{active_model}' isn't available to this API key, so this search used "
                          f"'{FALLBACK_MODEL}' instead. You can change the model name in the sidebar.")
                active_model, error = FALLBACK_MODEL, None
            except Exception as e2:
                error = e2
        if error is not None:
            fatal = (explain_gemini_error(error, active_model), str(error))
            status.update(label="Search could not start", state="error")

        # 2. The four search passes
        if fatal is None:
            for idx, angle in enumerate(PASS_ANGLES[:NUM_PASSES], 1):
                status.update(label=f"Pass {idx} of {NUM_PASSES}: {angle}")
                try:
                    search_resp = client.models.generate_content(
                        model=active_model,
                        contents=build_search_prompt(query or "the supplied URLs", angle, custom_urls),
                        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.3),
                    )
                    research_text = search_resp.text or ""
                    sources = grounded_sources(search_resp)
                    allowed_keys |= {normalize_url(u) for _, u in sources}
                    if not research_text.strip():
                        continue
                    extract_resp = client.models.generate_content(
                        model=active_model,
                        contents=build_extraction_prompt(query, research_text, sources, custom_urls, accumulated),
                        config=types.GenerateContentConfig(response_mime_type="application/json",
                                                           response_schema=CoverageExtraction, temperature=0),
                    )
                    data = CoverageExtraction.model_validate(parse_json(extract_resp.text) or {}).model_dump()
                    new_items = verify_and_filter(data.get("items", []), allowed_keys)
                    accumulated = merge_and_deduplicate_campaigns(accumulated, new_items)
                except Exception as e:
                    failures.append((f"Pass {idx}", explain_gemini_error(e, active_model), str(e)))

            if len(failures) == NUM_PASSES:
                status.update(label="Search failed", state="error")
            else:
                summary = {
                    "headline_synthesis": f"No verified coverage matched '{query}' between {window_label()}.",
                    "sentiment_framing_read": "N/A", "subject_quoted_vs_reported": "N/A",
                    "engagement_opportunities": "N/A", "demographic_audience_profile": "N/A",
                }
                if accumulated:
                    status.update(label="Checking Altmetric and writing summary")
                    enrich_altmetric(accumulated)
                    try:
                        summary = summarise(client, query, accumulated, active_model)
                    except Exception as e:
                        failures.append(("Summary", explain_gemini_error(e, active_model), str(e)))
                        summary["headline_synthesis"] = "Summary could not be generated; see campaign milestones below."

                metric_str, reach_str, _ = calculate_header_metrics(accumulated)
                st.session_state.cumulative_brief = {
                    "coverage_found": bool(accumulated),
                    "verified_coverage_metric": metric_str,
                    "total_combined_audience_reach": reach_str,
                    **summary,
                    "items": accumulated,
                    "generated_at": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                }
                st.session_state.brief_query = query
                st.session_state.active_settings = {
                    "purpose": active_report_purpose, "tier": report_format_tier, "lang": output_language,
                    "time": f"{date_window} ({window_label()})", "cov": social_media_focus,
                    "channels": ", ".join(selected_sources) if selected_sources else "All channels",
                }
                status.update(label=f"Complete: {len(accumulated)} campaign milestones", state="complete")

    # Messages are shown outside the collapsed status box so they're always visible.
    if notice:
        st.info(notice)
    if fatal:
        st.error(f"**Search couldn't start.** {fatal[0]}")
        with st.expander("Technical detail"):
            st.code(fatal[1])
        return
    if failures:
        all_failed = len([f for f in failures if f[0].startswith("Pass")]) == NUM_PASSES
        reasons = list(dict.fromkeys(f[1] for f in failures))
        heading = ("**All search passes failed.** Nothing is shown rather than substituting unverified data."
                   if all_failed else "**Some passes had problems, so results may be incomplete.**")
        (st.error if all_failed else st.warning)(heading + "\n\n" + "\n\n".join(reasons))
        with st.expander("Technical detail"):
            st.code("\n\n".join(f"{label}: {detail}" for label, _, detail in failures))


# ============================================================================
# 10. SEARCH BAR
# ============================================================================
with st.container(key="prominent_search"):
    with st.form("top_search_form", border=False):
        s_col1, s_col2 = st.columns([3.5, 1])
        with s_col1:
            top_query = st.text_input("Enter target terms:", value=st.session_state.executed_query,
                                      placeholder="e.g. Rajeev Roychand or Telstra", label_visibility="collapsed")
        with s_col2:
            top_submitted = st.form_submit_button("🔍 Search", width="stretch")

if top_submitted:
    st.session_state.executed_query = top_query.strip()
    run_synthesis_engine(top_query)

if st.session_state.pending_query:
    q = st.session_state.pending_query
    st.session_state.pending_query = None
    st.session_state.executed_query = q
    run_synthesis_engine(q)


# ============================================================================
# 11. EXPORTS
# ============================================================================
def clean_pdf_text(text):
    if not text:
        return ""
    for orig, repl in {"“": '"', "”": '"', "‘": "'", "’": "'", "—": "-", "–": "-", "•": "*", "📌": ""}.items():
        text = str(text).replace(orig, repl)
    return text.encode("latin-1", "replace").decode("latin-1")


class PDFReport(FPDF):
    brand = "MEDIERKAT"

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(107, 107, 107)
        self.set_y(10)
        self.cell(0, 5, f"{self.brand}  |  EXECUTIVE BRIEF", align="R")

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(107, 107, 107)
        self.cell(0, 5, "Generated with AI assistance via Kat Intelligence Engine. Confirm critical details against source.", align="C")


def generate_pdf_brief(brief, query, s, export_limit):
    pdf = PDFReport()
    pdf.brand = app_title.upper()
    pdf.set_margins(18, 22, 18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    epw = pdf.epw

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(35, 35, 35)
    pdf.cell(epw, 6, clean_pdf_text(f"Executive Brief ({s['lang']})"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(107, 107, 107)
    pdf.multi_cell(epw, 3.8, clean_pdf_text(f"OBJECTIVE: {s['purpose'].upper()}"))
    pdf.set_font("Helvetica", "I", 7.5)
    for line in (f"Format: {s['tier']}", f"Scope: {query[:80]}  |  Recency: {s['time']}",
                 brief.get("verified_coverage_metric", ""), brief.get("total_combined_audience_reach", "")):
        pdf.multi_cell(epw, 3.8, clean_pdf_text(line))

    pdf.set_draw_color(198, 188, 169)
    pdf.ln(2)
    pdf.line(18, pdf.get_y(), 18 + epw, pdf.get_y())
    pdf.ln(3)

    sections = [
        ("1. Executive overview", "headline_synthesis"),
        ("2. Positioning & reputation", "sentiment_framing_read"),
        ("3. Spokesperson quotes and commentary", "subject_quoted_vs_reported"),
        ("4. Strategic opportunities", "engagement_opportunities"),
    ]
    for title, key in sections:
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(35, 35, 35)
        pdf.cell(epw, 5, title, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.multi_cell(epw, 4, clean_pdf_text(brief.get(key, "")))
        pdf.ln(2)

    items = brief.get("items", [])[:export_limit]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(epw, 5, f"5. Campaign milestones (newest first, {len(items)} shown)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    for item in items:
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.multi_cell(epw, 4, clean_pdf_text(f"* [{item.get('campaign_milestone_date', '')}] {item.get('event_title', '')}"))
        pdf.set_font("Helvetica", "", 7.5)
        pdf.multi_cell(epw, 3.5, clean_pdf_text(item.get("core_event_summary", "")))
        outlets = ", ".join(o.get("outlet_name", "") for o in item.get("covering_outlets", []))
        pdf.set_font("Helvetica", "I", 7)
        pdf.multi_cell(epw, 3.4, clean_pdf_text(f"Outlets: {outlets}"))
        pdf.ln(1.5)
    return bytes(pdf.output())


def outlet_line_md(o):
    link = f" — [Source]({o['canonical_source_url']})" if is_valid_url(o.get("canonical_source_url")) else " — *(no verified link)*"
    alt_s = f" | Altmetric: {o['altmetric_score']}" if o.get("altmetric_score") is not None else ""
    return f"  - **{o.get('outlet_name', '')}** ({o.get('medium_type', '')}, {o.get('publication_date', '')}) | Audience: {o.get('audience_reach_metrics', '')}{alt_s}{link}"


def generate_markdown_brief(brief, query, s, export_limit):
    md = f"# {app_title.upper()} EXECUTIVE BRIEF ({s['lang']})\n\n"
    md += f"**Objective:** {s['purpose']}  \n**Report type:** {s['tier']}  \n**Query:** {query}  \n"
    md += f"**Recency:** {s['time']}  \n**Coverage focus:** {s['cov']}  \n**Channels:** {s['channels']}  \n"
    md += f"**{brief.get('verified_coverage_metric', '')}**  \n**{brief.get('total_combined_audience_reach', '')}**\n\n"
    md += "## 1. Executive summary and strategic read\n\n"
    md += f"**Overview:** {brief.get('headline_synthesis', '')}\n\n"
    md += f"**Positioning and reputation:** {brief.get('sentiment_framing_read', '')}\n\n"
    md += f"**Spokesperson quotes:** {brief.get('subject_quoted_vs_reported', '')}\n\n"
    md += f"**Strategic opportunities:** {brief.get('engagement_opportunities', '')}\n\n"
    md += f"**Audience profile:** {brief.get('demographic_audience_profile', '')}\n\n---\n\n"
    items = brief.get("items", [])[:export_limit]
    md += f"## 2. Campaign milestones (newest first, {len(items)} shown)\n\n"
    for item in items:
        md += f"### [{item.get('campaign_milestone_date', '')}] {item.get('event_title', '')}\n"
        md += f"- **Prominence:** {item.get('prominence_depth', '')} | **Framing:** {item.get('representation_mode', '')}\n"
        md += f"- **Key message:** {item.get('key_message_delivered', '')}\n- **Summary:** {item.get('core_event_summary', '')}\n"
        if is_markat and item.get("reddit_community_sentiment_summary", "N/A") != "N/A":
            md += f"- **Community sentiment:** {item['reddit_community_sentiment_summary']}\n"
        for o in item.get("covering_outlets", []):
            md += outlet_line_md(o) + "\n"
        md += "\n"
    md += "\n*Generated with AI assistance via Kat Intelligence Engine. Confirm critical details against source.*\n"
    return md


def generate_docx_brief(brief, query, s, export_limit):
    doc = Document()
    doc.add_heading(f"{app_title.upper()} EXECUTIVE BRIEF ({s['lang']})", level=0)
    meta = doc.add_paragraph()
    for label, val in (("Objective: ", s["purpose"]), ("Query: ", query), ("Recency: ", s["time"]),
                       ("Coverage: ", brief.get("verified_coverage_metric", "")),
                       ("Audience: ", brief.get("total_combined_audience_reach", ""))):
        meta.add_run(label).bold = True
        meta.add_run(f"{val}\n")
    doc.add_heading("1. Executive summary and strategic read", level=1)
    for label, key in (("Overview", "headline_synthesis"), ("Positioning and reputation", "sentiment_framing_read"),
                       ("Spokesperson quotes", "subject_quoted_vs_reported"), ("Strategic opportunities", "engagement_opportunities"),
                       ("Audience profile", "demographic_audience_profile")):
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(brief.get(key, ""))
    items = brief.get("items", [])[:export_limit]
    doc.add_heading(f"2. Campaign milestones (newest first, {len(items)} shown)", level=1)
    for item in items:
        doc.add_heading(f"[{item.get('campaign_milestone_date', '')}] {item.get('event_title', '')}", level=2)
        doc.add_paragraph(item.get("core_event_summary", ""))
        for o in item.get("covering_outlets", []):
            url = o.get("canonical_source_url") if is_valid_url(o.get("canonical_source_url")) else "no verified link"
            doc.add_paragraph(f"{o.get('outlet_name', '')} ({o.get('medium_type', '')}, {o.get('publication_date', '')}) — {url}", style="List Bullet")
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ============================================================================
# 12. VIEWS
# ============================================================================
def metric_card(label, value, caption):
    st.markdown(f"<div class='metric-card'><h4>{esc(label)}</h4><h2>{esc(value)}</h2><p class='cap'>{esc(caption)}</p></div>",
                unsafe_allow_html=True)


def coverage_timeline(items):
    dates = [parse_date(o.get("publication_date")) for it in items for o in it.get("covering_outlets", [])]
    dates = [d for d in dates if d is not None]
    if not dates:
        return None, 0
    s = pd.Series(dates)
    span = (s.max() - s.min()).days
    freq, fmt = ("D", "%d %b") if span <= 60 else (("W", "%d %b %y") if span <= 365 else ("M", "%b %Y"))
    counts = s.dt.to_period(freq).value_counts().sort_index()
    df = pd.DataFrame({"Period": [p.start_time.strftime(fmt) for p in counts.index], "Media items": counts.values})
    undated = sum(1 for it in items for o in it.get("covering_outlets", [])) - len(dates)
    return df, undated


brief = st.session_state.cumulative_brief
settings = st.session_state.get("active_settings", {
    "purpose": active_report_purpose, "tier": report_format_tier, "lang": output_language,
    "time": date_window, "cov": social_media_focus, "channels": ", ".join(selected_sources),
})
exec_query = st.session_state.get("brief_query", st.session_state.executed_query)

if "Dashboard" in main_mode:
    st.subheader(f"📊 {app_title} tracking dashboard")
    if not brief:
        st.info("Run a search to populate the dashboard. All figures here come from your search results.")
    else:
        items = brief.get("items", [])
        df, undated = coverage_timeline(items)
        st.markdown("##### 📈 Coverage by publication date")
        if df is not None:
            chart = alt.Chart(df).mark_line(point=True, color="#C6BCA9").encode(
                x=alt.X("Period:O", sort=None, title=None),
                y=alt.Y("Media items:Q", title="Media items"),
                tooltip=["Period", "Media items"],
            ).properties(height=260).configure_axis(labelColor="#C6BCA9", titleColor="#F2EDE3", gridColor="#2C2822")
            st.altair_chart(chart, width="stretch")
            if undated:
                st.caption(f"{undated} media item(s) had no parseable publication date and are not charted.")
        else:
            st.caption("No dated coverage to chart.")

        outlets = [o for it in items for o in it.get("covering_outlets", [])]
        _, _, total_reach = calculate_header_metrics(items)
        channel = Counter(o.get("medium_type", "Unknown") for o in outlets).most_common(1)
        framing = Counter(it.get("representation_mode", "Unknown") for it in items).most_common(1)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            metric_card("Campaigns", f"{len(items)}", settings["time"])
        with c2:
            metric_card("Potential audience", format_audience(total_reach), "Sum of outlet audiences, not deduplicated")
        with c3:
            metric_card("Dominant channel", channel[0][0] if channel else "—", f"{channel[0][1]} of {len(outlets)} items" if channel else "")
        with c4:
            metric_card("Most common framing", framing[0][0] if framing else "—", f"{framing[0][1]} of {len(items)} campaigns" if framing else "")

elif "Brief" in main_mode:
    st.subheader("📄 Brief builder")
    st.caption("Uses the query in the search bar above. Optionally add article URLs to include and verify.")
    raw_urls_text = st.text_area("Paste URLs (one per line, up to 100):", height=100, placeholder="https://www.example.com/article...")
    custom_urls_input = [line.strip() for line in raw_urls_text.splitlines() if line.strip().startswith("http")][:100]
    if st.button("Generate executive brief"):
        run_synthesis_engine(st.session_state.executed_query, custom_urls_input)
        brief = st.session_state.cumulative_brief
        settings = st.session_state.get("active_settings", settings)
        exec_query = st.session_state.get("brief_query", exec_query)

else:
    st.subheader("📚 Library")
    st.markdown("#### Saved query deck (this session, max 50)")
    new_q = st.text_input("Add a topic:", placeholder="Brand, topic or keyword...")
    if st.button("➕ Add topic") and new_q.strip():
        if len(st.session_state.saved_queries) >= 50:
            st.warning("The deck is full (50 topics).")
        elif new_q.strip() not in st.session_state.saved_queries:
            st.session_state.saved_queries.append(new_q.strip())
            st.rerun()

    def queue_query(q):
        st.session_state.pending_query = q
        st.session_state.main_mode = "📄 Brief"

    for i, q in enumerate(st.session_state.saved_queries):
        qc1, qc2 = st.columns([5, 1])
        qc1.markdown(f"**{i + 1}.** `{q}`")
        qc2.button("Run", key=f"run_q_{i}", on_click=queue_query, args=(q,))

    st.markdown("#### Saved briefs (this session)")
    if brief and st.button("💾 Save current brief to library"):
        st.session_state.report_library.append({"query": exec_query, "saved": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                                                "brief": copy.deepcopy(brief), "settings": dict(settings)})
    for i, rep in enumerate(st.session_state.report_library):
        st.download_button(f"⬇️ {rep['query']} — {rep['saved']} (.md)",
                           generate_markdown_brief(rep["brief"], rep["query"], rep["settings"], len(rep["brief"].get("items", []))),
                           f"{app_title}_{normalize_str(rep['query'])[:30]}.md", "text/markdown", key=f"lib_dl_{i}")

# ============================================================================
# 13. BRIEF RENDER
# ============================================================================
if brief and ("Dashboard" in main_mode or "Brief" in main_mode):
    st.markdown("---")
    items = brief.get("items", [])
    h1, h2 = st.columns(2)
    with h1:
        st.caption(f"{app_title.upper()} EXECUTIVE BRIEF · generated {brief.get('generated_at', '')}")
        st.header(f"Executive brief ({settings['lang']})")
        st.markdown(f"🎯 **Objective:** {esc(settings['purpose'])}")
        st.markdown(f"📋 **Report type:** {esc(settings['tier'])}")
        st.markdown(f"⏳ **Recency:** {esc(settings['time'])}  \n🌐 **Coverage focus:** {esc(settings['cov'])}")
        st.markdown(f"📡 **Channels:** {esc(settings['channels'])}")
        st.caption(brief.get("verified_coverage_metric", ""))
        st.caption(brief.get("total_combined_audience_reach", ""))
    with h2:
        n = len(items)
        options = sorted({x for x in (5, 10, 25, 50) if x < n} | {n}) if n else [0]
        export_limit = st.selectbox("Campaigns to include in export:", options, index=len(options) - 1,
                                    format_func=lambda x: f"All {x} campaign milestones" if x == n else f"Newest {x} campaigns")
        export_format = st.selectbox("Export format:", ["PDF Document (.pdf)", "Microsoft Word (.docx)", "Markdown (.md)"])
        base = f"{app_title}_Executive_Brief"
        if "PDF" in export_format:
            st.download_button("Download PDF", generate_pdf_brief(brief, exec_query, settings, export_limit), f"{base}.pdf", "application/pdf")
        elif "Word" in export_format:
            st.download_button("Download Word document", generate_docx_brief(brief, exec_query, settings, export_limit), f"{base}.docx",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        else:
            st.download_button("Download Markdown", generate_markdown_brief(brief, exec_query, settings, export_limit), f"{base}.md", "text/markdown")

    if not items:
        st.warning(f"No verified coverage matched '{exec_query}' in {settings['time']}. Nothing has been substituted.")
    else:
        st.subheader("1. Executive summary and strategic read")
        st.info(brief.get("headline_synthesis", ""))
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("2. Positioning and reputation")
            st.write(brief.get("sentiment_framing_read", ""))
            st.subheader("3. Spokesperson quotes and commentary")
            st.write(brief.get("subject_quoted_vs_reported", ""))
        with c2:
            st.subheader("4. Strategic engagement opportunities")
            st.warning(brief.get("engagement_opportunities", ""))
            st.caption(f"Audience profile: {brief.get('demographic_audience_profile', '')}")

        st.divider()
        st.subheader(f"5. Campaign milestones ({len(items)}, newest first)")
        for i, item in enumerate(items, 1):
            with st.expander(f"📌 [{item.get('campaign_milestone_date', '')}] #{i}: {item.get('event_title', '')}"):
                st.markdown(f"**Category:** {esc(item.get('source_category'))} | **Prominence:** {esc(item.get('prominence_depth'))}")
                st.markdown(f"**Framing:** {esc(item.get('representation_mode'))} | **Key message:** {esc(item.get('key_message_delivered'))}")
                st.write(f"**Summary:** {item.get('core_event_summary', '')}")
                st.markdown("**Covering outlets:**")
                for o in item.get("covering_outlets", []):
                    url = o.get("canonical_source_url", "")
                    link = (f"<br>🔗 <a href='{esc(url)}' target='_blank' rel='noopener'>Open source</a>" if is_valid_url(url)
                            else "<br><i>No verified link</i>")
                    flag = f"<br>⚠️ <i>{esc(o.get('verification_confidence'))}</i>" if "Uncorroborated" in o.get("verification_confidence", "") else ""
                    alt_html = (f"<br>🏅 <b>Altmetric Attention Score:</b> {esc(o['altmetric_score'])}"
                                if o.get("altmetric_score") is not None else "")
                    st.markdown(
                        f"📰 <b>{esc(o.get('outlet_name'))}</b> ({esc(o.get('medium_type'))}) | ✍️ {esc(o.get('author_byline'))} | "
                        f"📅 {esc(o.get('publication_date'))}<br>📊 Audience: <b>{esc(o.get('audience_reach_metrics'))}</b>"
                        f"{alt_html}{flag}{link}",
                        unsafe_allow_html=True,
                    )
                if is_markat and item.get("reddit_community_sentiment_summary", "N/A") not in ("", "N/A"):
                    st.markdown("---")
                    st.markdown(f"💬 **Community & forum sentiment:** *{item['reddit_community_sentiment_summary']}*")

    st.markdown(
        f"<div class='disclaimer-box'><b>Verification note:</b> Generated with AI assistance via {app_title}. "
        "Links are shown only when they came from search grounding or were supplied by you. Audience figures are "
        "model-reported masthead figures and are summed without deduplication. Confirm critical details against source.</div>",
        unsafe_allow_html=True,
    )
