import argparse
import asyncio
import logging
import sys
from pathlib import Path

from enrichment.places_enrichment import enrich_places
from enrichment.places import CATEGORIES, TIERS, PlacesError, run_export
from enrichment.runner import enrich_nri
from enrichment.website_finder import find_websites
from scraping.config import get_scrape_settings



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m enrichment")
    commands = parser.add_subparsers(dest="command", required=True)
    nri = commands.add_parser("nri", help="check firm websites for NRI signals")
    nri.add_argument("--limit", type=int, default=None, help="check at most this many websites")
    places = commands.add_parser("places", help="export professionals found via Google Places to a CSV")
    places.add_argument("--output", default="exports/places_professionals.csv")
    places.add_argument("--tier", choices=sorted(TIERS), default="pro")
    places.add_argument("--daily-limit", type=int, default=None)
    places.add_argument("--monthly-limit", type=int, default=None)
    places.add_argument("--categories", nargs="+", choices=sorted(CATEGORIES), default=None)
    places.add_argument("--cities", nargs="+", default=None)
    places.add_argument("--max-pages", type=int, default=3)
    finder = commands.add_parser("find-websites", help="find websites for unverified listings that have none")
    finder.add_argument("--limit", type=int, default=None, help="consider at most this many new listings")
    finder.add_argument("--no-search", action="store_true", help="skip the Tavily search step")
    enrich = commands.add_parser("enrich-places", help="search the web for details of imported Google listings")
    enrich.add_argument("csv_path")
    enrich.add_argument("--limit", type=int, default=None, help="search for at most this many listings")
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


async def _find_websites(limit: int | None, search: bool) -> int:
    summary = await find_websites(limit=limit, search=search)
    print(
        f"considered={summary.rows_considered} by_register={summary.found_by_register} "
        f"by_guess={summary.found_by_guess} by_search={summary.found_by_search} "
        f"not_found={summary.not_found} waiting_for_search={summary.left_for_search}"
    )
    print(f"searches={summary.searches_made} left_today={summary.searches_left_today} stopped={summary.stopped_reason}")
    return 0


async def _enrich_places(csv_path: str, limit: int | None) -> int:
    path = Path(csv_path)
    if not path.exists():
        print(f"No such file: {path}")
        return 2
    summary = await enrich_places(path, limit=limit)
    print(
        f"rows={summary.rows_in_file} enriched={summary.enriched} listing_only={summary.listing_only} "
        f"already_done={summary.already_done} not_imported={summary.not_imported}"
    )
    print(f"searches={summary.searches_made} left_today={summary.searches_left_today} stopped={summary.stopped_reason}")
    return 0


def _places(args) -> int:
    settings = get_scrape_settings()
    try:
        summary = run_export(
            output=Path(args.output),
            api_key=settings.google_api_key,
            tier=args.tier,
            daily_limit=args.daily_limit,
            monthly_limit=args.monthly_limit,
            categories=args.categories,
            cities=args.cities,
            max_pages=args.max_pages,
        )
    except PlacesError as exc:
        print(f"error: {exc}")
        return 2
    print(
        f"calls={summary.calls_made} written={summary.places_written} "
        f"duplicates={summary.duplicates_skipped} queries_done={summary.queries_completed} "
        f"queries_left={summary.queries_remaining} stopped={summary.stopped_reason}"
    )
    print(f"calls left today={summary.calls_left_today} this month={summary.calls_left_this_month}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    args = build_parser().parse_args(argv)
    if args.command == "nri":
        return asyncio.run(_nri(args.limit))
    if args.command == "find-websites":
        return asyncio.run(_find_websites(args.limit, not args.no_search))
    if args.command == "enrich-places":
        return asyncio.run(_enrich_places(args.csv_path, args.limit))
    return _places(args)


if __name__ == "__main__":
    sys.exit(main())
