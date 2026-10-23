import enum
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AccountType(enum.Enum):
    ASSETS = "Assets"
    LIABILITIES = "Liabilities"
    EQUITY = "Equity"
    INCOME = "Income"
    EXPENSES = "Expenses"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    open_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="accounts")
    postings: Mapped[list["Posting"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )
    balances: Mapped[list["Balance"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_account_user_name"),
        Index("ix_accounts_user_id", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<Account(name={self.name}, type={self.account_type.value})>"

    @property
    def parent_name(self) -> str | None:
        parts = self.name.rsplit(":", 1)
        return parts[0] if len(parts) > 1 else None

    @property
    def short_name(self) -> str:
        return self.name.rsplit(":", 1)[-1]


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Transaction flag (* for complete, ! for incomplete)
    flag: Mapped[str] = mapped_column(String(1), default="*", nullable=False)
    payee: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, index=True)
    narration: Mapped[str] = mapped_column(Text, nullable=False)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    postings: Mapped[list["Posting"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    links: Mapped[list["TransactionLink"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )
    tags: Mapped[list["TransactionTag"]] = relationship(
        back_populates="transaction", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_transactions_date_payee", "date", "payee"),
    )

    def __repr__(self) -> str:
        return f"<Transaction(date={self.date}, narration={self.narration[:50]})>"

    @property
    def is_balanced(self) -> bool:
        total = sum(p.amount for p in self.postings if p.amount is not None)
        return abs(total) < Decimal("0.001")


class Posting(Base):
    __tablename__ = "postings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    # Foreign keys
    transaction_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    # Amount (positive for debits, negative for credits in expense/asset accounts)
    # Can be None if auto-computed to balance
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    # Currency
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    # Cost basis (for investments)
    cost_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    cost_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cost_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # Price (for currency conversions)
    price_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(precision=20, scale=4), nullable=True
    )
    price_currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # Posting order within transaction
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(back_populates="postings")
    account: Mapped["Account"] = relationship(back_populates="postings")

    __table_args__ = (
        Index("ix_postings_account_id", "account_id"),
        Index("ix_postings_transaction_id", "transaction_id"),
    )

    def __repr__(self) -> str:
        return f"<Posting(account={self.account_id}, amount={self.amount} {self.currency})>"


class Balance(Base):
    __tablename__ = "balances"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    account_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=4), nullable=False
    )
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    account: Mapped["Account"] = relationship(back_populates="balances")

    __table_args__ = (
        UniqueConstraint("account_id", "date", "currency", name="uq_balance_account_date_currency"),
        Index("ix_balances_account_date", "account_id", "date"),
    )

    def __repr__(self) -> str:
        return f"<Balance(account={self.account_id}, date={self.date}, amount={self.amount})>"


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    from_currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    to_currency: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(
        Numeric(precision=20, scale=6), nullable=False
    )
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("date", "from_currency", "to_currency",
                        name="uq_exchange_rate_date_currencies"),
        Index("ix_exchange_rates_currencies", "from_currency", "to_currency"),
    )

    def __repr__(self) -> str:
        return f"<ExchangeRate({self.from_currency}/{self.to_currency}={self.rate} on {self.date})>"


class TransactionLink(Base):
    __tablename__ = "transaction_links"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    transaction_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    link: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="links")

    __table_args__ = (
        UniqueConstraint("transaction_id", "link", name="uq_transaction_link"),
    )


class TransactionTag(Base):
    __tablename__ = "transaction_tags"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    transaction_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False
    )
    tag: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    transaction: Mapped["Transaction"] = relationship(back_populates="tags")

    __table_args__ = (
        UniqueConstraint("transaction_id", "tag", name="uq_transaction_tag"),
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    primary_currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    accounts: Mapped[list["Account"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(username={self.username}, email={self.email})>"


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    regulator: Mapped[str] = mapped_column(String(100), nullable=False)
    default_profession_type: Mapped[str] = mapped_column(String(100), nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<DataSource(key={self.key})>"


class FinancialProfessional(Base):
    __tablename__ = "financial_professionals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    name_normalized: Mapped[str] = mapped_column(String(500), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    registrations: Mapped[list["ProfessionalRegistration"]] = relationship(
        back_populates="professional"
    )

    __table_args__ = (
        Index(
            "ix_financial_professionals_name_trgm",
            "name_normalized",
            postgresql_using="gin",
            postgresql_ops={"name_normalized": "gin_trgm_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<FinancialProfessional(display_name={self.display_name})>"


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    trigger: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expected_total: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pages_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_seen: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unchanged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    parse_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    marked_delisted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_scrape_runs_source_started", "source_id", "started_at"),)


class ProfessionalRegistration(Base):
    __tablename__ = "professional_registrations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    professional_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("financial_professionals.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("data_sources.id", ondelete="CASCADE"), nullable=False
    )
    profession_type: Mapped[str] = mapped_column(String(100), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    validity_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    address_raw: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    missing_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    professional: Mapped["FinancialProfessional"] = relationship(back_populates="registrations")
    source: Mapped["DataSource"] = relationship()
    versions: Mapped[list["RegistrationVersion"]] = relationship(
        back_populates="registration", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("source_id", "registration_number", name="uq_registration_source_number"),
        Index("ix_registrations_type_status", "profession_type", "status"),
        Index("ix_registrations_state_city", "state", "city"),
        Index("ix_registrations_professional", "professional_id"),
    )

    def __repr__(self) -> str:
        return f"<ProfessionalRegistration(registration_number={self.registration_number})>"


class RegistrationVersion(Base):
    __tablename__ = "registration_versions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    registration_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("professional_registrations.id", ondelete="CASCADE"),
        nullable=False,
    )
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("scrape_runs.id", ondelete="CASCADE"), nullable=False
    )
    scraped_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    registration: Mapped["ProfessionalRegistration"] = relationship(back_populates="versions")

    __table_args__ = (
        UniqueConstraint("registration_id", "run_id", name="uq_version_registration_run"),
        Index("ix_versions_registration_scraped", "registration_id", "scraped_at"),
    )
