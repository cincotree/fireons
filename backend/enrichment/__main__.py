import argparse
import asyncio
import logging
import sys
from datetime import datetime, timezone

from sqlalchemy import select, update

from database.models import FinancialProfessional, NriSignal, ProfessionalWebsite
from database.session import session_context
from enrichment.runner import enrich_nri

REVIEW_STATUSES = ("confirmed", "rejected", "pending")
CONFIDENCE_ORDER = {"high": 0, "medium": 1, "low": 2}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m enrichment")
    commands = parser.add_subparsers(dest="command", required=True)
    nri = commands.add_parser("nri", help="check firm websites for NRI signals")
    nri.add_argument("--limit", type=int, default=None, help="check at most this many websites")
    queue = commands.add_parser("review-queue", help="list NRI signals awaiting review")
    queue.add_argument("--confidence", choices=sorted(CONFIDENCE_ORDER), default=None)
    queue.add_argument("--limit", type=int, default=50)
    review = commands.add_parser("review", help="mark one signal confirmed or rejected")
    review.add_argument("signal_id")
    review.add_argument("status", choices=REVIEW_STATUSES)
    return parser


async def _nri(limit: int | None) -> int:
    summary = await enrich_nri(limit=limit)
    print(
        f"known={summary.websites_known} checked={summary.websites_checked} "
        f"unreachable={summary.unreachable} robots_blocked={summary.blocked_by_robots} "
        f"errors={summary.crawl_errors} signals={summary.signals_found} "
        f"removed={summary.signals_removed}"
    )
    return 1 if summary.crawl_errors else 0


async def _review_queue(confidence: str | None, limit: int) -> int:
    query = (
        select(NriSignal, FinancialProfessional.display_name, ProfessionalWebsite.domain)
        .join(FinancialProfessional, FinancialProfessional.id == NriSignal.professional_id)
        .join(ProfessionalWebsite, ProfessionalWebsite.id == NriSignal.website_id)
        .where(NriSignal.review_status == "pending")
    )
    if confidence:
        query = query.where(NriSignal.confidence == confidence)
    async with session_context() as session:
        rows = (await session.execute(query)).all()
    rows.sort(key=lambda row: (CONFIDENCE_ORDER[row[0].confidence], row[1]))
    for signal, name, domain in rows[:limit]:
        print(f"{signal.id} [{signal.confidence}] {name} ({domain}) {signal.signal_type}/{signal.location}")
        print(f"    {signal.page_url}")
        print(f"    {signal.matched_text}")
    print(f"{min(len(rows), limit)} of {len(rows)} pending signals shown")
    return 0


async def _review(signal_id: str, status: str) -> int:
    reviewed_at = None if status == "pending" else datetime.now(timezone.utc)
    async with session_context() as session:
        result = await session.execute(
            update(NriSignal)
            .where(NriSignal.id == signal_id)
            .values(review_status=status, reviewed_at=reviewed_at)
        )
    if not result.rowcount:
        print(f"No signal with id {signal_id}")
        return 1
    print(f"{signal_id} marked {status}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "nri":
        return asyncio.run(_nri(args.limit))
    if args.command == "review-queue":
        return asyncio.run(_review_queue(args.confidence, args.limit))
    return asyncio.run(_review(args.signal_id, args.status))


if __name__ == "__main__":
    sys.exit(main())
