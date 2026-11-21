import hashlib
import json
import re
from dataclasses import asdict
from datetime import date, datetime

from scraping.types import (
    ParseError,
    ProfessionalKind,
    RegistrationStatus,
    ScrapedRegistration,
)

INDIAN_STATES = {
    "andhra pradesh": "Andhra Pradesh",
    "arunachal pradesh": "Arunachal Pradesh",
    "assam": "Assam",
    "bihar": "Bihar",
    "chhattisgarh": "Chhattisgarh",
    "goa": "Goa",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    "himachal pradesh": "Himachal Pradesh",
    "jharkhand": "Jharkhand",
    "karnataka": "Karnataka",
    "kerala": "Kerala",
    "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra",
    "manipur": "Manipur",
    "meghalaya": "Meghalaya",
    "mizoram": "Mizoram",
    "nagaland": "Nagaland",
    "odisha": "Odisha",
    "orissa": "Odisha",
    "punjab": "Punjab",
    "rajasthan": "Rajasthan",
    "sikkim": "Sikkim",
    "tamil nadu": "Tamil Nadu",
    "telangana": "Telangana",
    "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh",
    "uttarakhand": "Uttarakhand",
    "uttaranchal": "Uttarakhand",
    "west bengal": "West Bengal",
    "andaman and nicobar islands": "Andaman and Nicobar Islands",
    "andaman & nicobar islands": "Andaman and Nicobar Islands",
    "chandigarh": "Chandigarh",
    "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "dadra and nagar haveli": "Dadra and Nagar Haveli and Daman and Diu",
    "daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "nct of delhi": "Delhi",
    "jammu and kashmir": "Jammu and Kashmir",
    "jammu & kashmir": "Jammu and Kashmir",
    "ladakh": "Ladakh",
    "lakshadweep": "Lakshadweep",
    "puducherry": "Puducherry",
    "pondicherry": "Puducherry",
}

FIRM_PATTERN = re.compile(
    r"\b(pvt|private|limited|ltd|llp|llc|inc|corporation|corp|company|co|services|solutions|"
    r"advisors|advisers|advisory|advisories|capital|wealth|finance|financial|consultants|"
    r"consultancy|securities|investments|investment|partners|associates|bank|trust|fund|"
    r"management|research|analytics|ventures|technologies|enterprises|group|holdings)\b",
    re.IGNORECASE,
)

PINCODE_PATTERN = re.compile(r"^\d{6}$")
VALIDITY_PATTERN = re.compile(
    r"^\s*(?P<start>[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\s*-\s*(?P<end>Perpetual|[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})\s*$",
    re.IGNORECASE,
)


def collapse_whitespace(value: str | None) -> str | None:
    if value is None:
        return None
    collapsed = re.sub(r"\s+", " ", value).strip()
    return collapsed or None


def normalize_name(name: str) -> str:
    lowered = name.casefold()
    stripped = re.sub(r"[^0-9a-zऀ-ॿ]+", " ", lowered)
    return re.sub(r"\s+", " ", stripped).strip()


def classify_kind(name: str) -> ProfessionalKind:
    if FIRM_PATTERN.search(name):
        return ProfessionalKind.FIRM
    return ProfessionalKind.INDIVIDUAL


def _parse_validity_date(value: str) -> date:
    cleaned = re.sub(r",\s*", ", ", re.sub(r"\s+", " ", value.strip()))
    for fmt in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ParseError(f"Unrecognised validity date: {value!r}")


def parse_validity(raw: str | None) -> tuple[date, date | None]:
    if raw is None:
        raise ParseError("Missing validity")
    match = VALIDITY_PATTERN.match(raw)
    if not match:
        raise ParseError(f"Unrecognised validity: {raw!r}")
    valid_from = _parse_validity_date(match.group("start"))
    end = match.group("end")
    if end.lower() == "perpetual":
        return valid_from, None
    valid_until = _parse_validity_date(end)
    if valid_until < valid_from:
        raise ParseError(f"Validity ends before it starts: {raw!r}")
    return valid_from, valid_until


def parse_address(address: str | None) -> tuple[str | None, str | None, str | None]:
    if not address:
        return None, None, None
    segments = [s.strip() for s in address.split(",") if s.strip()]
    pincode = None
    if segments and PINCODE_PATTERN.match(segments[-1]):
        pincode = segments.pop()
    elif segments:
        trailing = re.search(r"\s(\d{6})$", segments[-1])
        if trailing:
            pincode = trailing.group(1)
            segments[-1] = segments[-1][: trailing.start()].strip()
            segments = [s for s in segments if s]

    state = None
    state_index = None
    for index in range(len(segments) - 1, -1, -1):
        canonical = INDIAN_STATES.get(segments[index].casefold())
        if canonical:
            state = canonical
            state_index = index
            break

    city = None
    if state_index is not None:
        for index in range(state_index - 1, -1, -1):
            candidate = segments[index]
            if candidate.casefold() in INDIAN_STATES:
                continue
            if any(ch.isdigit() for ch in candidate):
                break
            city = candidate.title()
            break
    return city, state, pincode


def derive_status(valid_until: date | None, today: date) -> RegistrationStatus:
    if valid_until is not None and valid_until < today:
        return RegistrationStatus.EXPIRED
    return RegistrationStatus.ACTIVE


def content_hash(record: ScrapedRegistration) -> str:
    payload = asdict(record)
    payload["profession_type"] = record.profession_type.value
    payload["kind"] = record.kind.value
    for key in ("valid_from", "valid_until"):
        value = payload[key]
        payload[key] = value.isoformat() if value else None
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def snapshot(record: ScrapedRegistration) -> dict:
    payload = asdict(record)
    payload["profession_type"] = record.profession_type.value
    payload["kind"] = record.kind.value
    for key in ("valid_from", "valid_until"):
        value = payload[key]
        payload[key] = value.isoformat() if value else None
    return payload
