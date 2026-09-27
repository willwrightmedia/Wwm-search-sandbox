"""
Kat Intelligence Engine
- Medierkat: media intelligence (official releases, news, broadcast and trade press
only).
- Markat: social listening (how customers respond to brands' marketing, and brand vs
competitor sentiment).
Accounts: katadmin (creates own password on first visit) and katguest (password set by
katadmin).
"""

import copy
import datetime
import html
import io
import json
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import altair as alt
import bcrypt
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

# Medierkat: media only. Each selected channel is one search pass.
MEDIERKAT_CHANNELS = {
    "Official releases & newsrooms": "official media releases, newsroom posts and "
    "announcements published by the organisation "
    "itself, government bodies or stock exchanges",
    "News mastheads & wires": "national and international news mastheads, online news "
    "sites and wire services",
    "Broadcast (TV, radio, podcasts)": "television, radio and podcast coverage by "
    "broadcasters, including stories on their "
    "websites",
    "Trade & specialist press": "trade, industry and specialist press and newsletters",
}

# Markat: social only. Each selected channel is one search pass.
MARKAT_CHANNELS = {
    "Reddit": "Reddit threads and comments, in subreddits about the brand, its sector, "
    "and the relevant countries or cities",
    "X, Threads, Facebook, Instagram & LinkedIn": "public posts and comment threads on "
    "X (Twitter), Threads, Facebook, "
    "Instagram and LinkedIn, including "
    "replies to the brand's own campaign "
    "posts",
    "TikTok & YouTube": "TikTok and YouTube: customer and creator reactions to the "
    "brand's campaigns and ads, and the comment sections of "
    "campaign videos",
    "Community forums": "online community forums and brand community boards where "
    "customers discuss the brand (for example Whirlpool in "
    "Australia), including threads comparing it with competitors",
}

SOCIAL_DOMAINS = (
    "reddit.com",
    "redd.it",
    "x.com",
    "twitter.com",
    "threads.net",
    "threads.com",
    "facebook.com",
    "fb.com",
    "instagram.com",
    "linkedin.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "whirlpool.net.au",
    "quora.com",
    "bsky.app",
    "mastodon.social",
    "productreview.com.au",
)
SCHOLARLY_DOMAINS = (
    "sciencedirect.com",
    "springer.com",
    "wiley.com",
    "tandfonline.com",
    "mdpi.com",
    "doi.org",
    "sagepub.com",
    "frontiersin.org",
    "plos.org",
    "researchgate.net",
    "academia.edu",
    "arxiv.org",
)
SOCIAL_PLATFORM_RE = re.compile(
    r"\b(reddit|x|twitter|threads|facebook|instagram|linkedin|tiktok|youtube|forum|"
    r"forums|community|bluesky|mastodon|quora|whirlpool)\b",
    re.I,
)
NON_MEDIA_TYPE_WORDS = (
    "social",
    "reddit",
    "forum",
    "peer-reviewed",
    "peer reviewed",
    "academic",
    "scientific journal",
    "tiktok",
    "instagram",
    "facebook",
    "youtube comment",
    "twitter",
    "linkedin post",
)

COUNTRIES = [
    "Australia",
    "New Zealand",
    "Indonesia",
    "Singapore",
    "Malaysia",
    "Thailand",
    "Vietnam",
    "Philippines",
    "Japan",
    "South Korea",
    "China",
    "Hong Kong",
    "Taiwan",
    "India",
    "Pakistan",
    "Bangladesh",
    "United States",
    "Canada",
    "Mexico",
    "Brazil",
    "Argentina",
    "Chile",
    "Colombia",
    "United Kingdom",
    "Ireland",
    "France",
    "Germany",
    "Netherlands",
    "Belgium",
    "Spain",
    "Portugal",
    "Italy",
    "Switzerland",
    "Austria",
    "Sweden",
    "Norway",
    "Denmark",
    "Finland",
    "Poland",
    "Turkey",
    "United Arab Emirates",
    "Saudi Arabia",
    "Israel",
    "Egypt",
    "South Africa",
    "Nigeria",
    "Kenya",
]

RECENCY_OPTIONS = {
    "Past 24 hours (Current cycle)": 1,
    "Past 7 days (Past week)": 7,
    "Past 30 days (Past month)": 30,
    "Past 12 months (Past year)": 365,
    "Past 5 years archive": 1826,
    "Custom time horizon": None,
}

UNIT_MULTIPLIERS = {
    "trillion": 1e12,
    "billion": 1e9,
    "b": 1e9,
    "million": 1e6,
    "m": 1e6,
    "k": 1e3,
}

TITLE_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "into",
    "rmit",
    "university",
    "research",
    "new",
    "breakthrough",
    "study",
    "report",
    "news",
    "media",
    "release",
    "campaign",
    "coverage",
}

SENTIMENTS = ("Positive", "Negative", "Mixed", "Neutral")


# ============================================================================
# 1. SECRETS, GEMINI CLIENT & ACCOUNTS
# ============================================================================
def secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return default


def sanitize_api_key(raw_key):
    """Removes hidden characters picked up when copying a key (non-breaking spaces, zero-width characters, quotes)."""
    if not raw_key:
        return ""
    return re.sub(r"[^\w.\-]", "", str(raw_key).strip())


def create_gemini_client(api_key):
    """Forces the Google AI Studio Developer API, so Vertex AI environment variables can't redirect requests."""
    return genai.Client(
        api_key=sanitize_api_key(api_key), vertexai=False, enterprise=False
    )


ADMIN_USERNAME = "katadmin"
GUEST_USERNAME = "katguest"
SECRET_HASH_KEYS = {
    ADMIN_USERNAME: "KATADMIN_PASSWORD_HASH",
    GUEST_USERNAME: "KATGUEST_PASSWORD_HASH",
}
AUTH_STORE_PATH = Path("data/auth_store.json")
MIN_PASSWORD_LENGTH = 8
MAX_FAILED_LOGINS = 5
LOCKOUT_SECONDS = 60


def hash_password(plain):
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def check_password(plain, hashed):
    if len(str(plain).encode("utf-8")) > 72:
        return False
    try:
        return bcrypt.checkpw(str(plain).encode("utf-8"), str(hashed).encode("utf-8"))
    except (ValueError, TypeError):
        return False


