from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class ProfessionType(str, Enum):
    INVESTMENT_ADVISER = "investment_adviser"
    RESEARCH_ANALYST = "research_analyst"
    MF_DISTRIBUTOR = "mf_distributor"
    INSURANCE_AGENT = "insurance_agent"


class RegistrationStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DELISTED = "delisted"


class RunStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIAL = "partial"
    FAILED = "failed"


class ProfessionalKind(str, Enum):
    INDIVIDUAL = "individual"
    FIRM = "firm"


class RunTrigger(str, Enum):
    SCHEDULED = "scheduled"
    MANUAL = "manual"


@dataclass(frozen=True)
class SourceDefinition:
    key: str
    name: str
    regulator: str
    default_profession_type: ProfessionType
    base_url: str


@dataclass(frozen=True)
class ScrapedRegistration:
    registration_number: str
    name: str
    kind: ProfessionalKind
    profession_type: ProfessionType
    valid_from: date | None
    valid_until: date | None
    validity_raw: str | None
    city: str | None
    state: str | None
    pincode: str | None
    address_raw: str | None
    email: str | None
    phone: str | None
    contact_person: str | None
    source_url: str
    attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class FetchedPage:
    records: list[ScrapedRegistration]
    parse_errors: int = 0
    expected_total: int | None = None
    page_size: int | None = None


class ParseError(ValueError):
    pass


class ScrapeHttpError(RuntimeError):
    pass


class RunAlreadyInProgress(RuntimeError):
    pass
