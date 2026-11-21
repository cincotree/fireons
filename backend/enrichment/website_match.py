import re
from collections import defaultdict

from bs4 import BeautifulSoup

NAME_STOPWORDS = {
    "ca", "co", "company", "and", "associates", "associate", "partners", "partner", "llp", "pvt", "private",
    "ltd", "limited", "chartered", "accountant", "accountants", "accountancy", "tax", "taxation", "consultant",
    "consultants", "consultancy", "consulting", "advisor", "advisors", "adviser", "advisers", "advisory",
    "financial", "finance", "wealth", "planner", "planners", "planning", "services", "service", "solutions",
    "the", "of", "firm", "best", "top", "gst", "itr", "filing", "tds", "return", "returns", "investment",
    "investments", "insurance", "management", "group", "india", "estate", "lawyer", "lawyers", "advocate",
    "advocates", "legal", "audit", "auditors", "bookkeeping", "registration", "company", "in", "for", "near",
}
FINANCE_CUES = re.compile(
    r"chartered accountant|\bca\b|\btax\b|\bgst\b|financial|wealth|invest|insurance|advis|audit|planner|"
    r"mutual fund|accounting|estate plan",
    re.IGNORECASE,
)
DIRECTORY_DOMAINS = {
    "justdial.com", "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com", "youtube.com",
    "indiamart.com", "sulekha.com", "wikipedia.org", "google.com", "maps.google.com", "yellowpages.in",
    "mapsofindia.com", "quora.com", "reddit.com", "pinterest.com", "naukri.com", "glassdoor.co.in",
    "glassdoor.com", "ambitionbox.com", "tripadvisor.in", "tripadvisor.com", "zaubacorp.com", "tofler.in",
    "instafinancials.com", "indeed.com", "medium.com", "yelp.com", "clutch.co", "sebi.gov.in", "icai.org",
    "taxguru.in", "caclubindia.com", "bing.com", "apple.com", "tiktok.com", "threads.net", "wa.me",
    "whatsapp.com", "business.site", "godaddy.com", "wixsite.com", "wordpress.com", "blogspot.com",
    "grotal.com", "asklaila.com", "cylex-india.com", "thefreelibrary.com", "trustpilot.com", "mouthshut.com",
    "magicpin.in", "lawrato.com", "vakilsearch.com", "unolegal.com", "legalkart.com", "bajajfinserv.in",
    "5paisa.com", "etmoney.com", "cleartax.in", "groww.in", "zerodha.com",
}
TLDS = ("com", "in", "co.in")
MAX_GUESS_BASES = 3
MIN_GUESS_LENGTH = 6
MAX_TOKENS_IN_GUESS = 3


def clean_name(name: str) -> str:
    head = re.split(r"\s*[|(]\s*|\s+-\s+|\s*,\s*", name, maxsplit=1)[0]
    return re.sub(r"\s+", " ", head).strip()


def distinctive_tokens(name: str) -> list[str]:
    text = clean_name(name).lower().replace("&", " ")
    tokens = re.findall(r"[a-z0-9]+", text)
    return [t for t in tokens if t not in NAME_STOPWORDS and len(t) >= 3 and not t.isdigit()]


def guess_domains(name: str) -> list[str]:
    tokens = distinctive_tokens(name)[:MAX_TOKENS_IN_GUESS]
    bases: list[str] = []
    for base in ("".join(tokens), "".join(tokens[:2]), tokens[0] if tokens else ""):
        if len(base) >= MIN_GUESS_LENGTH and base not in bases:
            bases.append(base)
    bases = bases[:MAX_GUESS_BASES]
    return [f"{base}.{tld}" for base in bases for tld in TLDS]


def is_directory_domain(domain: str) -> bool:
    return any(domain == blocked or domain.endswith(f".{blocked}") for blocked in DIRECTORY_DOMAINS)


def page_text(html: str, limit: int = 300_000) -> str:
    soup = BeautifulSoup(html[:limit], "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = soup.title.get_text(" ") if soup.title else ""
    return re.sub(r"\s+", " ", f"{title} {soup.get_text(' ')}").lower()


def page_matches(name: str, city: str | None, html: str) -> bool:
    tokens = distinctive_tokens(name)
    if not tokens or not city:
        return False
    text = page_text(html)
    if not all(re.search(rf"\b{re.escape(token)}\b", text) for token in tokens):
        return False
    if not re.search(rf"\b{re.escape(city.lower())}\b", text):
        return False
    return bool(FINANCE_CUES.search(text))


def name_key(name: str, city: str | None) -> tuple[frozenset[str], str] | None:
    tokens = distinctive_tokens(name)
    if not tokens or not city:
        return None
    return frozenset(tokens), city.strip().lower()


def index_register_domains(rows: list[tuple[str, str, str | None, str]]) -> dict[tuple[frozenset[str], str], set[str]]:
    index: dict[tuple[frozenset[str], str], set[str]] = defaultdict(set)
    for _, name, city, domain in rows:
        key = name_key(name, city)
        if key:
            index[key].add(domain)
    return index