def load_store():
    try:
        return json.loads(AUTH_STORE_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def save_store(data):
    AUTH_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = AUTH_STORE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(AUTH_STORE_PATH)


def get_password_hash(username):
    """A password set in the app takes priority (an empty value means switched off); a hash pinned in secrets is the fallback."""
    passwords = load_store().get("passwords", {})
    if username in passwords:
        return passwords[username] or None
    pinned = secret(SECRET_HASH_KEYS.get(username, ""), "")
    return str(pinned) if pinned else None


def set_password(username, plain):
    store = load_store()
    new_hash = hash_password(plain)
    store.setdefault("passwords", {})[username] = new_hash
    save_store(store)
    return new_hash


def disable_password(username):
    store = load_store()
    store.setdefault("passwords", {})[username] = ""
    save_store(store)


def password_problem(password, confirm, username):
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"The password must be at least {MIN_PASSWORD_LENGTH} characters."
    if len(password.encode("utf-8")) > 72:
        return "The password is too long. Please use 72 characters or fewer."
    if password != confirm:
        return "The two passwords don't match."
    if password.strip().lower() in (username, "password", "katpassword"):
        return "Please choose a less guessable password."
    return None


def authenticate(username, password):
    if username not in SECRET_HASH_KEYS:
        return None
    stored = get_password_hash(username)
    if stored and check_password(password, stored):
        is_admin = username == ADMIN_USERNAME
        return {
            "username": username,
            "full_name": "Administrator" if is_admin else "Guest tester",
            "is_admin": is_admin,
        }
    return None


SESSION_DEFAULTS = {
    "authenticated_user": None,
    "login_stage": "username",
    "login_username": "",
    "failed_logins": 0,
    "lock_until": 0.0,
    "pin_notice": None,
    "active_app": "Medierkat (Media intelligence)",
    "main_mode": "📊 Dashboard",
    "cumulative_brief": None,  # Medierkat results
    "markat_brief": None,  # Markat results
    "executed_query": "",
    "pending_query": None,
    "pending_scope": None,  # Markat: detected market scope awaiting confirmation
    "scope_request": False,
    "dig_request": None,
    "saved_queries": [],
    "report_library": [],
}
for _k, _v in SESSION_DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = copy.deepcopy(_v)
# ============================================================================
# 2. STYLES
# ============================================================================
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;1,400&family=Inter:wght@300;400;500;600&display=swap');

    .stApp { background-color: #14120F !important; color: #F2EDE3 !important;
    font-family: 'Inter', sans-serif !important; }
    [data-testid="stSidebar"] { background-color: #1A1814 !important; border-right: 1px
    solid #2C2822 !important; }
    [data-testid="stSidebar"] * { color: #C6BCA9 !important; }

    div[data-baseweb="input"], div[data-baseweb="base-input"],
    div[data-baseweb="select"] > div, div[data-baseweb="textarea"] {
        background-color: #F2EDE3 !important; border: 1px solid #C6BCA9 !important;
        border-radius: 2px !important;
    }
    div[data-baseweb="input"] input, div[data-baseweb="base-input"] input,
    div[data-baseweb="textarea"] textarea, textarea {
        background-color: #F2EDE3 !important; color: #14120F !important; font-weight:
        600 !important; font-size: 0.95rem !important; opacity: 1 !important;
    }
    div[data-baseweb="input"] input::placeholder, textarea::placeholder { color: #777777
    !important; opacity: 0.8 !important; }
    div[data-baseweb="select"] * { color: #14120F !important; font-weight: 600
    !important; }

    /* PROMINENT SEARCH BOX — st.container(key="prominent_search") renders with class
    st-key-prominent_search */
    .st-key-prominent_search input {
        font-size: 1.35rem !important; padding: 14px 18px !important; height: 56px
        !important; font-weight: 600 !important;
    }
    .st-key-prominent_search button {
        height: 56px !important; font-size: 1.1rem !important; font-weight: 700
        !important; letter-spacing: 0.15em !important;
        background-color: #C6BCA9 !important; color: #14120F !important; border: none
        !important; border-radius: 2px !important;
    }

    .metric-card {
        background-color: #1A1814; border: 1px solid #2C2822; padding: 18px 12px;
        border-radius: 2px; text-align: center;
        height: 100%; display: flex; flex-direction: column; justify-content: center;
        align-items: center;
        min-height: 125px; box-sizing: border-box; overflow: hidden;
    }
    .metric-card h4 { font-size: clamp(0.65rem, 0.9vw, 0.75rem); letter-spacing: 0.12em;
    text-transform: uppercase; color: #C6BCA9; margin: 0 0 6px 0; }
    .metric-card h2 { font-size: clamp(0.95rem, 1.4vw, 1.25rem); font-weight: 600;
    color: #F2EDE3; line-height: 1.2; margin: 0 0 6px 0; word-break: break-word; }
    .metric-card .cap { font-size: clamp(0.6rem, 0.8vw, 0.7rem); color: #8A8275; margin:
    0; }

    .stButton>button {
        background-color: transparent !important; color: #F2EDE3 !important; border: 1px
        solid #C6BCA9 !important;
        border-radius: 2px !important; padding: 0.65rem 1.4rem !important; font-size:
        0.75rem !important;
        letter-spacing: 0.15em !important; text-transform: uppercase !important;
    }
    .stDownloadButton>button {
        background-color: #C6BCA9 !important; color: #14120F !important; font-weight:
        600 !important;
        padding: 0.75rem 1.4rem !important; border-radius: 2px !important; border: none
        !important;
    }
    .disclaimer-box { background-color: #1A1814; border-left: 2px solid #C6BCA9;
    padding: 10px 14px; font-size: 0.8rem; color: #8A8275; margin-top: 20px; }

    [data-testid="stStatusWidget"] svg { display: none !important; }
    [data-testid="stStatusWidget"]::before { content: "🦦"; font-size: 1.2rem; }
    </style>
""",
    unsafe_allow_html=True,
)


def render_brand_meerkat_svg(width=45, height=75, fill_color="#F2EDE3"):
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 60 100" '
        f'fill="{fill_color}" xmlns="http://www.w3.org/2000/svg">'
        '<path d="M35 8c4 0 8 3 9 7 2-1 4 0 4 2s-2 4-5 4c-3 5-10 7-16 5-4-2-6-6-4-11 '
        '2-4 7-7 12-7z"/>'
        '<circle cx="40" cy="12" r="1.5" fill="#14120F"/>'
        '<path d="M28 22c2 7 2 17 1 30s-3 23-1 33c3 4 13 4 15 0-2-13-3-30-2-48 '
        '1-10-2-17-6-17z"/>'
        '<path d="M37 35c5 2 8 6 6 9-3 1-7-3-8-7z"/>'
        '<path d="M27 75C18 79 8 85 1 91c-2 2 0 3 3 1 9-6 17-11 25-13z"/>'
        '<path d="M26 81l-6 4h9zM39 81l7 4h-10z"/></svg>'
    )


# ============================================================================
# 4. GENERAL HELPERS
# ============================================================================
def esc(value):
    return html.escape(str(value if value is not None else ""))


def normalize_str(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def is_valid_url(url):
    u = str(url or "").strip()
    return u.lower() not in {
        "none",
        "null",
        "",
        "n/a",
        "direct record input",
    } and u.startswith("http")


def normalize_url(url):
    if not is_valid_url(url):
        return ""
    p = urlparse(url.strip())
    return f"{p.netloc.lower().removeprefix('www.')}{p.path.rstrip('/')}"


def domain_of(url):
    return (
        urlparse(url.strip()).netloc.lower().removeprefix("www.")
        if is_valid_url(url)
        else ""
    )


MONTH_OR_DAY_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b|\b\d{4}-\d{1,2}\b|"
    r"\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b",
    re.I,
)


def parse_date(value):
    """Returns a Timestamp only when the value includes at least a month; a bare year is not treated as 1 January."""
    if not value or str(value).strip().lower() in {
        "not stated",
        "unknown",
        "n/a",
        "none",
    }:
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
        return float(m.group(1).replace(",", "")) * UNIT_MULTIPLIERS.get(
            m.group(2) or "", 1
        )
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
    uncorroborated = sum(
        1 for o in outlets if "Uncorroborated" in o.get("verification_confidence", "")
    )
    metric = (
        f"Media index: {len(outlets)} media records across {len(items)} campaign "
        "milestones"
        f" ({uncorroborated} uncorroborated)"
        if outlets
        else "Media index: 0 media records found in the selected window"
    )
    reach = (
        "Potential audience (sum of outlet audiences, not deduplicated): "
        f"{format_audience(total)}"
    )
    return metric, reach, total


def is_official(out):
    return (
        "official" in str(out.get("medium_type", "")).lower()
        or "release" in str(out.get("medium_type", "")).lower()
    )


# ============================================================================
# 5. DEDUPLICATION & CAMPAIGN MERGING (Medierkat)
# ============================================================================
DOMAIN_SUFFIXES = {
    "com",
    "net",
    "org",
    "edu",
    "gov",
    "co",
    "ac",
    "au",
    "uk",
    "nz",
    "io",
    "info",
    "id",
    "sg",
    "us",
    "ca",
    "in",
    "my",
    "vn",
}
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
    labels = [
        label for label in dom.split(".") if label and label not in DOMAIN_SUFFIXES
    ]
    return labels[-1].removeprefix("the") if labels else ""


def outlet_identities(out):
    ids = {
        canon_outlet_name(out.get("outlet_name")),
        domain_root(out.get("canonical_source_url", "")),
    }
    return {i for i in ids if i}


def same_outlet(a, b):
    """Same article URL, same outlet name, or a name that matches the other's web domain."""
    ua, ub = normalize_url(a.get("canonical_source_url")), normalize_url(
        b.get("canonical_source_url")
    )
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
    return {
        normalize_url(o.get("canonical_source_url"))
        for o in item.get("covering_outlets", [])
        if is_valid_url(o.get("canonical_source_url"))
    }


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
    gap, precise = month_gap(
        a.get("campaign_milestone_date"), b.get("campaign_milestone_date")
    )
    title_sim = token_overlap(
        text_tokens(a.get("event_title")), text_tokens(b.get("event_title"))
    )
    if gap is None:
        return title_sim >= 0.6
    if gap > 1:
        return False
    body_sim = token_overlap(
        text_tokens(
            a.get("event_title"),
            a.get("key_message_delivered"),
            a.get("core_event_summary"),
        ),
        text_tokens(
            b.get("event_title"),
            b.get("key_message_delivered"),
            b.get("core_event_summary"),
        ),
    )
    shared_outlets = sum(
        1
        for oa in a.get("covering_outlets", [])
        for ob in b.get("covering_outlets", [])
        if same_outlet(oa, ob)
    )
    if not precise:
        return title_sim >= 0.4 or shared_outlets >= 2
    return title_sim >= 0.25 or body_sim >= 0.35 or shared_outlets >= 2


def merge_outlet_record(existing, new):
    if not is_valid_url(existing.get("canonical_source_url")) and is_valid_url(
        new.get("canonical_source_url")
    ):
        existing["canonical_source_url"] = new["canonical_source_url"]
        existing["verification_confidence"] = new.get(
            "verification_confidence", existing.get("verification_confidence")
        )
    for field in (
        "author_byline",
        "publication_date",
        "audience_reach_metrics",
        "medium_type",
    ):
        if is_empty(existing.get(field)) and not is_empty(new.get(field)):
            existing[field] = new[field]


def add_outlets(target, outlets, used_urls=None):
    """Add outlets to a campaign, merging any that are already listed. used_urls stops one article appearing in two campaigns."""
    own_urls = article_urls(target)
    for o in outlets:
        url = normalize_url(o.get("canonical_source_url"))
        if used_urls is not None and url and url in used_urls and url not in own_urls:
            continue
        match = next(
            (ex for ex in target["covering_outlets"] if same_outlet(ex, o)), None
        )
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
    for field in (
        "key_message_delivered",
        "core_event_summary",
        "co_represented_entities",
        "source_category",
    ):
        if is_empty(target.get(field)) and not is_empty(src.get(field)):
            target[field] = src[field]


def next_campaign_id(items):
    nums = [
        int(m.group(1))
        for it in items
        if (m := re.fullmatch(r"C(\d+)", str(it.get("campaign_id", ""))))
    ]
    return f"C{max(nums, default=0) + 1}"


def merge_and_deduplicate_campaigns(existing_items, incoming_items):
    merged = copy.deepcopy(existing_items)
    for it in merged:
        it.setdefault("campaign_id", next_campaign_id(merged))
    used_urls = set().union(*(article_urls(it) for it in merged)) if merged else set()

    for new_item in copy.deepcopy(incoming_items):
        claimed = (
            str(new_item.pop("existing_campaign_id", "NEW") or "NEW").strip().upper()
        )
        target = next((m for m in merged if m.get("campaign_id") == claimed), None)
        if target is not None:
            gap, _ = month_gap(
                target.get("campaign_milestone_date"),
                new_item.get("campaign_milestone_date"),
            )
            if gap is not None and gap > 12:
                target = (
                    None  # model's link is implausible; fall back to our own matching
                )
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

    # Final sweep: merge campaigns that only became recognisable as the same event after
    # later passes added detail.
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
    merged.sort(
        key=lambda x: extract_year_month_tuple(x.get("campaign_milestone_date")),
        reverse=True,
    )
    return merged


def existing_campaigns_block(items):
    rows = []
    for it in items[:60]:
        outlets = ", ".join(
            o.get("outlet_name", "") for o in it.get("covering_outlets", [])[:10]
        )
        rows.append(
            f"{it.get('campaign_id')} | {it.get('campaign_milestone_date', '')} | "
            f"{it.get('event_title', '')} | already listed: {outlets}"
        )
    return "\n".join(rows) or "(none yet)"


# ============================================================================
# 3. LOGIN
# ============================================================================
def render_pin_hint(username, pw_hash):
    key = SECRET_HASH_KEYS[username]
    st.markdown(
        "Streamlit Community Cloud clears the app's saved files whenever it restarts, "
        "redeploys or wakes from sleep. "
        "To keep this password, add this line to your app's **Secrets** and save:"
    )
    st.code(f'{key} = "{pw_hash}"', language="toml")
    consequence = (
        " and **katadmin** could be claimed again from the login page"
        if username == ADMIN_USERNAME
        else " and guests won't be able to log in until you set it again"
    )
    st.caption(
        "This is a scrambled form of the password, not the password itself, but keep "
        "it private. "
        f"Until it's added, a restart will clear the password{consequence}."
    )


def log_in(user):
    st.session_state.authenticated_user = user
    st.session_state.login_stage = "username"
    st.session_state.failed_logins = 0


def record_failed_login():
    time.sleep(0.5)
    st.session_state.failed_logins += 1
    if st.session_state.failed_logins >= MAX_FAILED_LOGINS:
        st.session_state.lock_until = time.time() + LOCKOUT_SECONDS
        st.session_state.failed_logins = 0


def render_login_wall():
    svg = render_brand_meerkat_svg(60, 100)
    st.markdown(
        f'<div style="text-align:center;padding:40px 0 24px 0;">{svg}'
        "<div style=\"font-family:'Cormorant Garamond',serif;font-size:3rem;"
        'color:#F2EDE3;margin-top:10px;">Kat Intelligence Engine</div>'
        '<div style="font-size:0.8rem;letter-spacing:0.25em;text-transform:uppercase;'
        'color:#8A8275;">MEDIERKAT &amp; MARKAT</div></div>',
        unsafe_allow_html=True,
    )
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        wait = st.session_state.lock_until - time.time()
        if wait > 0:
            st.error(
                f"Too many attempts. Please wait {int(wait) + 1} seconds and try again."
            )
            return

        stage = st.session_state.login_stage
        username = st.session_state.login_username

        if stage == "username":
            with st.form("username_form"):
                entered = st.text_input("Username")
                go = st.form_submit_button("Continue", width="stretch")
            if go and entered.strip():
                name = entered.strip().lower()
                st.session_state.login_username = name
                first_visit = name == ADMIN_USERNAME and not get_password_hash(
                    ADMIN_USERNAME
                )
                st.session_state.login_stage = "create" if first_visit else "password"
                st.rerun()

        elif stage == "create":
            st.markdown(f"**Welcome.** Create a password for **{ADMIN_USERNAME}**.")
            with st.form("create_password_form"):
                pw = st.text_input("New password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                create = st.form_submit_button(
                    "Create password and log in", width="stretch"
                )
            if create:
                problem = password_problem(pw, confirm, ADMIN_USERNAME)
                if get_password_hash(ADMIN_USERNAME):
                    st.session_state.login_stage = "password"
                    st.error(
                        "A password has already been created for this account. Please "
                        "log in."
                    )
                elif problem:
                    st.error(problem)
                else:
                    new_hash = set_password(ADMIN_USERNAME, pw)
                    log_in(authenticate(ADMIN_USERNAME, pw))
                    st.session_state.pin_notice = {
                        "username": ADMIN_USERNAME,
                        "hash": new_hash,
                    }
                    st.rerun()
            if st.button("Use a different username"):
                st.session_state.login_stage = "username"
                st.rerun()

        else:
            st.markdown(f"Username: **{html.escape(username)}**")
            with st.form("password_form"):
                pw = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", width="stretch")
            if submitted:
                user = authenticate(username, pw)
                if user:
                    log_in(user)
                    st.rerun()
                else:
                    record_failed_login()
                    st.error("That username or password isn't correct.")
            if st.button("Use a different username"):
                st.session_state.login_stage = "username"
                st.rerun()


if st.session_state.authenticated_user is None:
    render_login_wall()
    st.stop()

current_user = st.session_state.authenticated_user
is_admin = bool(current_user.get("is_admin"))


# ============================================================================
# 6. NETWORK HELPERS (grounding redirect resolution)
# ============================================================================
@st.cache_data(ttl=86400, show_spinner=False)
def resolve_redirect(uri):
    """Follows a grounding redirect to the real article or post.
    Sites like Reddit often refuse automated visits once reached; the redirect itself
    proves the link is real, so the final address is kept. Missing pages are dropped."""
    headers = {"User-Agent": "Mozilla/5.0 (KatIntelligenceEngine link check)"}
    status, final = None, ""
    try:
        r = requests.head(uri, allow_redirects=True, timeout=6, headers=headers)
        status, final = r.status_code, r.url
        if status in (403, 405) or status >= 500:
            r = requests.get(
                uri, allow_redirects=True, timeout=8, headers=headers, stream=True
            )
            r.close()
            status, final = r.status_code, r.url
    except requests.RequestException as e:
        resp = getattr(e, "response", None)
        if resp is not None:
            status, final = resp.status_code, resp.url
    if status is not None and status < 400:
        return final
    blocked = status in (401, 403, 429, 999)
    dom = domain_of(final)
    if blocked and dom and dom != domain_of(uri) and not dom.endswith("google.com"):
        return final
    return ""


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
    if (
        "api key not valid" in low
        or "api_key_invalid" in low
        or "invalid api key" in low
        or "api key expired" in low
    ):
        return (
            "The Gemini API key isn't valid. Copy it again from Google AI Studio, "
            "making sure there are no spaces before or after it."
        )
    if (
        "401" in low
        or "unauthenticated" in low
        or "access_token_type" in low
        or "oauth" in low
    ):
        return (
            "Google rejected the API key (401 unauthenticated). The key may have been "
            "disabled or revoked. "
            "Try a brand-new key from AI Studio, or a standard key from the Google "
            "Cloud console "
            "(APIs & Services > Credentials) restricted to the Generative Language API."
        )
    if is_model_not_found(error):
        return (
            f"The model '{model}' isn't available to this API key. Try "
            "'gemini-flash-latest' in the sidebar's Gemini model box."
        )
    if "permission" in low or "403" in low:
        return (
            "This API key isn't allowed to make the request. Check that the "
            "Gemini API is enabled for the key and that any restrictions on the "
            "key allow it."
        )
    if (
        "resource_exhausted" in low
        or "429" in low
        or "quota" in low
        or "rate limit" in low
    ):
        return (
            "Gemini's usage limit has been reached. Wait a minute and try again, "
            "or check your quota and billing in Google AI Studio."
        )
    if (
        "timed out" in low
        or "timeout" in low
        or "deadline" in low
        or "connection" in low
        or "unavailable" in low
        or "503" in low
    ):
        return (
            "Gemini didn't respond in time or is temporarily unavailable. Try "
            "again in a moment."
        )
    if "validation error" in low or "json" in low or "expecting" in low:
        return (
            "Gemini replied in an unexpected format. Trying again usually fixes this."
        )
    return f"Gemini returned an error: {str(error)[:300]}"


def ping_gemini(client, model):
    client.models.generate_content(
        model=model, contents="Reply with the single word OK."
    )


def test_gemini_connection(api_key, model):
    if not sanitize_api_key(api_key):
        return False, "No API key entered."
    try:
        client = create_gemini_client(api_key)
        ping_gemini(client, model.strip())
        return True, f"Connected. The model '{model.strip()}' is working."
    except Exception as e:
        return False, explain_gemini_error(e, model.strip())


# ============================================================================
# 6c. SOURCE FILTERS (keep Medierkat to media, Markat to social)
# ============================================================================
def domain_in(dom, domains):
    return bool(dom) and any(dom == d or dom.endswith("." + d) for d in domains)


def is_media_source(out):
    """Medierkat keeps media only: no social platforms, forums or academic journals."""
    dom = domain_of(out.get("canonical_source_url", ""))
    if domain_in(dom, SOCIAL_DOMAINS) or domain_in(dom, SCHOLARLY_DOMAINS):
        return False
    medium = str(out.get("medium_type", "")).lower()
    if any(word in medium for word in NON_MEDIA_TYPE_WORDS):
        return False
    return "reddit" not in str(out.get("outlet_name", "")).lower()


def is_social_source(src):
    """Markat keeps social only: verified links must be on a social platform or forum; unlinked items must name one."""
    platform = str(src.get("platform", ""))
    if is_valid_url(src.get("source_url")):
        dom = domain_of(src["source_url"])
        return domain_in(dom, SOCIAL_DOMAINS) or bool(
            re.search(r"\b(forum|forums|community)\b", platform, re.I)
        )
    return bool(SOCIAL_PLATFORM_RE.search(platform))


def anonymise_account(value, brands):
    """Never keep an individual's handle: subreddits, forums and brand pages are fine."""
    text = str(value or "").strip()
    if re.match(r"^(/?u/|@)", text, re.I):
        handle = normalize_str(text)
        if not any(normalize_str(b) and normalize_str(b) in handle for b in brands):
            return "Individual user"
    return text or "not stated"


# ============================================================================
# 6d. MARKAT TOPIC MERGING & DEDUPLICATION
# ============================================================================
def source_key(src):
    url = normalize_url(src.get("source_url"))
    if url:
        return "url:" + url
    return "post:" + "|".join(
        normalize_str(src.get(k))
        for k in ("platform", "community_or_account", "post_date")
    )


def topic_urls(topic):
    return {
        normalize_url(s.get("source_url"))
        for s in topic.get("sources", [])
        if is_valid_url(s.get("source_url"))
    }


def topics_match(a, b):
    if normalize_str(a.get("brand")) != normalize_str(b.get("brand")):
        return False
    if topic_urls(a) & topic_urls(b):
        return True
    brand_words = text_tokens(a.get("brand"))
    title_a = text_tokens(a.get("topic_title")) - brand_words
    title_b = text_tokens(b.get("topic_title")) - brand_words
    title_sim = token_overlap(title_a, title_b)
    gap, _ = month_gap(a.get("period"), b.get("period"))
    if gap is None:
        return title_sim >= 0.6
    if gap > 2:
        return False
    body_a = (
        text_tokens(a.get("topic_title"), a.get("sentiment_drivers"), a.get("summary"))
        - brand_words
    )
    body_b = (
        text_tokens(b.get("topic_title"), b.get("sentiment_drivers"), b.get("summary"))
        - brand_words
    )
    return title_sim >= 0.3 or token_overlap(body_a, body_b) >= 0.4


def add_sources(target, sources, used_urls=None):
    own_keys = {source_key(s) for s in target["sources"]}
    own_urls = topic_urls(target)
    for s in sources:
        url = normalize_url(s.get("source_url"))
        if used_urls is not None and url and url in used_urls and url not in own_urls:
            continue  # the same post already sits under another topic
        key = source_key(s)
        if key in own_keys:
            continue
        target["sources"].append(s)
        own_keys.add(key)
        if url:
            own_urls.add(url)
            if used_urls is not None:
                used_urls.add(url)


def merge_topic(target, src, used_urls=None):
    add_sources(target, src.get("sources", []), used_urls)
    s1, s2 = target.get("sentiment", "Neutral"), src.get("sentiment", "Neutral")
    if s1 != s2:
        target["sentiment"] = (
            s2 if s1 == "Neutral" else (s1 if s2 == "Neutral" else "Mixed")
        )
    if target.get("customer_type") != src.get("customer_type") and not is_empty(
        src.get("customer_type")
    ):
        target["customer_type"] = "Mixed"
    target["countries"] = sorted(
        set(target.get("countries", [])) | set(src.get("countries", []))
    )
    views = list(
        dict.fromkeys(
            target.get("representative_views", []) + src.get("representative_views", [])
        )
    )
    target["representative_views"] = views[:4]
    target["is_marketing_campaign"] = bool(
        target.get("is_marketing_campaign") or src.get("is_marketing_campaign")
    )
    ta, sa = extract_year_month_tuple(target.get("period")), extract_year_month_tuple(
        src.get("period")
    )
    if (not ta[0] and sa[0]) or (not ta[1] and sa[1]):
        target["period"] = src.get("period")
    for field in ("sentiment_drivers", "summary"):
        if is_empty(target.get(field)) and not is_empty(src.get(field)):
            target[field] = src[field]


def next_topic_id(topics):
    nums = [
        int(m.group(1))
        for t in topics
        if (m := re.fullmatch(r"T(\d+)", str(t.get("topic_id", ""))))
    ]
    return f"T{max(nums, default=0) + 1}"


def merge_social_topics(existing, incoming):
    merged = copy.deepcopy(existing)
    used_urls = set().union(*(topic_urls(t) for t in merged)) if merged else set()
    for new in copy.deepcopy(incoming):
        claimed = str(new.pop("existing_topic_id", "NEW") or "NEW").strip().upper()
        target = next(
            (
                t
                for t in merged
                if t.get("topic_id") == claimed
                and normalize_str(t.get("brand")) == normalize_str(new.get("brand"))
            ),
            None,
        )
        if target is None:
            target = next((t for t in merged if topics_match(t, new)), None)
        if target is not None:
            merge_topic(target, new, used_urls)
        else:
            sources = new.get("sources", [])
            new["sources"] = []
            new["topic_id"] = next_topic_id(merged)
            add_sources(new, sources, used_urls)
            if new["sources"]:
                merged.append(new)

    changed = True
    while changed:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                if topics_match(merged[i], merged[j]):
                    merge_topic(merged[i], merged[j])
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    merged.sort(key=lambda t: extract_year_month_tuple(t.get("period")), reverse=True)
    return merged


def existing_topics_block(topics):
    rows = [
        f"{t.get('topic_id')} | {t.get('brand')} | {t.get('period', '')} | "
        f"{t.get('topic_title', '')}"
        for t in topics[:60]
    ]
    return "\n".join(rows) or "(none yet)"


def match_brand(name, brands):
    """Maps the model's brand label onto the searched brand or a known competitor."""
    target = normalize_str(name)
    for b in brands:
        nb = normalize_str(b)
        if nb and (nb == target or nb in target or target in nb):
            return b
    return str(name or "").strip() or (brands[0] if brands else "")


# ============================================================================
# 7. SCHEMAS
# ============================================================================
class CoverageOutlet(BaseModel):
    outlet_name: str = Field(
        description="Publisher, broadcaster or institution, verbatim."
    )
    medium_type: str = Field(
        description="One of: Official Release, Online News, Print, Wire, Television, "
        "Radio, Podcast, Trade Press."
    )
    author_byline: str = Field(
        default="not stated", description="Author, or 'not stated'."
    )
    publication_date: str = Field(
        default="not stated",
        description="Publication date as stated in the source, e.g. '22 August 2023'.",
    )
    original_language: str = Field(default="English")
    canonical_source_url: str = Field(
        default="None",
        description="MUST be copied exactly from the verified source list, otherwise "
        "'None'.",
    )
    audience_reach_metrics: str = Field(
        default="Not available",
        description="Published masthead audience figure, or 'Not available'. Never "
        "estimate.",
    )
    country_domain_code: str = Field(default="Global")
    verification_confidence: str = Field(default="[Uncorroborated]")


class EventCoverageItem(BaseModel):
    existing_campaign_id: str = Field(
        default="NEW",
        description="ID of the existing campaign this is the same news event as (e.g. "
        "'C2'), or 'NEW'.",
    )
    event_title: str
    campaign_milestone_date: str = Field(
        description="Month and year of the milestone, e.g. 'August 2023'."
    )
    source_category: str = ""
    prominence_depth: str = Field(
        default="Mention", description="Feature, Segment or Mention."
    )
    representation_mode: str = Field(
        default="Neutral",
        description="One or two words: Positive, Neutral, Negative, Mixed.",
    )
    key_message_delivered: str = ""
    co_represented_entities: str = ""
    core_event_summary: str = ""
    covering_outlets: list[CoverageOutlet] = []


class CoverageExtraction(BaseModel):
    coverage_found: bool = False
    items: list[EventCoverageItem] = []


class BriefSummary(BaseModel):
    headline_synthesis: str = Field(description="1-2 sentence executive overview.")
    sentiment_framing_read: str = Field(
        description="1-2 sentences on framing and positioning."
    )
    subject_quoted_vs_reported: str = Field(
        description="Direct quotes vs reported speech, only as evidenced in the items."
    )
    engagement_opportunities: str = Field(
        description="Strategic opportunities grounded in the items."
    )
    demographic_audience_profile: str = Field(
        description="Likely audience profile of the covering outlets."
    )


class MarketScope(BaseModel):
    company_name: str = ""
    footprint: str = Field(
        default="unknown",
        description="'single-country', 'multi-country' or 'global', judged only by "
        "where consumers buy under this exact brand name.",
    )
    countries: list[str] = Field(
        default=[],
        description="Countries where consumers buy under this exact brand name. For a "
        "truly global consumer brand, its five largest consumer markets.",
    )
    languages: list[str] = Field(
        default=[], description="Main languages of those customers."
    )
    sub_brands: list[str] = Field(
        default=[],
        description="Customer-facing brands the company owns in those same countries, "
        "e.g. budget or online-only brands.",
    )
    other_named_subsidiaries: list[str] = Field(
        default=[],
        description="Subsidiaries in other countries trading under a different name.",
    )
    competitors: list[str] = Field(
        default=[], description="Up to five main competitors in those same countries."
    )
    rationale: str = Field(
        default="", description="One sentence explaining the footprint."
    )


class SocialSource(BaseModel):
    platform: str = Field(
        description="Reddit, X, Threads, Facebook, Instagram, LinkedIn, TikTok, "
        "YouTube, or the forum's name."
    )
    community_or_account: str = Field(
        default="not stated",
        description="Subreddit, forum, group or brand page. Never an individual "
        "person's username.",
    )
    country: str = Field(default="not stated")
    post_date: str = Field(
        default="not stated",
        description="Date of the post or thread, e.g. '14 March 2026'.",
    )
    engagement: str = Field(
        default="Not available",
        description="Upvotes, comments, likes or views only if stated in the notes. "
        "Never estimate.",
    )
    source_url: str = Field(
        default="None",
        description="MUST be copied exactly from the verified source list, otherwise "
        "'None'.",
    )
    verification_confidence: str = Field(default="[Uncorroborated]")


class SentimentTopic(BaseModel):
    existing_topic_id: str = Field(
        default="NEW",
        description="ID of the existing topic this is the same discussion as (e.g. "
        "'T3'), or 'NEW'.",
    )
    topic_title: str = Field(
        description="The marketing campaign, ad, promotion, launch, offer or customer "
        "issue being discussed."
    )
    brand: str = Field(
        description="The company the discussion is about: the searched brand or one of "
        "its competitors."
    )
    is_marketing_campaign: bool = Field(
        default=False,
        description="True if the topic is a proactive marketing activity by the brand: "
        "an ad, campaign, promotion, sponsorship, offer or launch.",
    )
    period: str = Field(
        description="Month and year of the discussion, e.g. 'March 2026'."
    )
    countries: list[str] = []
    sentiment: str = Field(description="Positive, Negative, Mixed or Neutral.")
    customer_type: str = Field(
        default="Mixed",
        description="'Existing customers', 'Prospective customers' or 'Mixed'.",
    )
    sentiment_drivers: str = Field(
        description="What people liked or disliked, in one or two sentences."
    )
    representative_views: list[str] = Field(
        default=[],
        description="Up to three short paraphrases of typical comments. No usernames "
        "or personal details.",
    )
    summary: str = ""
    sources: list[SocialSource] = []


class SocialExtraction(BaseModel):
    discussion_found: bool = False
    topics: list[SentimentTopic] = []


class MarkatSummary(BaseModel):
    headline_read: str = Field(
        description="1-2 sentences on overall customer sentiment towards the brand."
    )
    representativeness: str = Field(
        description="How representative the discussion appears: volume, spread across "
        "communities and platforms, and whether it looks like a small vocal group or "
        "broad sentiment."
    )
    campaign_reception: str = Field(
        description="How customers responded to the brand's proactive marketing "
        "campaigns."
    )
    competitor_comparison: str = Field(
        description="How sentiment towards the brand compares with its competitors."
    )
    pain_points_and_praise: str = Field(
        description="The main things customers complain about and praise."
    )
    opportunities: str = Field(
        description="Marketing opportunities and risks suggested by the discussion."
    )


# ============================================================================
# 8. TOP BAR, SIDEBAR & HEADER
# ============================================================================
LAYERS = ["Medierkat (Media intelligence)", "Markat (Social customer sentiment)"]
if st.session_state.active_app not in LAYERS:
    st.session_state.active_app = LAYERS[0]


def clear_all_searches():
    if st.session_state.active_app.startswith("Markat"):
        st.session_state.markat_brief = None
    else:
        st.session_state.cumulative_brief = None
    st.session_state.executed_query = ""


p_col1, p_col2, p_col3 = st.columns([2, 2, 1])
with p_col1:
    st.markdown(
        f"**Signed in as:** `{current_user['username']}`"
        + (" (admin)" if is_admin else "")
    )
with p_col2:
    st.selectbox("Platform app layer:", LAYERS, key="active_app")
with p_col3:
    if st.button("🔒 Log out", width="stretch"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

if is_admin and st.session_state.pin_notice:
    with st.expander("🔐 Keep your password after the app restarts", expanded=True):
        render_pin_hint(
            st.session_state.pin_notice["username"], st.session_state.pin_notice["hash"]
        )
        if st.button("Done, I've added it to Secrets"):
            st.session_state.pin_notice = None
            st.rerun()

st.divider()
st.radio(
    "Select mode:",
    ["📊 Dashboard", "📄 Brief", "📚 Library"],
    horizontal=True,
    key="main_mode",
)
main_mode = st.session_state.main_mode
is_markat = st.session_state.active_app.startswith("Markat")
app_title = "Markat" if is_markat else "Medierkat"

secret_key = sanitize_api_key(secret("GEMINI_API_KEY", ""))

# Defaults so both layers' variables always exist
media_markets, scope_mode, scope_countries, competitor_input = (
    ["Global"],
    "Auto-detect",
    [],
    "",
)

with st.sidebar:
    st.markdown(f"### {app_title.upper()}")
    st.caption("SOCIAL CUSTOMER SENTIMENT" if is_markat else "MEDIA INTELLIGENCE")
    st.divider()

    if is_admin:
        st.subheader("Intelligence engine")
        if secret_key:
            gemini_key = secret_key
            st.caption("✅ Using the Gemini API key from Secrets.")
        else:
            gemini_key = st.text_input(
                "Gemini API key", type="password", placeholder="AQ..."
            )
            st.caption("Add GEMINI_API_KEY to Secrets so guests can search.")
        model_name = st.text_input(
            "Gemini model", value=str(secret("GEMINI_MODEL", DEFAULT_MODEL))
        )
        st.caption(f"Gemini library version: {GENAI_VERSION}")
        if st.button("Test connection", key="test_connection"):
            ok, message = test_gemini_connection(gemini_key, model_name)
            (st.success if ok else st.error)(message)
        st.divider()
    else:
        gemini_key = secret_key
        model_name = str(secret("GEMINI_MODEL", DEFAULT_MODEL))
        if not gemini_key:
            st.warning("Search isn't set up yet. Please contact the administrator.")

    st.subheader("Objective and report")
    purposes = (
        [
            "Customer reaction to a marketing campaign",
            "Brand sentiment vs competitors",
            "Customer pain points and praise",
            "Pre-launch sentiment scan",
            "Custom objective",
        ]
        if is_markat
        else [
            "Demonstrate long-term impact & track record",
            "Identify emerging issue / early warning radar",
            "Track ongoing issue / crisis management",
            "Institutional board briefing / executive reporting",
            "Custom objective",
        ]
    )
    report_purpose_selected = st.selectbox("Primary objective", purposes)
    custom_purpose_input = (
        st.text_input("Specify custom objective:")
        if "Custom" in report_purpose_selected
        else ""
    )
    active_report_purpose = custom_purpose_input.strip() or report_purpose_selected

    report_format_tier = st.selectbox(
        "Report type",
        (
            [
                "Executive sentiment brief (1 page)",
                "Marketing team report (2 pages)",
                "Detailed social listening report (up to 4 pages)",
            ]
            if is_markat
            else [
                "Executive leadership brief (1 page — C-Suite and Board)",
                "Strategic advisory report (2 pages — Subject experts)",
                "Comprehensive media operations report (up to 4 pages — PR and Media "
                "teams)",
            ]
        ),
    )
    output_language = st.selectbox(
        "Report output language",
        [
            "English",
            "French (Français)",
            "Spanish (Español)",
            "German (Deutsch)",
            "Mandarin Chinese (中文)",
            "Japanese (日本語)",
            "Indonesian (Bahasa Indonesia)",
            "Vietnamese (Tiếng Việt)",
            "Hindi (हिंदी)",
            "Arabic (العربية)",
        ],
    )

    st.divider()
    st.subheader("Time frame")
    date_window = st.selectbox(
        "Recency scope", list(RECENCY_OPTIONS.keys()), index=2 if is_markat else 1
    )
    custom_range = None
    if RECENCY_OPTIONS[date_window] is None:
        today = datetime.date.today()
        custom_range = st.date_input(
            "Custom range", value=(today - datetime.timedelta(days=90), today)
        )

    st.divider()
    if is_markat:
        st.subheader("Social channels")
        selected_channels = st.multiselect(
            "Search these channels",
            list(MARKAT_CHANNELS.keys()),
            default=list(MARKAT_CHANNELS.keys()),
        )
        st.subheader("Market scope")
        scope_mode = st.selectbox(
            "Which countries' customers?",
            ["Auto-detect", "Single country", "Multiple countries", "Global"],
            help="Auto-detect first checks where the company actually sells: Telstra "
            "is Australia-only, Coca-Cola is global.",
        )
        if scope_mode == "Single country":
            scope_countries = [st.selectbox("Country", COUNTRIES, index=0)]
        elif scope_mode == "Multiple countries":
            scope_countries = st.multiselect(
                "Countries", COUNTRIES, default=["Australia", "New Zealand"]
            )
        if scope_mode == "Auto-detect":
            st.checkbox(
                "Let me confirm the market scope before searching",
                value=True,
                key="confirm_scope",
            )
        competitor_input = st.text_input(
            "Competitors (optional)",
            placeholder="e.g. Optus, TPG. Leave blank to auto-detect",
        )
    else:
        st.subheader("Media channels")
        selected_channels = st.multiselect(
            "Search these channels",
            list(MEDIERKAT_CHANNELS.keys()),
            default=list(MEDIERKAT_CHANNELS.keys()),
        )
        media_markets = st.multiselect(
            "Priority media markets", ["Global"] + COUNTRIES, default=["Global"]
        )

    st.divider()
    st.button(
        "Reset brief and clear all", on_click=clear_all_searches, key="sidebar_reset"
    )


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
subtitle = (
    "How customers respond to brands' marketing, and how they rate them against "
    "competitors, across social media."
    if is_markat
    else "Media intelligence from official releases, news, broadcast and trade press."
)
st.markdown(
    '<div style="display:flex;align-items:center;background-color:#1A1814;border:1px '
    'solid #2C2822;padding:24px 30px;border-radius:2px;margin-bottom:18px;">'
    f'<div style="margin-right:24px;flex-shrink:0;">{header_svg}</div><div>'
    '<div style="font-size:0.75rem;letter-spacing:0.25em;text-transform:uppercase;'
    'color:#8A8275;margin-bottom:4px;">'
    f'{"SOCIAL CUSTOMER SENTIMENT" if is_markat else "MEDIA INTELLIGENCE"}</div>'
    "<div style=\"font-family:'Cormorant Garamond',serif;font-size:2.6rem;"
    f'color:#F2EDE3;line-height:1;">{app_title}</div>'
    "<div style=\"font-family:'Cormorant Garamond',serif;font-size:1.1rem;"
    f'font-style:italic;color:#C6BCA9;margin-top:6px;">{subtitle}</div>'
    f"</div></div>",
    unsafe_allow_html=True,
)


# ============================================================================
# 9. SEARCH ENGINES
# ============================================================================
def connect_gemini(status):
    """Checks the key and model once. Returns (client, model, notice, fatal)."""
    active_model = (model_name or DEFAULT_MODEL).strip()
    status.update(label="Checking Gemini connection")
    client, error, notice = None, None, None
    try:
        client = create_gemini_client(gemini_key)
        ping_gemini(client, active_model)
    except Exception as e:
        error = e
    if (
        error is not None
        and client is not None
        and is_model_not_found(error)
        and active_model != FALLBACK_MODEL
    ):
        try:
            ping_gemini(client, FALLBACK_MODEL)
            notice = (
                f"The model '{active_model}' isn't available, so this search "
                f"used '{FALLBACK_MODEL}' instead."
            )
            active_model, error = FALLBACK_MODEL, None
        except Exception as e2:
            error = e2
    if error is not None:
        status.update(label="Search could not start", state="error")
        return (
            None,
            active_model,
            notice,
            (explain_gemini_error(error, active_model), str(error)),
        )
    return client, active_model, notice, None


def grounded_call(client, model, prompt):
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0.3
        ),
    )
    return resp.text or "", grounded_sources(resp)


def structured_call(client, model, prompt, schema, temperature=0):
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=temperature,
        ),
    )
    parsed = getattr(resp, "parsed", None)
    if isinstance(parsed, BaseModel):
        return parsed.model_dump()
    return schema.model_validate(parse_json(resp.text) or {}).model_dump()


def show_run_messages(notice, fatal, failures, num_passes):
    """Shown outside the collapsed status box so messages are always visible."""
    if notice:
        st.info(notice)
    if fatal:
        st.error(f"**Search couldn't start.** {fatal[0]}")
        with st.expander("Technical detail"):
            st.code(fatal[1])
        return
    if failures:
        all_failed = len([f for f in failures if f[0].startswith("Pass")]) == num_passes
        reasons = list(dict.fromkeys(f[1] for f in failures))
        heading = (
            "**All search passes failed.** Nothing is shown rather than substituting "
            "unverified data."
            if all_failed
            else "**Some steps had problems, so results may be incomplete.**"
        )
        (st.error if all_failed else st.warning)(
            heading + "\n\n" + "\n\n".join(reasons)
        )
        with st.expander("Technical detail"):
            st.code("\n\n".join(f"{label}: {detail}" for label, _, detail in failures))


def run_settings():
    return {
        "purpose": active_report_purpose,
        "tier": report_format_tier,
        "lang": output_language,
        "time": f"{date_window} ({window_label()})",
        "channels": ", ".join(selected_channels) or "All channels",
    }


def search_ready(query):
    if not query:
        st.error("Please enter a search term.")
        return False
    if not sanitize_api_key(gemini_key):
        st.error(
            "Search isn't set up: no Gemini API key found. "
            + (
                "Add GEMINI_API_KEY to Secrets or enter a key in the sidebar."
                if is_admin
                else "Please contact the administrator."
            )
        )
        return False
    return True


# ---------------------------------------------------------------- Medierkat
INITIAL_PASSES = 2
DEEPER = (
    ". Dig deeper than a first search: look for smaller, regional or less prominent "
    "sources that a quick search would miss"
)


def channel_labels(channels):
    return [c for c in selected_channels if c in channels] or list(channels)


def plan_passes(channels, extra_round=None):
    """A new search splits the selected channels across two passes.
    Each 'Find more' runs one pass on a single channel, rotating through them."""
    labels = channel_labels(channels)
    if extra_round is None:
        half = (len(labels) + 1) // 2
        groups = [g for g in (labels[:half], labels[half:]) if g][:INITIAL_PASSES]
        return [(" + ".join(g), "; and ".join(channels[c] for c in g)) for g in groups]
    label = labels[extra_round % len(labels)]
    return [(label, channels[label] + DEEPER)]


def next_extra_label(channels, brief):
    labels = channel_labels(channels)
    return labels[(brief or {}).get("extra_rounds", 0) % len(labels)]


def already_found_block(names):
    names = list(dict.fromkeys(str(n) for n in names if n and not is_empty(n)))[:40]
    if not names:
        return ""
    return (
        "\nThese sources have already been found, so look for different ones: "
        + "; ".join(names)
    )


def medierkat_search_prompt(query, angle, custom_urls, avoid=""):
    start, end = window_bounds()
    markets = ", ".join(media_markets) if media_markets else "Global"
    url_hint = (
        (
            "\nAlso review these user-supplied URLs if relevant:\n"
            + "\n".join(custom_urls[:100])
        )
        if custom_urls
        else ""
    )
    return f"""Today is {datetime.date.today():%d %B %Y}.
You are Medierkat's senior media intelligence analyst. Use Google Search to find real
media coverage of: "{query}".
Focus this search on: {angle}.
Priority media markets: {markets}.
Only include coverage published between {start:%d %B %Y} and {end:%d %B %Y}.
This is media coverage only. Do NOT include social media posts, Reddit or other forums,
blogs' comment sections, or academic journal articles.
For each item found, report: outlet name, headline, publication date, author if stated,
the article URL,
what it said, and whether spokespeople were quoted directly.
Group coverage by the underlying news event or milestone (e.g. an official media release
and the stories that followed it).
Report only what the search results show. If nothing is found in the window, say so
plainly.{url_hint}{avoid}"""


def medierkat_extraction_prompt(
    query, research_text, sources, custom_urls, existing_items
):
    src_lines = "\n".join(f"- {url}  ({title})" for title, url in sources)
    if custom_urls:
        src_lines += "\n" + "\n".join(
            f"- {u}  (user supplied)" for u in custom_urls[:100]
        )
    return f"""Convert the research notes below into JSON matching the schema, for the
    query "{query}".

RULES
1. canonical_source_url must be copied EXACTLY from the VERIFIED SOURCES list. If the
matching article is not in that list, write 'None'.
2. verification_confidence is '[Verified Source]' only when canonical_source_url is from
the list; otherwise '[Uncorroborated]'.
3. audience_reach_metrics: use only a published masthead audience figure you are
confident of. If unsure, write 'Not available'. Never estimate.
4. medium_type must be one of: Official Release, Online News, Print, Wire, Television,
Radio, Podcast, Trade Press.
5. Media only: leave out social media, Reddit, forums and academic journals entirely.
6. Group outlets under the news event they covered. List the official release first.
7. Exclude login, support, search-results and homepage URLs.
8. If the notes contain no real coverage, return coverage_found=false and an empty items
list.
9. EXISTING CAMPAIGNS below were found in earlier passes. If an item is the same news
event as one of them, set
   existing_campaign_id to that ID (e.g. 'C2') and list only outlets not already listed
   for it. Otherwise use 'NEW'.
   Never create a second campaign for an event that already exists, even if you would
   word its title differently.
10. Within one campaign, list each outlet only once.

EXISTING CAMPAIGNS
{existing_campaigns_block(existing_items)}

VERIFIED SOURCES
{src_lines or '(none)'}

RESEARCH NOTES
{research_text[:30000]}"""


def verify_media_items(items, allowed_keys):
    start, end = window_bounds()
    kept = []
    for item in items:
        outlets = []
        for o in item.get("covering_outlets", []):
            url = o.get("canonical_source_url", "")
            if is_valid_url(url) and normalize_url(url) in allowed_keys:
                o["verification_confidence"] = "[Verified Source]"
            else:
                o["canonical_source_url"] = "None"
                o["verification_confidence"] = "[Uncorroborated]"
            if not is_media_source(o):
                continue
            d = parse_date(o.get("publication_date"))
            if d is not None and not (start <= d.date() <= end):
                continue
            outlets.append(o)
        if outlets:
            item["covering_outlets"] = outlets
            kept.append(item)
    return kept


def summarise_media(client, model, query, items):
    compact = [
        {
            k: it.get(k)
            for k in (
                "event_title",
                "campaign_milestone_date",
                "representation_mode",
                "key_message_delivered",
                "core_event_summary",
            )
        }
        | {"outlets": [o.get("outlet_name") for o in it.get("covering_outlets", [])]}
        for it in items[:40]
    ]
    prompt = f"""Write an executive media brief summary in {output_language} for the
    query "{query}".
Objective: {active_report_purpose}. Report type: {report_format_tier}.
Base every statement strictly on these media coverage milestones; do not add facts,
dates or figures that are not present:
{json.dumps(compact, ensure_ascii=False)}"""
    return structured_call(client, model, prompt, BriefSummary, temperature=0.2)


def run_medierkat(query, custom_urls=None, more=False):
    custom_urls = custom_urls or []
    query = (query or "").strip()
    if not search_ready(query):
        return
    previous = st.session_state.cumulative_brief or {}
    more = more and previous.get("query") == query
    extra_round = previous.get("extra_rounds", 0) if more else None
    passes = plan_passes(MEDIERKAT_CHANNELS, extra_round)
    accumulated = list(previous.get("items", [])) if more else []
    before = sum(len(it["covering_outlets"]) for it in accumulated)
    avoid = (
        already_found_block(
            [o.get("outlet_name") for it in accumulated for o in it["covering_outlets"]]
        )
        if more
        else ""
    )
    allowed_keys = {normalize_url(u) for u in custom_urls if is_valid_url(u)}
    failures = []

    with st.status("Media search active", expanded=False) as status:
        client, model, notice, fatal = connect_gemini(status)
        if fatal is None:
            for idx, (label, angle) in enumerate(passes, 1):
                status.update(
                    label=(
                        f"Extra search: {label}"
                        if more
                        else f"Pass {idx} of {len(passes)}: {label}"
                    )
                )
                try:
                    research_text, sources = grounded_call(
                        client,
                        model,
                        medierkat_search_prompt(query, angle, custom_urls, avoid),
                    )
                    allowed_keys |= {normalize_url(u) for _, u in sources}
                    if not research_text.strip():
                        continue
                    data = structured_call(
                        client,
                        model,
                        medierkat_extraction_prompt(
                            query, research_text, sources, custom_urls, accumulated
                        ),
                        CoverageExtraction,
                    )
                    accumulated = merge_and_deduplicate_campaigns(
                        accumulated,
                        verify_media_items(data.get("items", []), allowed_keys),
                    )
                except Exception as e:
                    failures.append(
                        (f"Pass {idx}", explain_gemini_error(e, model), str(e))
                    )

            if len([f for f in failures if f[0].startswith("Pass")]) == len(passes):
                status.update(label="Search failed", state="error")
            else:
                summary = {
                    "headline_synthesis": "No verified media coverage matched "
                    f"'{query}' between {window_label()}.",
                    "sentiment_framing_read": "N/A",
                    "subject_quoted_vs_reported": "N/A",
                    "engagement_opportunities": "N/A",
                    "demographic_audience_profile": "N/A",
                }
                if accumulated:
                    status.update(label="Writing summary")
                    try:
                        summary = summarise_media(client, model, query, accumulated)
                    except Exception as e:
                        failures.append(
                            ("Summary", explain_gemini_error(e, model), str(e))
                        )
                        summary["headline_synthesis"] = (
                            "Summary could not be generated; see the coverage "
                            "milestones below."
                        )
                metric_str, reach_str, _ = calculate_header_metrics(accumulated)
                settings = run_settings()
                settings["cov"] = "Media only · priority markets: " + (
                    ", ".join(media_markets) or "Global"
                )
                st.session_state.cumulative_brief = {
                    "query": query,
                    "coverage_found": bool(accumulated),
                    "verified_coverage_metric": metric_str,
                    "total_combined_audience_reach": reach_str,
                    **summary,
                    "items": accumulated,
                    "generated_at": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                    "settings": settings,
                    "extra_rounds": (extra_round + 1) if more else 0,
                }
                status.update(
                    label=f"Complete: {len(accumulated)} coverage milestones",
                    state="complete",
                )
    show_run_messages(notice, fatal, failures, len(passes))
    if more and fatal is None and len(failures) < len(passes):
        added = sum(len(it["covering_outlets"]) for it in accumulated) - before
        report_added(added, "media item", passes[0][0])


# ---------------------------------------------------------------- Markat
def detect_market_scope(client, model, brand):
    research, _ = grounded_call(
        client,
        model,
        f"""Today is {datetime.date.today():%d %B %Y}.
Using Google Search, work out where customers buy products or services sold under the
brand name "{brand}" itself.
Ignore countries where the parent company operates only through subsidiaries trading
under a different name, or only in wholesale, enterprise or network infrastructure.
Report:
- the countries where consumers buy under the "{brand}" name (for a truly global
  consumer brand, its five largest consumer markets);
- whether that makes it single-country, multi-country or global;
- customer-facing sub-brands the company owns in those same countries (for example
  budget or online-only brands);
- subsidiaries in other countries that trade under a different name;
- up to five main competitors in those same countries;
- the main languages of those customers, and a one-sentence reason.""",
    )
    return structured_call(
        client,
        model,
        f'Convert these notes about "{brand}" into JSON matching the schema.\n\n'
        f"{research[:15000]}",
        MarketScope,
    )


def build_scope(
    brand,
    footprint,
    countries,
    competitors,
    sub_brands=(),
    languages=(),
    source="chosen by you",
    rationale="",
    other_named=(),
):
    countries = [c for c in dict.fromkeys(countries) if c]
    footprint = str(footprint or "unknown").lower()
    if len(countries) == 1:
        footprint = "single-country"
    elif len(countries) > 1 and footprint not in ("multi-country", "global"):
        footprint = "multi-country"
    elif not countries:
        footprint = "global" if footprint == "global" else "unknown"
    if footprint == "single-country":
        label = f"Single country: {countries[0]}"
    elif footprint == "multi-country":
        label = "Multiple countries: " + ", ".join(countries)
    elif footprint == "global":
        label = "Global" + (
            ": focusing on its largest markets, " + ", ".join(countries)
            if countries
            else ""
        )
    else:
        label = "Not determined: searching without a country focus"
    return {
        "brand": brand,
        "footprint": footprint,
        "countries": countries,
        "languages": list(languages),
        "competitors": [c for c in dict.fromkeys(competitors) if c][:6],
        "sub_brands": [s for s in dict.fromkeys(sub_brands) if s][:6],
        "other_named": list(other_named)[:6],
        "label": label,
        "source": source,
        "rationale": rationale,
    }


def resolve_scope(detected, brand):
    """Combines the sidebar choice with what was detected."""
    d = detected or {}
    typed = [c.strip() for c in competitor_input.split(",") if c.strip()]
    competitors = typed or d.get("competitors", [])[:5]
    common = dict(
        sub_brands=d.get("sub_brands", []),
        languages=d.get("languages", []),
        other_named=d.get("other_named_subsidiaries", []),
    )
    if scope_mode == "Single country":
        return build_scope(
            brand, "single-country", scope_countries[:1], competitors, **common
        )
    if scope_mode == "Multiple countries":
        return build_scope(
            brand, "multi-country", scope_countries, competitors, **common
        )
    if scope_mode == "Global":
        return build_scope(brand, "global", [], competitors, **common)
    return build_scope(
        brand,
        d.get("footprint", "unknown"),
        d.get("countries", [])[:5],
        competitors,
        source="auto-detected",
        rationale=d.get("rationale", ""),
        **common,
    )


def markat_search_prompt(brand, angle, scope, custom_urls, avoid=""):
    start, end = window_bounds()
    comps = ", ".join(scope["competitors"]) or "its main competitors"
    if scope["countries"]:
        geo = f"Focus on discussion by customers in {', '.join(scope['countries'])}."
    else:
        geo = "Include discussion from any country, noting the country where clear."
    langs = (
        f" Search in local languages where relevant ({', '.join(scope['languages'])})."
        if scope["languages"]
        else ""
    )
    url_hint = (
        (
            "\nAlso review these user-supplied links if relevant:\n"
            + "\n".join(custom_urls[:100])
        )
        if custom_urls
        else ""
    )
    return f"""Today is {datetime.date.today():%d %B %Y}.
You are Markat's social listening analyst. Use Google Search to find real public social
media discussion about "{brand}"
and its competitors ({comps}).
Focus this search on: {angle}.
Market scope: {scope['label']}. {geo}{langs}
Only include discussion posted between {start:%d %B %Y} and {end:%d %B %Y}.
Focus on how existing and prospective customers respond to the brand's proactive
marketing (advertising campaigns,
promotions, product launches, sponsorships and offers), and on their sentiment towards
the brand compared with its competitors.
This is social media only: do NOT use news articles, press releases or corporate media
as sources.
For each discussion found, report: platform, subreddit, forum or page, country if clear,
date, the URL, which brand and
which campaign or issue it concerns, overall sentiment, what drove it, whether
commenters appear to be existing or
prospective customers, and any engagement numbers shown (upvotes, comments, likes,
views).
Do not record the usernames or personal details of individual people.
Report only what the search results show. If nothing is found in the window, say so
plainly.{url_hint}{avoid}"""


def markat_extraction_prompt(
    brand, scope, research_text, sources, custom_urls, existing_topics, extra_rule=""
):
    src_lines = "\n".join(f"- {url}  ({title})" for title, url in sources)
    if custom_urls:
        src_lines += "\n" + "\n".join(
            f"- {u}  (user supplied)" for u in custom_urls[:100]
        )
    brands = ", ".join(
        [brand] + scope.get("sub_brands", []) + scope.get("competitors", [])
    )
    return f"""Convert the social listening notes below into JSON matching the
schema, for the brand "{brand}".

RULES
1. source_url must be copied EXACTLY from the VERIFIED SOURCES list. If the matching
post is not in that list, write 'None'.
2. verification_confidence is '[Verified Source]' only when source_url is from the
list; otherwise '[Uncorroborated]'.
3. brand must be one of: {brands}. Use a sub-brand's own name for discussion about it.
4. Social media and forums only. Leave out news articles, press releases and corporate
media entirely.
5. is_marketing_campaign is true only for the brand's own proactive marketing: ads,
campaigns, promotions, sponsorships, offers, launches.
6. sentiment must be exactly one of: Positive, Negative, Mixed, Neutral.
7. community_or_account: the subreddit, forum, group or brand page. Never an individual
person's username; write 'Individual user' instead.
8. representative_views: up to three short paraphrases of typical comments, with no
usernames or personal details.
9. engagement: only numbers stated in the notes. Otherwise 'Not available'. Never
estimate.
10. EXISTING TOPICS below were found in earlier passes. If a topic is the same
discussion as one of them, set existing_topic_id to that ID (e.g. 'T3') and list only
sources not already listed. Otherwise use 'NEW'. Never duplicate an existing topic.
11. List each source only once. If the notes contain no real social discussion, return
discussion_found=false and no topics.{extra_rule}

EXISTING TOPICS
{existing_topics_block(existing_topics)}

VERIFIED SOURCES
{src_lines or '(none)'}

NOTES
{research_text[:30000]}"""


def verify_social_topics(topics, allowed_keys, brands):
    start, end = window_bounds()
    kept = []
    for t in topics:
        sources = []
        for s in t.get("sources", []):
            url = s.get("source_url", "")
            if is_valid_url(url) and normalize_url(url) in allowed_keys:
                s["verification_confidence"] = "[Verified Source]"
            else:
                s["source_url"] = "None"
                s["verification_confidence"] = "[Uncorroborated]"
            if not is_social_source(s):
                continue
            d = parse_date(s.get("post_date"))
            if d is not None and not (start <= d.date() <= end):
                continue
            s["community_or_account"] = anonymise_account(
                s.get("community_or_account"), brands
            )
            sources.append(s)
        if sources:
            t["sources"] = sources
            t["brand"] = match_brand(t.get("brand"), brands)
            sentiment = str(t.get("sentiment", "")).strip().capitalize()
            t["sentiment"] = sentiment if sentiment in SENTIMENTS else "Mixed"
            kept.append(t)
    return kept


def summarise_social(client, model, brand, scope, topics):
    compact = [
        {
            k: t.get(k)
            for k in (
                "brand",
                "topic_title",
                "is_marketing_campaign",
                "period",
                "sentiment",
                "customer_type",
                "sentiment_drivers",
                "countries",
            )
        }
        | {
            "platforms": sorted({s.get("platform", "") for s in t.get("sources", [])}),
            "signal": signal_text(topic_signal(t)),
        }
        for t in topics[:50]
    ]
    prompt = f"""Write a customer sentiment brief in {output_language} for the brand
"{brand}".
Objective: {active_report_purpose}. Report type: {report_format_tier}.
Market scope: {scope['label']}.
Sub-brands: {', '.join(scope.get('sub_brands', [])) or 'none'}.
Competitors: {', '.join(scope.get('competitors', [])) or 'not identified'}.
Weigh each topic by its signal strength. Treat single-source topics as anecdotal, and
say plainly where sentiment seems to come from a small, vocal group rather than broad
discussion. Remember that social media over-represents digitally engaged and
dissatisfied customers.
Base every statement strictly on these social listening topics; do not add facts,
figures or campaigns that are not present:
{json.dumps(compact, ensure_ascii=False)}"""
    return structured_call(client, model, prompt, MarkatSummary, temperature=0.2)


SIGNAL_LEVELS = ["Single source", "Limited", "Moderate", "Widely discussed"]
SIGNAL_BARS = ["▮▯▯▯", "▮▮▯▯", "▮▮▮▯", "▮▮▮▮"]
ENGAGEMENT_RE = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*([km])?\b", re.I)


def engagement_total(sources):
    total = 0.0
    for s in sources:
        if is_empty(s.get("engagement")):
            continue
        for num, unit in ENGAGEMENT_RE.findall(str(s["engagement"])):
            try:
                value = float(num.replace(",", ""))
            except ValueError:
                continue
            total += value * {"k": 1e3, "m": 1e6}.get(unit.lower(), 1)
    return int(total)


def topic_signal(topic):
    """How widely a topic is discussed, from the number of sources, distinct
    communities and any stated engagement."""
    sources = topic.get("sources", [])
    n = len(sources)
    communities = {
        (normalize_str(s.get("platform")), normalize_str(s.get("community_or_account")))
        for s in sources
    }
    platforms = {normalize_str(s.get("platform")) for s in sources}
    engagement = engagement_total(sources)
    if n <= 1:
        level = 0
    elif len(communities) >= 5 or n >= 7:
        level = 3
    elif len(communities) <= 2 and n <= 3:
        level = 1
    else:
        level = 2
    if engagement >= 1000 and level < 3:
        level += 1
    return {
        "level": level,
        "label": SIGNAL_LEVELS[level],
        "bars": SIGNAL_BARS[level],
        "sources": n,
        "communities": len(communities),
        "platforms": len(platforms),
        "engagement": engagement,
    }


def signal_text(sig):
    text = (
        f"{sig['label']}: {sig['sources']} "
        f"{'source' if sig['sources'] == 1 else 'sources'} across "
        f"{sig['communities']} "
        f"{'community' if sig['communities'] == 1 else 'communities'}"
    )
    if sig["engagement"]:
        text += f", about {sig['engagement']:,} stated interactions"
    return text


def run_markat(
    query, custom_urls=None, more=False, scope_override=None, dig_topic=None
):
    custom_urls = custom_urls or []
    brand = (query or "").strip()
    if not search_ready(brand):
        return
    previous = st.session_state.markat_brief or {}
    same_brand = previous.get("query") == brand
    dig = dig_topic is not None and same_brand
    more = (more or dig) and same_brand
    topics = list(previous.get("topics", [])) if more else []
    before = sum(len(t["sources"]) for t in topics)
    extra_round = previous.get("extra_rounds", 0) if (more and not dig) else None

    extra_rule = ""
    if dig:
        target = next((t for t in topics if t.get("topic_id") == dig_topic), None)
        if target is None:
            st.warning("That topic is no longer in the brief.")
            return
        channels = channel_labels(MARKAT_CHANNELS)
        angle = (
            "these channels: "
            + "; ".join(MARKAT_CHANNELS[c] for c in channels)
            + f". Focus only on this specific topic about {target.get('brand')}: "
            f"'{target.get('topic_title')}'. What drove it: "
            f"{target.get('sentiment_drivers', '')}. Find more threads, comments and "
            "communities discussing it, to judge how widespread the reaction is"
        )
        passes = [(f"Dig deeper: {target.get('topic_title')}", angle)]
        avoid_sources = target["sources"]
        extra_rule = (
            f"\n12. Discussion of '{target.get('topic_title')}' belongs under existing "
            f"topic {dig_topic}: set existing_topic_id to {dig_topic} for it."
        )
    else:
        passes = plan_passes(MARKAT_CHANNELS, extra_round)
        avoid_sources = [s for t in topics for s in t["sources"]]
    avoid = (
        already_found_block(
            [
                (
                    s.get("source_url")
                    if is_valid_url(s.get("source_url"))
                    else f"{s.get('platform')} {s.get('community_or_account')}"
                )
                for s in avoid_sources
            ]
        )
        if more
        else ""
    )
    allowed_keys = {normalize_url(u) for u in custom_urls if is_valid_url(u)}
    failures, awaiting_confirmation = [], False

    with st.status("Social listening active", expanded=False) as status:
        client, model, notice, fatal = connect_gemini(status)
        if fatal is None:
            if more:
                scope = previous["scope"]
            elif scope_override is not None:
                scope = scope_override
            else:
                detected = None
                if scope_mode == "Auto-detect" or not competitor_input.strip():
                    status.update(
                        label="Assessing where customers buy this brand, and its "
                        "competitors"
                    )
                    try:
                        detected = detect_market_scope(client, model, brand)
                    except Exception as e:
                        failures.append(
                            ("Market scope", explain_gemini_error(e, model), str(e))
                        )
                scope = resolve_scope(detected, brand)
                if scope_mode == "Auto-detect" and st.session_state.get(
                    "confirm_scope", True
                ):
                    open_scope_confirmation(brand, scope, custom_urls)
                    awaiting_confirmation = True
                    status.update(
                        label="Market scope ready to confirm", state="complete"
                    )

            if not awaiting_confirmation:
                brands = [brand] + scope.get("sub_brands", []) + scope["competitors"]
                for idx, (label, angle) in enumerate(passes, 1):
                    status.update(
                        label=(
                            label
                            if dig
                            else (
                                f"Extra search: {label}"
                                if more
                                else f"Pass {idx} of {len(passes)}: {label}"
                            )
                        )
                    )
                    try:
                        research_text, sources = grounded_call(
                            client,
                            model,
                            markat_search_prompt(
                                brand, angle, scope, custom_urls, avoid
                            ),
                        )
                        allowed_keys |= {normalize_url(u) for _, u in sources}
                        if not research_text.strip():
                            continue
                        data = structured_call(
                            client,
                            model,
                            markat_extraction_prompt(
                                brand,
                                scope,
                                research_text,
                                sources,
                                custom_urls,
                                topics,
                                extra_rule,
                            ),
                            SocialExtraction,
                        )
                        topics = merge_social_topics(
                            topics,
                            verify_social_topics(
                                data.get("topics", []), allowed_keys, brands
                            ),
                        )
                    except Exception as e:
                        failures.append(
                            (f"Pass {idx}", explain_gemini_error(e, model), str(e))
                        )

                if len([f for f in failures if f[0].startswith("Pass")]) == len(passes):
                    status.update(label="Search failed", state="error")
                else:
                    summary = {
                        "headline_read": f"No verified social discussion about "
                        f"'{brand}' was found between {window_label()}.",
                        "representativeness": "N/A",
                        "campaign_reception": "N/A",
                        "competitor_comparison": "N/A",
                        "pain_points_and_praise": "N/A",
                        "opportunities": "N/A",
                    }
                    if topics:
                        status.update(label="Writing summary")
                        try:
                            summary = summarise_social(
                                client, model, brand, scope, topics
                            )
                        except Exception as e:
                            failures.append(
                                ("Summary", explain_gemini_error(e, model), str(e))
                            )
                            summary["headline_read"] = (
                                "Summary could not be generated; see the topics below."
                            )
                    settings = run_settings()
                    settings["cov"] = f"Social only · {scope['label']}"
                    st.session_state.markat_brief = {
                        "query": brand,
                        "scope": scope,
                        **summary,
                        "topics": topics,
                        "generated_at": datetime.datetime.now().strftime(
                            "%d %b %Y %H:%M"
                        ),
                        "settings": settings,
                        "extra_rounds": (
                            (extra_round + 1)
                            if extra_round is not None
                            else previous.get("extra_rounds", 0) if more else 0
                        ),
                    }
                    status.update(
                        label=f"Complete: {len(topics)} discussion topics",
                        state="complete",
                    )
    show_run_messages(notice, fatal, failures, len(passes))
    if more and fatal is None and len(failures) < len(passes):
        added = sum(len(t["sources"]) for t in topics) - before
        report_added(added, "social source", passes[0][0])


def open_scope_confirmation(brand, scope, custom_urls):
    """Stores the detected scope and pre-fills the confirmation form."""
    st.session_state.pending_scope = {
        "brand": brand,
        "scope": scope,
        "custom_urls": custom_urls,
    }
    st.session_state.scope_countries_edit = scope["countries"]
    st.session_state.scope_competitors_edit = ", ".join(scope["competitors"])
    st.session_state.scope_subbrands_edit = ", ".join(scope.get("sub_brands", []))


def report_added(added, noun, label):
    if added > 0:
        st.success(f"Added {added} new {noun}{'s' if added != 1 else ''} from {label}.")
    else:
        st.info(f"No new results from {label} this time. Try Find more again.")


def run_search(query, custom_urls=None, more=False):
    (run_markat if is_markat else run_medierkat)(query, custom_urls, more)


# ============================================================================
# 10. SEARCH BAR
# ============================================================================
with st.container(key="prominent_search"):
    with st.form("top_search_form", border=False):
        s_col1, s_col2 = st.columns([3.5, 1])
        with s_col1:
            top_query = st.text_input(
                "Enter target terms:",
                value=st.session_state.executed_query,
                placeholder=(
                    "Brand or company, e.g. Telstra or Coca-Cola"
                    if is_markat
                    else "Person, organisation or topic, e.g. RMIT coffee concrete"
                ),
                label_visibility="collapsed",
            )
        with s_col2:
            top_submitted = st.form_submit_button("🔍 Search", width="stretch")

if top_submitted:
    st.session_state.executed_query = top_query.strip()
    run_search(top_query)

if st.session_state.pending_query:
    q = st.session_state.pending_query
    st.session_state.pending_query = None
    st.session_state.executed_query = q
    run_search(q)


def request_find_more():
    st.session_state.find_more_requested = True


def request_dig(topic_id):
    st.session_state.dig_request = topic_id


def request_scope_search():
    st.session_state.scope_request = True


def cancel_scope():
    st.session_state.pending_scope = None


# Requested actions run before the buttons are drawn, so labels are always current.
if st.session_state.get("find_more_requested"):
    st.session_state.find_more_requested = False
    requested = (
        st.session_state.markat_brief
        if is_markat
        else st.session_state.cumulative_brief
    )
    if requested:
        run_search(requested["query"], more=True)

if st.session_state.get("dig_request") and is_markat:
    topic_id = st.session_state.dig_request
    st.session_state.dig_request = None
    if st.session_state.markat_brief:
        run_markat(st.session_state.markat_brief["query"], dig_topic=topic_id)

if st.session_state.get("scope_request") and is_markat:
    st.session_state.scope_request = False
    pending = st.session_state.pending_scope
    if pending:
        detected = pending["scope"]
        countries = list(
            st.session_state.get("scope_countries_edit", detected["countries"])
        )
        competitors = [
            c.strip()
            for c in st.session_state.get("scope_competitors_edit", "").split(",")
            if c.strip()
        ]
        sub_brands = [
            c.strip()
            for c in st.session_state.get("scope_subbrands_edit", "").split(",")
            if c.strip()
        ]
        changed = (
            countries != detected["countries"]
            or competitors != detected["competitors"]
            or sub_brands != detected.get("sub_brands", [])
        )
        confirmed = build_scope(
            pending["brand"],
            detected["footprint"] if countries else "global",
            countries,
            competitors,
            sub_brands=sub_brands,
            languages=detected.get("languages", []),
            source="edited by you" if changed else "auto-detected, confirmed by you",
            rationale="" if changed else detected.get("rationale", ""),
            other_named=detected.get("other_named", []),
        )
        st.session_state.pending_scope = None
        run_markat(pending["brand"], pending["custom_urls"], scope_override=confirmed)

if is_markat and st.session_state.pending_scope:
    pending = st.session_state.pending_scope
    detected = pending["scope"]
    with st.container(border=True):
        st.markdown(f"#### Confirm the market scope for {esc(pending['brand'])}")
        st.markdown(
            f"**Detected:** {esc(detected['label'])}"
            + (f"  \n{esc(detected['rationale'])}" if detected.get("rationale") else "")
        )
        if detected.get("other_named"):
            st.caption(
                "Not included (these trade under other names): "
                + ", ".join(detected["other_named"])
            )
        options = COUNTRIES + [c for c in detected["countries"] if c not in COUNTRIES]
        st.multiselect(
            "Countries whose customers to search (leave empty for no country focus)",
            options,
            key="scope_countries_edit",
        )
        st.text_input("Sub-brands to include", key="scope_subbrands_edit")
        st.text_input("Competitors to compare", key="scope_competitors_edit")
        b1, b2 = st.columns([2, 1])
        b1.button(
            "✅ Confirm and search",
            on_click=request_scope_search,
            key="confirm_scope_search",
            width="stretch",
        )
        b2.button("Cancel", on_click=cancel_scope, key="cancel_scope", width="stretch")

current_results = (
    st.session_state.markat_brief if is_markat else st.session_state.cumulative_brief
)
if current_results and not (is_markat and st.session_state.pending_scope):
    next_channel = next_extra_label(
        MARKAT_CHANNELS if is_markat else MEDIERKAT_CHANNELS, current_results
    )
    st.button(
        f"➕ Find more: {next_channel}",
        key="find_more",
        on_click=request_find_more,
        help="Runs one extra search on this channel and adds only new, "
        "non-duplicate results to the current brief.",
    )


# ============================================================================
# 11. EXPORTS (Medierkat)
# ============================================================================
def clean_pdf_text(text):
    if not text:
        return ""
    for orig, repl in {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "—": "-",
        "–": "-",
        "•": "*",
        "📌": "",
    }.items():
        text = str(text).replace(orig, repl)
    return text.encode("latin-1", "replace").decode("latin-1")


class PDFReport(FPDF):
    brand = "MEDIERKAT"
    kind = "EXECUTIVE BRIEF"

    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(107, 107, 107)
        self.set_y(10)
        self.cell(0, 5, f"{self.brand}  |  {self.kind}", align="R")

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 6.5)
        self.set_text_color(107, 107, 107)
        self.cell(
            0,
            5,
            "Generated with AI assistance via Kat Intelligence Engine. Confirm "
            "critical details against source.",
            align="C",
        )


def generate_pdf_brief(brief, query, s, export_limit):
    pdf = PDFReport()
    pdf.brand = "MEDIERKAT"
    pdf.set_margins(18, 22, 18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    epw = pdf.epw

    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(35, 35, 35)
    pdf.cell(
        epw,
        6,
        clean_pdf_text(f"Executive Brief ({s['lang']})"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "B", 7.5)
    pdf.set_text_color(107, 107, 107)
    pdf.multi_cell(epw, 3.8, clean_pdf_text(f"OBJECTIVE: {s['purpose'].upper()}"))
    pdf.set_font("Helvetica", "I", 7.5)
    for line in (
        f"Format: {s['tier']}",
        f"Scope: {query[:80]}  |  Recency: {s['time']}",
        brief.get("verified_coverage_metric", ""),
        brief.get("total_combined_audience_reach", ""),
    ):
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
    pdf.cell(
        epw,
        5,
        f"5. Campaign milestones (newest first, {len(items)} shown)",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(1)
    for item in items:
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.multi_cell(
            epw,
            4,
            clean_pdf_text(
                f"* [{item.get('campaign_milestone_date', '')}] "
                f"{item.get('event_title', '')}"
            ),
        )
        pdf.set_font("Helvetica", "", 7.5)
        pdf.multi_cell(epw, 3.5, clean_pdf_text(item.get("core_event_summary", "")))
        outlets = ", ".join(
            o.get("outlet_name", "") for o in item.get("covering_outlets", [])
        )
        pdf.set_font("Helvetica", "I", 7)
        pdf.multi_cell(epw, 3.4, clean_pdf_text(f"Outlets: {outlets}"))
        pdf.ln(1.5)
    return bytes(pdf.output())


def outlet_line_md(o):
    link = (
        f" — [Source]({o['canonical_source_url']})"
        if is_valid_url(o.get("canonical_source_url"))
        else " — *(no verified link)*"
    )
    return (
        f"  - **{o.get('outlet_name', '')}** ({o.get('medium_type', '')}, "
        f"{o.get('publication_date', '')}) | Audience: "
        f"{o.get('audience_reach_metrics', '')}{link}"
    )


def generate_markdown_brief(brief, query, s, export_limit):
    md = f"# MEDIERKAT EXECUTIVE BRIEF ({s['lang']})\n\n"
    md += (
        f"**Objective:** {s['purpose']}  \n**Report type:** {s['tier']}  "
        f"\n**Query:** {query}  \n"
    )
    md += (
        f"**Recency:** {s['time']}  \n**Coverage focus:** {s['cov']}  "
        f"\n**Channels:** {s['channels']}  \n"
    )
    md += (
        f"**{brief.get('verified_coverage_metric', '')}**  "
        f"\n**{brief.get('total_combined_audience_reach', '')}**\n\n"
    )
    md += "## 1. Executive summary and strategic read\n\n"
    md += f"**Overview:** {brief.get('headline_synthesis', '')}\n\n"
    md += (
        f"**Positioning and reputation:** {brief.get('sentiment_framing_read', '')}\n\n"
    )
    md += f"**Spokesperson quotes:** {brief.get('subject_quoted_vs_reported', '')}\n\n"
    md += (
        f"**Strategic opportunities:** {brief.get('engagement_opportunities', '')}\n\n"
    )
    md += (
        f"**Audience profile:** {brief.get('demographic_audience_profile', '')}\n\n"
        "---\n\n"
    )
    items = brief.get("items", [])[:export_limit]
    md += f"## 2. Campaign milestones (newest first, {len(items)} shown)\n\n"
    for item in items:
        md += (
            f"### [{item.get('campaign_milestone_date', '')}] "
            f"{item.get('event_title', '')}\n"
        )
        md += (
            f"- **Prominence:** {item.get('prominence_depth', '')} | **Framing:** "
            f"{item.get('representation_mode', '')}\n"
        )
        md += (
            f"- **Key message:** {item.get('key_message_delivered', '')}\n- "
            f"**Summary:** {item.get('core_event_summary', '')}\n"
        )
        for o in item.get("covering_outlets", []):
            md += outlet_line_md(o) + "\n"
        md += "\n"
    md += (
        "\n*Generated with AI assistance via Kat Intelligence Engine. Confirm "
        "critical details against source.*\n"
    )
    return md


def generate_docx_brief(brief, query, s, export_limit):
    doc = Document()
    doc.add_heading(f"MEDIERKAT EXECUTIVE BRIEF ({s['lang']})", level=0)
    meta = doc.add_paragraph()
    for label, val in (
        ("Objective: ", s["purpose"]),
        ("Query: ", query),
        ("Recency: ", s["time"]),
        ("Coverage: ", brief.get("verified_coverage_metric", "")),
        ("Audience: ", brief.get("total_combined_audience_reach", "")),
    ):
        meta.add_run(label).bold = True
        meta.add_run(f"{val}\n")
    doc.add_heading("1. Executive summary and strategic read", level=1)
    for label, key in (
        ("Overview", "headline_synthesis"),
        ("Positioning and reputation", "sentiment_framing_read"),
        ("Spokesperson quotes", "subject_quoted_vs_reported"),
        ("Strategic opportunities", "engagement_opportunities"),
        ("Audience profile", "demographic_audience_profile"),
    ):
        p = doc.add_paragraph()
        p.add_run(f"{label}: ").bold = True
        p.add_run(brief.get(key, ""))
    items = brief.get("items", [])[:export_limit]
    doc.add_heading(
        f"2. Campaign milestones (newest first, {len(items)} shown)", level=1
    )
    for item in items:
        doc.add_heading(
            f"[{item.get('campaign_milestone_date', '')}] {item.get('event_title', '')}",
            level=2,
        )
        doc.add_paragraph(item.get("core_event_summary", ""))
        for o in item.get("covering_outlets", []):
            url = (
                o.get("canonical_source_url")
                if is_valid_url(o.get("canonical_source_url"))
                else "no verified link"
            )
            doc.add_paragraph(
                f"{o.get('outlet_name', '')} ({o.get('medium_type', '')}, "
                f"{o.get('publication_date', '')}) — {url}",
                style="List Bullet",
            )
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


# ============================================================================
# 11b. EXPORTS (Markat)
# ============================================================================
def brand_rank(brief, brand):
    name = normalize_str(brand)
    if name == normalize_str(brief.get("query")):
        return 0
    if name in {normalize_str(s) for s in brief.get("scope", {}).get("sub_brands", [])}:
        return 1
    return 2


def ordered_topics(brief):
    """The brand first, then its sub-brands, then competitors; within each, the most
    widely discussed topics first, then the newest."""
    return sorted(
        brief.get("topics", []),
        key=lambda t: (
            brand_rank(brief, t.get("brand")),
            -topic_signal(t)["level"],
            [-x for x in extract_year_month_tuple(t.get("period"))],
        ),
    )


def markat_source_line(s):
    link = (
        f" — [Source]({s['source_url']})"
        if is_valid_url(s.get("source_url"))
        else " — *(no verified link)*"
    )
    engagement = f" | {s['engagement']}" if not is_empty(s.get("engagement")) else ""
    return (
        f"  - {s.get('platform', '')} · {s.get('community_or_account', '')} "
        f"({s.get('post_date', '')}){engagement}{link}"
    )


MARKAT_SECTIONS = [
    ("Overall customer sentiment", "headline_read"),
    ("How representative is this?", "representativeness"),
    ("Reception of marketing campaigns", "campaign_reception"),
    ("Brand vs competitors", "competitor_comparison"),
    ("Pain points and praise", "pain_points_and_praise"),
    ("Opportunities and risks", "opportunities"),
]


def generate_markat_markdown(brief, limit):
    s, scope = brief["settings"], brief["scope"]
    md = f"# MARKAT CUSTOMER SENTIMENT BRIEF ({s['lang']})\n\n"
    md += f"**Brand:** {brief['query']}  \n"
    md += f"**Market scope:** {scope['label']} ({scope['source']})  \n"
    if scope.get("sub_brands"):
        md += f"**Sub-brands included:** {', '.join(scope['sub_brands'])}  \n"
    md += f"**Competitors:** {', '.join(scope['competitors']) or 'not identified'}  \n"
    md += f"**Objective:** {s['purpose']}  \n**Time frame:** {s['time']}  \n"
    md += f"**Channels:** {s['channels']}\n\n"
    for i, (title, key) in enumerate(MARKAT_SECTIONS, 1):
        md += f"## {i}. {title}\n\n{brief.get(key, '')}\n\n"
    topics = ordered_topics(brief)[:limit]
    md += (
        f"---\n\n## {len(MARKAT_SECTIONS) + 1}. Discussion topics ({len(topics)} "
        "shown)\n\n"
    )
    for t in topics:
        flag = " · marketing campaign" if t.get("is_marketing_campaign") else ""
        md += (
            f"### [{t.get('period', '')}] {t.get('brand', '')}: "
            f"{t.get('topic_title', '')} ({t.get('sentiment', '')}{flag})\n"
        )
        md += f"- **Signal:** {signal_text(topic_signal(t))}\n"
        md += (
            f"- **Customers:** {t.get('customer_type', '')} | **Countries:** "
            f"{', '.join(t.get('countries', [])) or 'not stated'}\n"
        )
        md += f"- **What drove it:** {t.get('sentiment_drivers', '')}\n"
        for v in t.get("representative_views", []):
            md += f"- *Typical view:* {v}\n"
        for src in t.get("sources", []):
            md += markat_source_line(src) + "\n"
        md += "\n"
    md += (
        "\n*Generated with AI assistance via Kat Intelligence Engine. Views are "
        "paraphrased; social media over-represents digitally engaged customers. "
        "Confirm "
        "against sources.*\n"
    )
    return md


def generate_markat_docx(brief, limit):
    s, scope = brief["settings"], brief["scope"]
    doc = Document()
    doc.add_heading(f"MARKAT CUSTOMER SENTIMENT BRIEF ({s['lang']})", level=0)
    meta = doc.add_paragraph()
    rows = [
        ("Brand: ", brief["query"]),
        ("Market scope: ", f"{scope['label']} ({scope['source']})"),
        ("Sub-brands included: ", ", ".join(scope.get("sub_brands", [])) or "none"),
        ("Competitors: ", ", ".join(scope["competitors"]) or "not identified"),
        ("Objective: ", s["purpose"]),
        ("Time frame: ", s["time"]),
        ("Channels: ", s["channels"]),
    ]
    for label, val in rows:
        meta.add_run(label).bold = True
        meta.add_run(f"{val}\n")
    for i, (title, key) in enumerate(MARKAT_SECTIONS, 1):
        doc.add_heading(f"{i}. {title}", level=1)
        doc.add_paragraph(brief.get(key, ""))
    topics = ordered_topics(brief)[:limit]
    doc.add_heading(
        f"{len(MARKAT_SECTIONS) + 1}. Discussion topics ({len(topics)} shown)", level=1
    )
    for t in topics:
        doc.add_heading(
            f"[{t.get('period', '')}] {t.get('brand', '')}: {t.get('topic_title', '')} "
            f"({t.get('sentiment', '')})",
            level=2,
        )
        doc.add_paragraph(f"Signal: {signal_text(topic_signal(t))}")
        doc.add_paragraph(
            f"Customers: {t.get('customer_type', '')}. What drove it: "
            f"{t.get('sentiment_drivers', '')}"
        )
        for v in t.get("representative_views", []):
            doc.add_paragraph(f"Typical view: {v}", style="List Bullet")
        for src in t.get("sources", []):
            url = (
                src.get("source_url")
                if is_valid_url(src.get("source_url"))
                else ("no verified link")
            )
            doc.add_paragraph(
                f"{src.get('platform', '')} · {src.get('community_or_account', '')} "
                f"({src.get('post_date', '')}) — {url}",
                style="List Bullet",
            )
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def generate_markat_pdf(brief, limit):
    s, scope = brief["settings"], brief["scope"]
    pdf = PDFReport()
    pdf.brand, pdf.kind = "MARKAT", "CUSTOMER SENTIMENT BRIEF"
    pdf.set_margins(18, 22, 18)
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=20)
    epw = pdf.epw
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(35, 35, 35)
    pdf.cell(
        epw,
        6,
        clean_pdf_text(f"Customer Sentiment Brief: {brief['query']} ({s['lang']})"),
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_font("Helvetica", "I", 7.5)
    pdf.set_text_color(107, 107, 107)
    lines = [
        f"Market scope: {scope['label']} ({scope['source']})",
        f"Sub-brands included: {', '.join(scope.get('sub_brands', [])) or 'none'}",
        f"Competitors: {', '.join(scope['competitors']) or 'not identified'}",
        f"Objective: {s['purpose']}  |  Time frame: {s['time']}",
        f"Channels: {s['channels']}",
    ]
    for line in lines:
        pdf.multi_cell(epw, 3.8, clean_pdf_text(line))
    pdf.ln(2)
    pdf.set_draw_color(198, 188, 169)
    pdf.line(18, pdf.get_y(), 18 + epw, pdf.get_y())
    pdf.ln(3)
    for i, (title, key) in enumerate(MARKAT_SECTIONS, 1):
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(35, 35, 35)
        pdf.cell(epw, 5, clean_pdf_text(f"{i}. {title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8.5)
        pdf.multi_cell(epw, 4, clean_pdf_text(brief.get(key, "")))
        pdf.ln(2)
    topics = ordered_topics(brief)[:limit]
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        epw,
        5,
        f"{len(MARKAT_SECTIONS) + 1}. Discussion topics ({len(topics)} shown)",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    for t in topics:
        pdf.set_font("Helvetica", "B", 8.5)
        pdf.multi_cell(
            epw,
            4,
            clean_pdf_text(
                f"* [{t.get('period', '')}] {t.get('brand', '')}: "
                f"{t.get('topic_title', '')} ({t.get('sentiment', '')})"
            ),
        )
        pdf.set_font("Helvetica", "", 7.5)
        pdf.multi_cell(epw, 3.5, clean_pdf_text(t.get("sentiment_drivers", "")))
        platforms = ", ".join(
            sorted({src.get("platform", "") for src in t.get("sources", [])})
        )
        pdf.set_font("Helvetica", "I", 7)
        pdf.multi_cell(
            epw,
            3.4,
            clean_pdf_text(
                f"Signal: {signal_text(topic_signal(t))}. Platforms: {platforms}"
            ),
        )
        pdf.ln(1.5)
    return bytes(pdf.output())


# ============================================================================
# 12. VIEWS
# ============================================================================
SENTIMENT_COLOURS = {
    "Positive": "#7FA37A",
    "Negative": "#B5654F",
    "Mixed": "#C6A15B",
    "Neutral": "#8A8275",
}
SENTIMENT_ICONS = {"Positive": "🟢", "Negative": "🔴", "Mixed": "🟠", "Neutral": "⚪"}


def metric_card(label, value, caption):
    st.markdown(
        f"<div class='metric-card'><h4>{esc(label)}</h4><h2>{esc(value)}</h2><p "
        f"class='cap'>{esc(caption)}</p></div>",
        unsafe_allow_html=True,
    )


def dated_counts(dates):
    dates = [d for d in dates if d is not None]
    if not dates:
        return None
    s = pd.Series(dates)
    span = (s.max() - s.min()).days
    freq, fmt = (
        ("D", "%d %b")
        if span <= 60
        else (("W", "%d %b %y") if span <= 365 else ("M", "%b %Y"))
    )
    counts = s.dt.to_period(freq).value_counts().sort_index()
    return pd.DataFrame(
        {
            "Period": [p.start_time.strftime(fmt) for p in counts.index],
            "Items": counts.values,
        }
    )


def line_chart(df, y_title):
    chart = (
        alt.Chart(df)
        .mark_line(point=True, color="#C6BCA9")
        .encode(
            x=alt.X("Period:O", sort=None, title=None),
            y=alt.Y("Items:Q", title=y_title),
            tooltip=["Period", "Items"],
        )
        .properties(height=240)
        .configure_axis(labelColor="#C6BCA9", titleColor="#F2EDE3", gridColor="#2C2822")
    )
    st.altair_chart(chart, width="stretch")


def export_controls(n, make_pdf, make_docx, make_md, base):
    options = sorted({x for x in (5, 10, 25, 50) if x < n} | {n}) if n else [0]
    limit = st.selectbox(
        "Items to include in export:",
        options,
        index=len(options) - 1,
        format_func=lambda x: f"All {x}" if x == n else f"Newest {x}",
    )
    fmt = st.selectbox(
        "Export format:",
        ["PDF Document (.pdf)", "Microsoft Word (.docx)", "Markdown (.md)"],
    )
    if "PDF" in fmt:
        st.download_button(
            "Download PDF", make_pdf(limit), f"{base}.pdf", "application/pdf"
        )
    elif "Word" in fmt:
        st.download_button(
            "Download Word document",
            make_docx(limit),
            f"{base}.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        st.download_button(
            "Download Markdown", make_md(limit), f"{base}.md", "text/markdown"
        )


def disclaimer(text):
    st.markdown(
        f"<div class='disclaimer-box'><b>Verification note:</b> {text}</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------- Medierkat views
def render_medierkat_dashboard(brief):
    items = brief.get("items", [])
    st.markdown("##### 📈 Coverage by publication date")
    df = dated_counts(
        [
            parse_date(o.get("publication_date"))
            for it in items
            for o in it.get("covering_outlets", [])
        ]
    )
    if df is not None:
        line_chart(df, "Media items")
    else:
        st.caption("No dated coverage to chart.")
    outlets = [o for it in items for o in it.get("covering_outlets", [])]
    _, _, total_reach = calculate_header_metrics(items)
    channel = Counter(o.get("medium_type", "Unknown") for o in outlets).most_common(1)
    framing = Counter(
        it.get("representation_mode", "Unknown") for it in items
    ).most_common(1)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Coverage milestones", f"{len(items)}", brief["settings"]["time"])
    with c2:
        metric_card(
            "Potential audience",
            format_audience(total_reach),
            "Sum of outlet audiences, not deduplicated",
        )
    with c3:
        metric_card(
            "Dominant channel",
            channel[0][0] if channel else "—",
            f"{channel[0][1]} of {len(outlets)} items" if channel else "",
        )
    with c4:
        metric_card(
            "Most common framing",
            framing[0][0] if framing else "—",
            f"{framing[0][1]} of {len(items)} milestones" if framing else "",
        )


def render_medierkat_brief(brief):
    items, s, query = brief.get("items", []), brief["settings"], brief["query"]
    h1, h2 = st.columns(2)
    with h1:
        st.caption(
            f"MEDIERKAT EXECUTIVE BRIEF · generated {brief.get('generated_at', '')}"
        )
        st.header(f"Executive brief ({s['lang']})")
        st.markdown(
            f"🎯 **Objective:** {esc(s['purpose'])}  \n📋 **Report type:** "
            f"{esc(s['tier'])}"
        )
        st.markdown(
            f"⏳ **Time frame:** {esc(s['time'])}  \n🌐 **Scope:** {esc(s['cov'])}  \n📡 "
            f"**Channels:** {esc(s['channels'])}"
        )
        st.caption(brief.get("verified_coverage_metric", ""))
        st.caption(brief.get("total_combined_audience_reach", ""))
    with h2:
        export_controls(
            len(items),
            lambda n: generate_pdf_brief(brief, query, s, n),
            lambda n: generate_docx_brief(brief, query, s, n),
            lambda n: generate_markdown_brief(brief, query, s, n),
            "Medierkat_Executive_Brief",
        )
    if not items:
        st.warning(
            f"No verified media coverage matched '{query}' in {s['time']}. Nothing has "
            "been substituted."
        )
        return
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
    st.subheader(f"5. Coverage milestones ({len(items)}, newest first)")
    for i, item in enumerate(items, 1):
        with st.expander(
            f"📌 [{item.get('campaign_milestone_date', '')}] #{i}: "
            f"{item.get('event_title', '')}"
        ):
            st.markdown(
                f"**Prominence:** {esc(item.get('prominence_depth'))} | **Framing:** "
                f"{esc(item.get('representation_mode'))}"
            )
            st.markdown(f"**Key message:** {esc(item.get('key_message_delivered'))}")
            st.write(f"**Summary:** {item.get('core_event_summary', '')}")
            for o in item.get("covering_outlets", []):
                url = o.get("canonical_source_url", "")
                link = (
                    f"<br>🔗 <a href='{esc(url)}' target='_blank' rel='noopener'>Open "
                    "source</a>"
                    if is_valid_url(url)
                    else "<br><i>No verified link</i>"
                )
                flag = (
                    f"<br>⚠️ <i>{esc(o.get('verification_confidence'))}</i>"
                    if "Uncorroborated" in o.get("verification_confidence", "")
                    else ""
                )
                st.markdown(
                    f"📰 <b>{esc(o.get('outlet_name'))}</b> "
                    f"({esc(o.get('medium_type'))}) | ✍️ {esc(o.get('author_byline'))} "
                    "| "
                    f"📅 {esc(o.get('publication_date'))}<br>📊 Audience: <b>"
                    f"{esc(o.get('audience_reach_metrics'))}</b>{flag}{link}",
                    unsafe_allow_html=True,
                )
    disclaimer(
        "Generated with AI assistance via Medierkat. Links are shown only when they "
        "came from search grounding or were supplied by you. "
        "Audience figures are model-reported masthead figures, summed without "
        "deduplication. Confirm critical details against source."
    )


# ---------------------------------------------------------------- Markat views
def render_markat_dashboard(brief):
    topics, scope = brief.get("topics", []), brief["scope"]
    own = [t for t in topics if brand_rank(brief, t.get("brand")) < 2]
    sources = [s for t in topics for s in t.get("sources", [])]
    platform = Counter(s.get("platform", "Unknown") for s in sources).most_common(1)
    pos = sum(1 for t in own if t.get("sentiment") == "Positive")
    neg = sum(1 for t in own if t.get("sentiment") == "Negative")
    broad = sum(1 for t in topics if topic_signal(t)["level"] >= 2)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card(
            "Discussion topics", f"{len(topics)}", f"{len(own)} about {brief['query']}"
        )
    with c2:
        metric_card(
            f"{brief['query']} sentiment",
            f"{pos} positive · {neg} negative" if own else "—",
            f"of {len(own)} topics",
        )
    with c3:
        metric_card(
            "Widely discussed",
            f"{broad} of {len(topics)}",
            "Topics with moderate or wide discussion",
        )
    with c4:
        metric_card(
            "Market scope",
            scope["footprint"].replace("-", " ").title(),
            ", ".join(scope["countries"][:3]) or "No country focus",
        )
    if platform:
        st.caption(
            f"Most active platform: {platform[0][0]} ({platform[0][1]} of "
            f"{len(sources)} sources)"
        )

    if topics:
        st.markdown("##### Sentiment by brand")
        rows = Counter(
            (t.get("brand", ""), t.get("sentiment", "Mixed")) for t in topics
        )
        df = pd.DataFrame(
            [{"Brand": b, "Sentiment": s, "Topics": n} for (b, s), n in rows.items()]
        )
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                y=alt.Y("Brand:N", title=None, sort="-x"),
                x=alt.X("sum(Topics):Q", title="Discussion topics"),
                color=alt.Color(
                    "Sentiment:N",
                    scale=alt.Scale(
                        domain=list(SENTIMENT_COLOURS),
                        range=list(SENTIMENT_COLOURS.values()),
                    ),
                    legend=alt.Legend(
                        orient="bottom", labelColor="#C6BCA9", titleColor="#F2EDE3"
                    ),
                ),
                tooltip=["Brand", "Sentiment", "Topics"],
            )
            .properties(height=max(120, 40 * df["Brand"].nunique()))
            .configure_axis(
                labelColor="#C6BCA9", titleColor="#F2EDE3", gridColor="#2C2822"
            )
        )
        st.altair_chart(chart, width="stretch")
        levels = Counter(topic_signal(t)["label"] for t in topics)
        st.caption(
            "Signal strength: "
            + " · ".join(f"{lvl} {levels.get(lvl, 0)}" for lvl in SIGNAL_LEVELS)
        )
        st.markdown("##### Discussion by date")
        df2 = dated_counts([parse_date(s.get("post_date")) for s in sources])
        if df2 is not None:
            line_chart(df2, "Social posts and threads")
        else:
            st.caption("No dated posts to chart.")


def render_markat_brief(brief):
    s, scope = brief["settings"], brief["scope"]
    topics = ordered_topics(brief)
    h1, h2 = st.columns(2)
    with h1:
        st.caption(
            "MARKAT CUSTOMER SENTIMENT BRIEF · generated "
            f"{brief.get('generated_at', '')}"
        )
        st.header(f"{brief['query']}: customer sentiment")
        st.markdown(
            f"🎯 **Objective:** {esc(s['purpose'])}  \n📋 **Report type:** "
            f"{esc(s['tier'])}"
        )
        st.markdown(
            f"⏳ **Time frame:** {esc(s['time'])}  \n📡 **Channels:** "
            f"{esc(s['channels'])}"
        )
    with h2:
        export_controls(
            len(topics),
            lambda n: generate_markat_pdf(brief, n),
            lambda n: generate_markat_docx(brief, n),
            lambda n: generate_markat_markdown(brief, n),
            f"Markat_{normalize_str(brief['query'])[:30]}",
        )

    reason = f" {scope['rationale']}" if scope.get("rationale") else ""
    subs = (
        f"  \n**Sub-brands included:** {', '.join(scope['sub_brands'])}"
        if scope.get("sub_brands")
        else ""
    )
    st.info(
        f"**Market scope:** {scope['label']} ({scope['source']}).{reason}{subs}  \n"
        "**Competitors compared:** "
        f"{', '.join(scope['competitors']) or 'none identified'}"
    )
    if not topics:
        st.warning(
            f"No verified social discussion about '{brief['query']}' was found in "
            f"{s['time']}. Nothing has been substituted."
        )
        return
    for i, (title, key) in enumerate(MARKAT_SECTIONS, 1):
        st.subheader(f"{i}. {title}")
        (st.warning if key == "opportunities" else st.write)(brief.get(key, ""))
    st.divider()
    st.subheader(f"{len(MARKAT_SECTIONS) + 1}. Discussion topics ({len(topics)})")
    st.caption(
        "Most widely discussed first. Signal strength counts distinct sources and "
        "communities: ▮▯▯▯ single source · ▮▮▯▯ limited · ▮▮▮▯ moderate · ▮▮▮▮ widely "
        "discussed."
    )
    brands_in_order = list(dict.fromkeys(t.get("brand", "") for t in topics))
    for b in brands_in_order:
        group = [t for t in topics if t.get("brand", "") == b]
        rank = brand_rank(brief, b)
        tag = "" if rank == 0 else " · sub-brand" if rank == 1 else " · competitor"
        st.markdown(f"#### {esc(b)}{tag}")
        for t in group:
            sig = topic_signal(t)
            icon = SENTIMENT_ICONS.get(t.get("sentiment"), "⚪")
            campaign = " 📣" if t.get("is_marketing_campaign") else ""
            with st.expander(
                f"{icon} {sig['bars']} [{t.get('period', '')}] "
                f"{t.get('topic_title', '')}"
                f"{campaign} · {t.get('sentiment', '')}"
            ):
                st.markdown(f"**Signal:** {esc(signal_text(sig))}")
                st.markdown(
                    f"**Customers:** {esc(t.get('customer_type'))} | **Countries:** "
                    f"{esc(', '.join(t.get('countries', [])) or 'not stated')}"
                    + (
                        " | **Marketing campaign**"
                        if t.get("is_marketing_campaign")
                        else ""
                    )
                )
                st.markdown(f"**What drove it:** {esc(t.get('sentiment_drivers'))}")
                for v in t.get("representative_views", []):
                    st.markdown(f"> {esc(v)}")
                if not is_empty(t.get("summary")):
                    st.caption(t["summary"])
                for src in t.get("sources", []):
                    url = src.get("source_url", "")
                    link = (
                        f" · 🔗 <a href='{esc(url)}' target='_blank' rel='noopener'>"
                        "Open</a>"
                        if is_valid_url(url)
                        else " · <i>no verified link</i>"
                    )
                    engagement = (
                        f" · {esc(src['engagement'])}"
                        if not is_empty(src.get("engagement"))
                        else ""
                    )
                    flag = (
                        " ⚠️"
                        if "Uncorroborated" in src.get("verification_confidence", "")
                        else ""
                    )
                    st.markdown(
                        f"💬 <b>{esc(src.get('platform'))}</b> · "
                        f"{esc(src.get('community_or_account'))} · "
                        f"{esc(src.get('post_date'))}{engagement}{link}{flag}",
                        unsafe_allow_html=True,
                    )
                st.button(
                    "🔎 Dig deeper into this topic",
                    key=f"dig_{t.get('topic_id')}",
                    on_click=request_dig,
                    args=(t.get("topic_id"),),
                    help="Runs one focused search for more discussion of this topic, "
                    "to "
                    "judge how widespread it is.",
                )
    disclaimer(
        "Generated with AI assistance via Markat from public social media and forums "
        "only. Social media over-represents digitally engaged and often dissatisfied "
        "customers, so treat it alongside survey and NPS data. Customer views are "
        "paraphrased and individual usernames are not recorded. Sentiment is assessed "
        "by AI; confirm important findings against the linked sources. 📣 marks the "
        "brand's own marketing campaigns; ⚠️ marks sources without a verified link."
    )


# ---------------------------------------------------------------- Page body
brief = (
    st.session_state.markat_brief if is_markat else st.session_state.cumulative_brief
)

if "Dashboard" in main_mode:
    st.subheader(f"📊 {app_title} dashboard")
    if not brief:
        st.info(
            "Run a search to populate the dashboard. Everything shown comes from your "
            "search results."
        )
    elif is_markat:
        render_markat_dashboard(brief)
    else:
        render_medierkat_dashboard(brief)

elif "Brief" in main_mode:
    st.subheader("📄 Brief builder")
    st.caption(
        "Uses the search term above. Optionally add specific links to include and "
        "verify."
    )
    raw_urls_text = st.text_area(
        "Links (one per line, up to 100):", height=100, placeholder="https://..."
    )
    custom_urls_input = [
        line.strip()
        for line in raw_urls_text.splitlines()
        if line.strip().startswith("http")
    ][:100]
    if st.button("Generate brief"):
        run_search(st.session_state.executed_query, custom_urls_input)
        brief = (
            st.session_state.markat_brief
            if is_markat
            else st.session_state.cumulative_brief
        )

else:
    st.subheader("📚 Library")
    if is_admin:
        with st.expander("⚙️ Admin console"):
            st.markdown(f"**Guest access ({GUEST_USERNAME})**")
            guest_on = bool(get_password_hash(GUEST_USERNAME))
            st.caption(
                "Guest access is on."
                if guest_on
                else "Guest access is off until you set a password."
            )
            with st.form("guest_password_form"):
                g1 = st.text_input(
                    f"New password for {GUEST_USERNAME}", type="password"
                )
                g2 = st.text_input("Confirm password", type="password")
                set_guest = st.form_submit_button("Set guest password")
            if set_guest:
                problem = password_problem(g1, g2, GUEST_USERNAME)
                if problem:
                    st.error(problem)
                else:
                    st.success(
                        f"Guest password set. Share the username {GUEST_USERNAME} and "
                        "this password with your testers."
                    )
                    render_pin_hint(GUEST_USERNAME, set_password(GUEST_USERNAME, g1))
            if guest_on and st.button("Turn off guest access"):
                disable_password(GUEST_USERNAME)
                st.success("Guest access is off.")
                if secret(SECRET_HASH_KEYS[GUEST_USERNAME]):
                    st.warning(
                        f"Also delete {SECRET_HASH_KEYS[GUEST_USERNAME]} from Secrets, "
                        "or guest access will return after the app restarts."
                    )

            st.divider()
            st.markdown(f"**Change your password ({ADMIN_USERNAME})**")
            with st.form("admin_password_form"):
                current_pw = st.text_input("Current password", type="password")
                a1 = st.text_input("New password", type="password")
                a2 = st.text_input("Confirm new password", type="password")
                change = st.form_submit_button("Update password")
            if change:
                problem = password_problem(a1, a2, ADMIN_USERNAME)
                if not authenticate(ADMIN_USERNAME, current_pw):
                    st.error("Your current password isn't correct.")
                elif problem:
                    st.error(problem)
                else:
                    st.success("Password updated.")
                    render_pin_hint(ADMIN_USERNAME, set_password(ADMIN_USERNAME, a1))

    st.markdown("#### Saved searches (this session, max 50)")
    new_q = st.text_input(
        "Add a search term:", placeholder="Brand, topic or keyword..."
    )
    if st.button("➕ Add") and new_q.strip():
        if len(st.session_state.saved_queries) >= 50:
            st.warning("The list is full (50 searches).")
        elif new_q.strip() not in st.session_state.saved_queries:
            st.session_state.saved_queries.append(new_q.strip())
            st.rerun()

    def queue_query(q):
        st.session_state.pending_query = q
        st.session_state.main_mode = "📄 Brief"

    for i, q in enumerate(st.session_state.saved_queries):
        qc1, qc2 = st.columns([5, 1])
        qc1.markdown(f"**{i + 1}.** `{q}`")
        qc2.button(
            "Run",
            key=f"run_q_{i}",
            on_click=queue_query,
            args=(q,),
            help=f"Runs in {app_title}",
        )

    st.markdown("#### Saved briefs (this session)")
    if brief and st.button(f"💾 Save current {app_title} brief"):
        st.session_state.report_library.append(
            {
                "kind": app_title,
                "query": brief["query"],
                "saved": datetime.datetime.now().strftime("%d %b %Y %H:%M"),
                "brief": copy.deepcopy(brief),
            }
        )
    for i, rep in enumerate(st.session_state.report_library):
        b = rep["brief"]
        data = (
            generate_markat_markdown(b, len(b.get("topics", [])))
            if rep["kind"] == "Markat"
            else generate_markdown_brief(
                b, b["query"], b["settings"], len(b.get("items", []))
            )
        )
        st.download_button(
            f"⬇️ {rep['kind']}: {rep['query']} — {rep['saved']} (.md)",
            data,
            f"{rep['kind']}_{normalize_str(rep['query'])[:30]}.md",
            "text/markdown",
            key=f"lib_dl_{i}",
        )

if brief and ("Dashboard" in main_mode or "Brief" in main_mode):
    st.markdown("---")
    (render_markat_brief if is_markat else render_medierkat_brief)(brief)
