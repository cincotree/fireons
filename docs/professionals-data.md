# Professionals directory data

## What runs in production

Only the scheduled Fargate job `exchange_rate_sync` (daily at 20:30 UTC, see `scheduled_jobs` in `infra/environments/production/variables.tf`). The jobs image contains only `jobs/` and `database/`, and `backend/jobs/registry.py` registers no scraper or enrichment job. Nothing that fills the directory runs in AWS.

The API (Lambda) only reads the registry tables. It makes no calls to Google or Tavily, and needs no keys for them.

## What you run locally

Run these from the repo root. To load production, set `DATABASE_URL` to the Neon URL for that command only (`DATABASE_URL=... make scrape SOURCE=sebi_ria`), never export it in a shell that also runs the e2e tests. Keys (`GOOGLE_API_KEY`, `TAVILY_API_KEY`) come from `backend/.env`.

Two targets cover everything: `make daily` (export-places, import-places, enrich-places, enrich-nri, in that order, stopping at the first failure) and `make weekly` (scrapes all four registers, continues past a failing source and exits non-zero if any failed). To target production: `DATABASE_URL='postgresql+psycopg://...?sslmode=require' make daily`.

| Step | Command | How often | Needs |
|---|---|---|---|
| Migrate | `make migrate` | only before the first release, or after pulling migrations into a local database; the deploy applies them to production | |
| Registers | `make scrape SOURCE=<key>` for `sebi_ria`, `sebi_research_analyst`, `fee_only_india`, `fpsb_cfp` | weekly | |
| Export Google places | `make export-places` | daily until all queries finish (capped by the free quota) | `GOOGLE_API_KEY` |
| Import Google places | `make import-places` | after each export | |
| Enrich Google places | `make enrich-places` | daily until none are pending (30 searches a day by default) | `TAVILY_API_KEY` |
| NRI signals | `make enrich-nri` | after new websites are found | |
| Review NRI signals | `python -m enrichment review-queue` then `python -m enrichment review <id> confirmed\|rejected` | as needed | |

Enrichment is capped by `WEBSITE_SEARCH_DAILY_LIMIT` (default 30) and `WEBSITE_SEARCH_MONTHLY_LIMIT` (default 1000) in `backend/.env`, shared with the website finder. At the defaults, 2,400 listings take about 80 days. Raise both to go faster, but the monthly default matches the free Tavily allowance, so check your plan first.

`export-places` writes `backend/exports/places_professionals.csv`, which holds Google content. It is gitignored and is a working file only: only the place ID, Maps link, category and searched city are stored in the database, and the Google name is used in memory as the Tavily query.

## Not built

There is no JSON export and no S3 upload for this data, and no job that imports from S3. The scripts above write straight to the database that `DATABASE_URL` points at. Scheduling the scrapers or enrichment in AWS would mean registering them in `backend/jobs/registry.py`, adding `scraping/` and `enrichment/` to `Dockerfile.worker`, and adding `scheduled_jobs` entries.
