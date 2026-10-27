import ipaddress
import re
from collections import Counter

GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "yahoo.com",
    "yahoo.co.in",
    "yahoo.in",
    "yahoo.co.uk",
    "ymail.com",
    "rocketmail.com",
    "hotmail.com",
    "hotmail.co.in",
    "outlook.com",
    "outlook.in",
    "live.com",
    "live.in",
    "msn.com",
    "icloud.com",
    "me.com",
    "aol.com",
    "protonmail.com",
    "proton.me",
    "rediffmail.com",
    "rediff.com",
    "zoho.com",
    "zohomail.in",
    "mail.com",
    "gmx.com",
    "sify.com",
    "bsnl.in",
    "vsnl.com",
    "vsnl.net",
    "airtelmail.com",
    "in.com",
}
BLOCKED_SUFFIXES = (".local", ".internal", ".localhost", ".lan", ".test", ".invalid", ".example")
DOMAIN_PATTERN = re.compile(r"^(?=.{4,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$")
DEFAULT_SHARED_DOMAIN_LIMIT = 3


def domain_from_email(email: str | None) -> str | None:
    if not email or email.count("@") != 1:
        return None
    domain = email.rsplit("@", 1)[1].strip().lower().rstrip(".")
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or None


def is_public_firm_domain(domain: str) -> bool:
    if domain in GENERIC_EMAIL_DOMAINS or domain.endswith(BLOCKED_SUFFIXES):
        return False
    try:
        ipaddress.ip_address(domain)
        return False
    except ValueError:
        pass
    return bool(DOMAIN_PATTERN.match(domain))


def candidate_domains(
    emails_by_professional: dict[str, list[str]],
    shared_domain_limit: int = DEFAULT_SHARED_DOMAIN_LIMIT,
) -> dict[str, set[str]]:
    per_professional: dict[str, set[str]] = {}
    for professional_id, emails in emails_by_professional.items():
        domains = {d for d in map(domain_from_email, emails) if d and is_public_firm_domain(d)}
        if domains:
            per_professional[professional_id] = domains
    usage = Counter(d for domains in per_professional.values() for d in domains)
    result: dict[str, set[str]] = {}
    for professional_id, domains in per_professional.items():
        kept = {d for d in domains if usage[d] <= shared_domain_limit}
        if kept:
            result[professional_id] = kept
    return result
