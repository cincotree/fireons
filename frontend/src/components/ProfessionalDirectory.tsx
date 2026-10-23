"use client";

import { useEffect, useState } from "react";
import {
  BadgeCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  History,
  Mail,
  MapPin,
  Phone,
  Search,
  SearchX,
  ShieldCheck,
  SlidersHorizontal,
  X,
} from "lucide-react";
import { Monogram } from "@/components/Monogram";
import { MultiSelect } from "@/components/MultiSelect";
import { RegistrationHistoryModal } from "@/components/RegistrationHistoryModal";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { getBaseHttpUrl } from "@/utils/api";
import { Facets, ProfessionalSource, Registration, RegistrationPage } from "@/types/professionals";

const PAGE_SIZE = 25;
const SEARCH_DEBOUNCE_MS = 300;
const NO_FACETS: Facets = { states: [], cities: [], profession_types: [] };
const FOCUS_RING =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57] focus-visible:ring-offset-2 focus-visible:ring-offset-[#E8F0ED]";
const CONTROL =
  "rounded-xl border border-[#D3DFDA] bg-white shadow-[0_1px_2px_rgba(18,33,29,0.06),0_10px_24px_-14px_rgba(18,33,29,0.28)]";

async function fetchJson<T>(path: string, failureMessage: string): Promise<T> {
  const baseUrl = await getBaseHttpUrl();
  const response = await fetch(`${baseUrl}${path}`);
  if (response.status === 429) {
    throw new Error("Too many requests. Please wait a moment and try again.");
  }
  if (!response.ok) throw new Error(failureMessage);
  return response.json();
}

interface FilterSelectProps {
  label: string;
  allLabel: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, allLabel, value, options, onChange }: FilterSelectProps) {
  return (
    <div className="relative">
      <select
        aria-label={label}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={`h-[52px] w-full appearance-none pl-4 pr-11 text-[15px] text-[#2A3A35] ${CONTROL} ${FOCUS_RING}`}
      >
        <option value="">{allLabel}</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown
        className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-[#66766F]"
        aria-hidden="true"
      />
    </div>
  );
}

function SkeletonRows() {
  return (
    <>
      {Array.from({ length: 6 }).map((_, index) => (
        <TableRow key={index} className="block border-[#E6ECE9] md:table-row">
          <TableCell className="block px-5 py-4 md:table-cell" colSpan={5}>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 animate-pulse rounded-xl bg-[#E8F0ED] motion-reduce:animate-none" />
              <div className="space-y-2">
                <div className="h-3.5 w-56 animate-pulse rounded bg-[#E8F0ED] motion-reduce:animate-none" />
                <div className="h-3 w-32 animate-pulse rounded bg-[#EFF4F2] motion-reduce:animate-none" />
              </div>
            </div>
          </TableCell>
        </TableRow>
      ))}
    </>
  );
}

export function ProfessionalDirectory() {
  const [sources, setSources] = useState<ProfessionalSource[]>([]);
  const [sourceKey, setSourceKey] = useState("");
  const [facets, setFacets] = useState<Facets>(NO_FACETS);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [stateFilter, setStateFilter] = useState<string[]>([]);
  const [cityFilter, setCityFilter] = useState<string[]>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [data, setData] = useState<RegistrationPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadToken, setReloadToken] = useState(0);
  const [selected, setSelected] = useState<Registration | null>(null);

  useEffect(() => {
    fetchJson<ProfessionalSource[]>("/api/registrations/sources", "Could not load data sources.")
      .then(setSources)
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (sourceKey) params.set("source", sourceKey);
    stateFilter.forEach((name) => params.append("state", name));
    fetchJson<Facets>(`/api/registrations/facets?${params.toString()}`, "")
      .then((loaded) => {
        setFacets(loaded);
        setCityFilter((current) => {
          const stillValid = current.filter((name) => loaded.cities.includes(name));
          return stillValid.length === current.length ? current : stillValid;
        });
      })
      .catch(() => setFacets(NO_FACETS));
  }, [sourceKey, stateFilter]);

  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(searchInput.trim());
      setPage(1);
    }, SEARCH_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    let cancelled = false;
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    if (sourceKey) params.set("source", sourceKey);
    if (search) params.set("q", search);
    stateFilter.forEach((name) => params.append("state", name));
    cityFilter.forEach((name) => params.append("city", name));
    setLoading(true);
    setError(null);
    fetchJson<RegistrationPage>(
      `/api/registrations?${params.toString()}`,
      "Could not load professionals. Please try again."
    )
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [sourceKey, search, stateFilter, cityFilter, page, reloadToken]);

  const total = data?.total ?? 0;
  const firstShown = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const lastShown = Math.min(page * PAGE_SIZE, total);
  const pageCount = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const hasNextPage = page * PAGE_SIZE < total;

  const sourceName = sources.find((candidate) => candidate.key === sourceKey)?.name ?? sourceKey;
  const appliedFilters: { key: string; label: string; kind: string; clear: () => void }[] = [
    ...(sourceKey
      ? [
          {
            key: `source:${sourceKey}`,
            label: sourceName,
            kind: "source",
            clear: () => {
              setSourceKey("");
              setStateFilter([]);
              setCityFilter([]);
            },
          },
        ]
      : []),
    ...stateFilter.map((name) => ({
      key: `state:${name}`,
      label: name,
      kind: "state",
      clear: () => setStateFilter((current) => current.filter((item) => item !== name)),
    })),
    ...cityFilter.map((name) => ({
      key: `city:${name}`,
      label: name,
      kind: "city",
      clear: () => setCityFilter((current) => current.filter((item) => item !== name)),
    })),
  ];
  const activeFilterCount = appliedFilters.length;

  const clearEverything = () => {
    setSearchInput("");
    setSearch("");
    setSourceKey("");
    setStateFilter([]);
    setCityFilter([]);
    setPage(1);
  };

  return (
    <div className="min-h-screen bg-[#F6F8F7] text-[#2A3A35]">
      <section className="border-b border-[#D3DFDA] bg-[#E8F0ED]">
        <div className="mx-auto max-w-7xl px-4 pb-8 pt-10 sm:px-6">
          <h1 className="text-3xl font-bold tracking-tight text-[#12211D] sm:text-4xl">Find a registered financial professional</h1>

          <div className="mt-6 flex items-stretch gap-3">
            <div className="relative flex-1">
              <Search
                className="pointer-events-none absolute left-5 top-1/2 h-5 w-5 -translate-y-1/2 text-[#66766F]"
                aria-hidden="true"
              />
              <input
                type="search"
                aria-label="Search"
                value={searchInput}
                onChange={(event) => setSearchInput(event.target.value)}
                placeholder="Search by name, registration number, city, state, or source..."
                className={`h-14 w-full pl-14 pr-12 text-base text-[#12211D] placeholder:text-[#7D8C86] text-ellipsis ${CONTROL} ${FOCUS_RING} [&::-webkit-search-cancel-button]:hidden`}
              />
              {searchInput && (
                <button
                  type="button"
                  aria-label="Clear search"
                  onClick={() => setSearchInput("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-[#66766F] hover:bg-[#F0F4F2] hover:text-[#12211D] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
                >
                  <X className="h-4 w-4" aria-hidden="true" />
                </button>
              )}
            </div>
            <button
              type="button"
              onClick={() => setFiltersOpen((open) => !open)}
              aria-expanded={filtersOpen}
              aria-controls="directory-filters"
              className={`inline-flex h-14 items-center gap-2 px-4 text-[15px] font-medium text-[#12211D] hover:bg-[#F6F8F7] sm:px-5 ${CONTROL} ${FOCUS_RING} ${
                filtersOpen || activeFilterCount > 0 ? "border-[#0E6B57]" : ""
              }`}
            >
              <SlidersHorizontal
                className={`h-5 w-5 ${activeFilterCount > 0 ? "text-[#0E6B57]" : "text-[#66766F]"}`}
                aria-hidden="true"
              />
              <span className="sr-only sm:not-sr-only">
                {activeFilterCount > 0 ? `Filters (${activeFilterCount})` : "Filters"}
              </span>
            </button>
          </div>

          {filtersOpen && (
            <div id="directory-filters" className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2">
              <FilterSelect
                label="Source"
                allLabel="All sources"
                value={sourceKey}
                options={sources.map((candidate) => ({ value: candidate.key, label: candidate.name }))}
                onChange={(value) => {
                  setSourceKey(value);
                  setStateFilter([]);
                  setCityFilter([]);
                  setPage(1);
                }}
              />
              <MultiSelect
                label="State"
                noun="states"
                allLabel="All states"
                options={facets.states}
                value={stateFilter}
                onChange={(value) => {
                  setStateFilter(value);
                  setPage(1);
                }}
                triggerClassName={`${CONTROL} ${FOCUS_RING}`}
              />
              <MultiSelect
                label="City"
                noun="cities"
                allLabel="All cities"
                options={facets.cities}
                value={cityFilter}
                onChange={(value) => {
                  setCityFilter(value);
                  setPage(1);
                }}
                triggerClassName={`${CONTROL} ${FOCUS_RING}`}
              />
            </div>
          )}

          {appliedFilters.length > 0 && (
            <ul className="mt-4 flex flex-wrap gap-2" aria-label="Applied filters">
              {appliedFilters.map((filter) => (
                <li key={filter.key}>
                  <button
                    type="button"
                    onClick={() => {
                      filter.clear();
                      setPage(1);
                    }}
                    aria-label={`Remove ${filter.label} ${filter.kind} filter`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-[#BFDDD3] bg-white py-1 pl-3 pr-2 text-sm font-medium text-[#0E6B57] hover:bg-[#F6FBF9] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
                  >
                    {filter.label}
                    <X className="h-3.5 w-3.5" aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">
        {error && (
          <div
            role="alert"
            className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          >
            <span>{error}</span>
            <button
              type="button"
              onClick={() => setReloadToken((token) => token + 1)}
              className="rounded-lg border border-red-300 bg-white px-3 py-1.5 font-medium text-red-800 hover:bg-red-100 focus:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
            >
              Retry
            </button>
          </div>
        )}

        <p className="mb-3 min-h-5 text-sm text-[#66766F]" aria-live="polite">
          {total > 0 ? `Showing ${firstShown}–${lastShown} of ${total.toLocaleString()}` : ""}
        </p>

        <div className="overflow-hidden rounded-2xl border border-[#DCE5E1] bg-white shadow-[0_1px_2px_rgba(18,33,29,0.04)]">
          <Table className="block md:table md:table-auto">
            <TableHeader className="hidden border-b border-[#DCE5E1] bg-[#FAFCFB] md:table-header-group">
              <TableRow className="hover:bg-transparent">
                <TableHead className="h-11 px-5 text-xs font-semibold text-[#66766F]">Name</TableHead>
                <TableHead className="h-11 px-4 text-xs font-semibold text-[#66766F]">Registration no.</TableHead>
                <TableHead className="h-11 px-4 text-xs font-semibold text-[#66766F]">Location</TableHead>
                <TableHead className="h-11 px-4 text-xs font-semibold text-[#66766F]">Contact</TableHead>
                <TableHead className="h-11 px-4 text-xs font-semibold text-[#66766F]">Source</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody className={`block md:table-row-group transition-opacity ${loading && data ? "opacity-60" : ""}`}>
              {loading && !data && <SkeletonRows />}
              {data?.items.map((registration) => (
                <TableRow
                  key={registration.id}
                  className="block border-[#E6ECE9] px-5 py-4 hover:bg-[#F8FBFA] md:table-row md:px-0 md:py-0"
                >
                  <TableCell className="block p-0 md:table-cell md:px-5 md:py-4">
                    <div className="flex items-center gap-3">
                      <Monogram name={registration.name} />
                      <div className="min-w-0">
                        <button
                          type="button"
                          onClick={() => setSelected(registration)}
                          aria-label={`View history for ${registration.name}`}
                          className="group inline-flex max-w-full items-center gap-1.5 rounded text-left text-[15px] font-semibold text-[#12211D] hover:text-[#0E6B57] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
                        >
                          <span className="break-words">{registration.name}</span>
                          <History
                            className="h-3.5 w-3.5 shrink-0 text-[#0E6B57] opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
                            aria-hidden="true"
                          />
                        </button>
                        <p className="text-xs text-[#66766F]">
                          {registration.kind === "firm" ? "Firm" : "Individual"}
                        </p>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="block whitespace-nowrap p-0 pt-2 md:table-cell md:px-4 md:py-4">
                    <span className="inline-flex items-center gap-1.5 text-sm font-medium tabular-nums text-[#12211D]">
                      <BadgeCheck className="h-4 w-4 text-[#0E6B57]" aria-hidden="true" />
                      {registration.registration_number}
                    </span>
                  </TableCell>
                  <TableCell className="block p-0 pt-2 md:table-cell md:px-4 md:py-4">
                    {registration.city || registration.state ? (
                      <span className="inline-flex items-start gap-1.5 text-sm">
                        <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#66766F]" aria-hidden="true" />
                        {[registration.city, registration.state].filter(Boolean).join(", ")}
                      </span>
                    ) : (
                      <span className="text-sm text-[#7D8C86]">—</span>
                    )}
                  </TableCell>
                  <TableCell className="block p-0 pt-2 md:table-cell md:px-4 md:py-4">
                    <div className="flex flex-col gap-1 text-sm">
                      {registration.email && (
                        <a
                          href={`mailto:${registration.email}`}
                          className="inline-flex max-w-[240px] items-center gap-1.5 rounded text-[#0E6B57] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
                        >
                          <Mail className="h-4 w-4 shrink-0" aria-hidden="true" />
                          <span className="truncate">{registration.email}</span>
                        </a>
                      )}
                      {registration.phone && (
                        <a
                          href={`tel:${registration.phone.replace(/[^\d+]/g, "")}`}
                          className="inline-flex items-center gap-1.5 rounded tabular-nums text-[#2A3A35] hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
                        >
                          <Phone className="h-4 w-4 shrink-0 text-[#66766F]" aria-hidden="true" />
                          {registration.phone}
                        </a>
                      )}
                      {!registration.email && !registration.phone && <span className="text-[#7D8C86]">—</span>}
                    </div>
                  </TableCell>
                  <TableCell className="block p-0 pt-2 md:table-cell md:px-4 md:py-4">
                    <a
                      href={registration.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 rounded-full border border-[#D3DFDA] bg-[#F6F8F7] px-2.5 py-1 text-xs font-semibold text-[#12211D] hover:border-[#0E6B57] hover:text-[#0E6B57] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
                    >
                      <ShieldCheck className="h-3.5 w-3.5 text-[#0E6B57]" aria-hidden="true" />
                      {registration.regulator}
                      <ExternalLink className="h-3 w-3 text-[#66766F]" aria-hidden="true" />
                    </a>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {!loading && !error && data && data.items.length === 0 && (
            <div className="flex flex-col items-center px-6 py-16 text-center">
              <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#E8F0ED] text-[#0E6B57]">
                <SearchX className="h-6 w-6" aria-hidden="true" />
              </span>
              <p className="mt-4 text-base font-semibold text-[#12211D]">No professionals match your filters.</p>
              <p className="mt-1 max-w-sm text-sm text-[#66766F]">
                Check the spelling, try fewer words, or remove a filter.
              </p>
              <button
                type="button"
                onClick={clearEverything}
                className="mt-5 rounded-xl bg-[#0E6B57] px-4 py-2.5 text-sm font-semibold text-white hover:bg-[#0B5846] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57] focus-visible:ring-offset-2"
              >
                Clear search and filters
              </button>
            </div>
          )}
        </div>

        <nav className="mt-5 flex items-center justify-between" aria-label="Pagination">
          <span className="text-sm text-[#66766F]">{total > 0 ? `Page ${page} of ${pageCount}` : ""}</span>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={page <= 1 || loading}
              onClick={() => setPage(page - 1)}
              className="inline-flex h-10 items-center gap-1 rounded-xl border border-[#D3DFDA] bg-white pl-3 pr-4 text-sm font-medium text-[#12211D] hover:bg-[#F6F8F7] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57] disabled:cursor-not-allowed disabled:opacity-45"
            >
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              Previous
            </button>
            <button
              type="button"
              disabled={!hasNextPage || loading}
              onClick={() => setPage(page + 1)}
              className="inline-flex h-10 items-center gap-1 rounded-xl border border-[#D3DFDA] bg-white pl-4 pr-3 text-sm font-medium text-[#12211D] hover:bg-[#F6F8F7] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57] disabled:cursor-not-allowed disabled:opacity-45"
            >
              Next
              <ChevronRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        </nav>
      </main>

      <RegistrationHistoryModal registration={selected} onClose={() => setSelected(null)} />
    </div>
  );
}
