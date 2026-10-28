from functools import lru_cache

from pydantic_settings import BaseSettings


class ScrapeSettings(BaseSettings):
    scrape_min_interval_seconds: float = 3.0
    scrape_max_pages: int = 200
    scrape_max_retries: int = 4
    scrape_timeout_seconds: float = 30.0
    scrape_user_agent: str = "Fireons-Registry-Scraper/1.0"
    scrape_schedule_cron: str = "0 3 * * sun"
    scrape_schedule_timezone: str = "Asia/Kolkata"
    scrape_completeness_ratio: float = 0.98
    scrape_delist_after_missed_runs: int = 2
    nri_max_pages_per_site: int = 5
    nri_recheck_days: int = 30
    nri_shared_domain_limit: int = 3
    nri_max_page_bytes: int = 1_500_000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_scrape_settings() -> ScrapeSettings:
    return ScrapeSettings()
