import hashlib
import re
from dataclasses import dataclass
from enum import Enum

from bs4 import BeautifulSoup

from scraping.normalize import collapse_whitespace

MAX_SIGNALS_PER_PAGE = 10
SNIPPET_RADIUS = 110
MAX_PROMINENT_LENGTH = 300
MIN_DUPLICATE_LENGTH = 8
NEGATION_PATTERN = re.compile(
    r"\b(not|no|never|cannot|can't|unable|except|excluding|exclude|excludes|unavailable)\b",
    re.IGNORECASE,
)


class SignalType(str, Enum):
    NRI_MENTION = "nri_mention"
    NRI_ACCOUNT = "nri_account"
    REPATRIATION = "repatriation"
    OVERSEAS_AUDIENCE = "overseas_audience"


class Confidence(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Location(str, Enum):
    TITLE = "title"
    META = "meta"
    HEADING = "heading"
    LINK = "link"
    BODY = "body"


PROMINENT_LOCATIONS = {Location.TITLE, Location.META, Location.HEADING, Location.LINK}
STRONG_TYPES = {SignalType.NRI_MENTION, SignalType.NRI_ACCOUNT}

PATTERNS: list[tuple[SignalType, re.Pattern[str]]] = [
    (
        SignalType.NRI_MENTION,
        re.compile(
            r"\bNRIs?\b|\bnon[\s-]*resident\s+(?:indians?|investors?)\b|"
            r"\bpersons?\s+of\s+indian\s+origin\b|\boverseas\s+indians?\b",
            re.IGNORECASE,
        ),
    ),
    (SignalType.NRI_ACCOUNT, re.compile(r"\b(?:NRE|NRO|FCNR)\b")),
    (
        SignalType.REPATRIATION,
        re.compile(
            r"\brepatriat\w*\b|\bFEMA\b|\bforeign\s+remittances?\b|\bPIS\s+(?:account|route|permission)\b",
            re.IGNORECASE,
        ),
    ),
    (
        SignalType.OVERSEAS_AUDIENCE,
        re.compile(
            r"\bindians?\s+(?:living|residing|settled|working)?\s*(?:abroad|overseas)\b|"
            r"\bglobal\s+indians?\b|\bindian\s+diaspora\b|\b(?:OCI|PIO)\s+(?:card|holders?)\b",
            re.IGNORECASE,
        ),
    ),
]


@dataclass(frozen=True)
class DetectedSignal:
    page_url: str
    signal_type: SignalType
    matched_text: str
    text_hash: str
    location: Location
    confidence: Confidence


@dataclass
class _Candidate:
    signal_type: SignalType
    snippet: str
    location: Location
    negated: bool


def _hash(snippet: str) -> str:
    return hashlib.sha256(snippet.casefold().encode("utf-8")).hexdigest()


def _snippet_around(text: str, start: int, end: int) -> str:
    left = max(0, start - SNIPPET_RADIUS)
    right = min(len(text), end + SNIPPET_RADIUS)
    snippet = text[left:right].strip()
    prefix = "..." if left > 0 else ""
    suffix = "..." if right < len(text) else ""
    return f"{prefix}{snippet}{suffix}"


def _is_negated(text: str, start: int) -> bool:
    return bool(NEGATION_PATTERN.search(text[max(0, start - 40) : start]))


def _scan(text: str, location: Location) -> list[_Candidate]:
    candidates = []
    for signal_type, pattern in PATTERNS:
        for match in pattern.finditer(text):
            if location in PROMINENT_LOCATIONS:
                snippet = text[:MAX_PROMINENT_LENGTH]
            else:
                snippet = _snippet_around(text, match.start(), match.end())
            candidates.append(
                _Candidate(signal_type, snippet, location, _is_negated(text, match.start()))
            )
    return candidates


def _link_texts(soup: BeautifulSoup) -> list[str]:
    texts = []
    for anchor in soup.find_all("a"):
        label = collapse_whitespace(anchor.get_text(" "))
        href = (anchor.get("href") or "").replace("-", " ").replace("_", " ").replace("/", " ")
        if label and len(label) <= 120:
            texts.append(label)
        elif href.strip() and re.search(r"nri|non resident|overseas", href, re.IGNORECASE):
            texts.append(collapse_whitespace(href) or "")
    return texts


def _grade(candidate: _Candidate, page_types: set[SignalType]) -> Confidence:
    prominent = candidate.location in PROMINENT_LOCATIONS
    strong = candidate.signal_type in STRONG_TYPES
    if strong and prominent:
        grade = Confidence.HIGH
    elif strong:
        grade = Confidence.HIGH if len(page_types) >= 2 else Confidence.MEDIUM
    elif prominent:
        grade = Confidence.MEDIUM
    else:
        grade = Confidence.LOW
    if candidate.negated:
        return Confidence.LOW
    return grade


def detect_signals(page_url: str, html: str) -> list[DetectedSignal]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()

    candidates: list[_Candidate] = []
    title = collapse_whitespace(soup.title.get_text(" ")) if soup.title else None
    if title:
        candidates += _scan(title, Location.TITLE)
    for meta in soup.find_all("meta"):
        key = (meta.get("name") or meta.get("property") or "").lower()
        content = collapse_whitespace(meta.get("content"))
        if content and key in {"description", "keywords", "og:title", "og:description"}:
            candidates += _scan(content, Location.META)
    for heading in soup.find_all(["h1", "h2", "h3"]):
        text = collapse_whitespace(heading.get_text(" "))
        if text:
            candidates += _scan(text, Location.HEADING)
    for text in _link_texts(soup):
        candidates += _scan(text, Location.LINK)
    body_text = collapse_whitespace((soup.body or soup).get_text(" "))
    if body_text:
        candidates += _scan(body_text, Location.BODY)

    prominent_text = {
        (c.signal_type, c.snippet.casefold()) for c in candidates if c.location in PROMINENT_LOCATIONS
    }
    candidates = [
        c
        for c in candidates
        if c.location in PROMINENT_LOCATIONS
        or not any(
            t == c.signal_type and len(text) >= MIN_DUPLICATE_LENGTH and text in c.snippet.casefold()
            for t, text in prominent_text
        )
    ]
    page_types = {c.signal_type for c in candidates if not c.negated}
    best: dict[tuple[SignalType, str], DetectedSignal] = {}
    for candidate in candidates:
        key = (candidate.signal_type, _hash(candidate.snippet))
        confidence = _grade(candidate, page_types)
        existing = best.get(key)
        rank = [Confidence.LOW, Confidence.MEDIUM, Confidence.HIGH]
        if existing and rank.index(existing.confidence) >= rank.index(confidence):
            continue
        best[key] = DetectedSignal(
            page_url=page_url,
            signal_type=candidate.signal_type,
            matched_text=candidate.snippet,
            text_hash=key[1],
            location=candidate.location,
            confidence=confidence,
        )
    order = {Confidence.HIGH: 0, Confidence.MEDIUM: 1, Confidence.LOW: 2}
    ranked = sorted(best.values(), key=lambda s: (order[s.confidence], s.signal_type.value))
    return ranked[:MAX_SIGNALS_PER_PAGE]
