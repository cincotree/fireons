"use client";

import { useEffect, useRef, useState } from "react";
import { BadgeCheck, ExternalLink, Mail, MapPin, Phone, User, X } from "lucide-react";
import { Monogram } from "@/components/Monogram";
import { getBaseHttpUrl } from "@/utils/api";
import { CONFIDENCE_LABELS } from "@/components/NriBadge";
import { NriDetail, Registration, RegistrationHistory } from "@/types/professionals";

const FIELD_LABELS: Record<string, string> = {
  name: "Name",
  kind: "Type",
  registration_number: "Registration number",
  profession_type: "Profession",
  valid_from: "Valid from",
  valid_until: "Valid until",
  validity_raw: "Validity",
  city: "City",
  state: "State",
  pincode: "Pincode",
  address_raw: "Address",
  email: "Email",
  phone: "Phone",
  contact_person: "Contact person",
  attributes: "Other details",
  source_url: "Source link",
};

export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

interface Props {
  registration: Registration | null;
  onClose: () => void;
}

function DetailRow({ icon, label, children }: { icon: React.ReactNode; label: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-3">
      <span className="mt-0.5 text-[#66766F]" aria-hidden="true">
        {icon}
      </span>
      <div className="min-w-0">
        <dt className="text-xs font-medium text-[#66766F]">{label}</dt>
        <dd className="mt-0.5 break-words text-sm text-[#12211D]">{children}</dd>
      </div>
    </div>
  );
}

export function RegistrationHistoryModal({ registration, onClose }: Props) {
  const [history, setHistory] = useState<RegistrationHistory | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [nriDetail, setNriDetail] = useState<NriDetail | null>(null);
  const [nriError, setNriError] = useState<string | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!registration) return;
    let cancelled = false;
    setHistory(null);
    setError(null);
    setLoading(true);
    (async () => {
      try {
        const baseUrl = await getBaseHttpUrl();
        const response = await fetch(`${baseUrl}/api/registrations/${registration.id}/history`);
        if (!response.ok) throw new Error("Could not load history. Please try again.");
        const data: RegistrationHistory = await response.json();
        if (!cancelled) setHistory(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Could not load history.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [registration]);

  useEffect(() => {
    setNriDetail(null);
    setNriError(null);
    if (!registration?.nri) return;
    let cancelled = false;
    (async () => {
      try {
        const baseUrl = await getBaseHttpUrl();
        const response = await fetch(`${baseUrl}/api/registrations/${registration.id}/nri`);
        if (!response.ok) throw new Error("Could not load NRI signals. Please try again.");
        const data: NriDetail = await response.json();
        if (!cancelled) setNriDetail(data);
      } catch (err) {
        if (!cancelled) setNriError(err instanceof Error ? err.message : "Could not load NRI signals.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [registration]);

  useEffect(() => {
    if (!registration) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCloseRef.current();
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    document.addEventListener("keydown", onKeyDown);
    closeButton.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [registration]);

  if (!registration) return null;

  const location = [registration.city, registration.state].filter(Boolean).join(", ");

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="panel-scrim-in absolute inset-0 bg-[#12211D]/40" onClick={onClose} aria-hidden="true" />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="history-title"
        className="panel-slide-in relative flex h-full w-full max-w-lg flex-col bg-white shadow-2xl"
      >
        <header className="flex items-start gap-4 border-b border-[#DCE5E1] px-6 py-5">
          <Monogram name={registration.name} size="lg" />
          <div className="min-w-0 flex-1">
            <h2 id="history-title" className="text-lg font-semibold leading-snug text-[#12211D]">
              {registration.name}
            </h2>
            <p className="mt-1 inline-flex items-center gap-1.5 text-sm font-medium tabular-nums text-[#0E6B57]">
              <BadgeCheck className="h-4 w-4" aria-hidden="true" />
              {registration.registration_number}
            </p>
            <p className="mt-0.5 text-sm text-[#66766F]">{registration.source_name}</p>
          </div>
          <button
            ref={closeButton}
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-2 text-[#66766F] hover:bg-[#F0F4F2] hover:text-[#12211D] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6">
          <dl className="grid gap-4">
            {registration.contact_person && (
              <DetailRow icon={<User className="h-4 w-4" />} label="Contact person">
                {registration.contact_person}
              </DetailRow>
            )}
            {(registration.address || location) && (
              <DetailRow icon={<MapPin className="h-4 w-4" />} label="Address">
                {registration.address || location}
              </DetailRow>
            )}
            {registration.email && (
              <DetailRow icon={<Mail className="h-4 w-4" />} label="Email">
                <a href={`mailto:${registration.email}`} className="text-[#0E6B57] hover:underline">
                  {registration.email}
                </a>
              </DetailRow>
            )}
            {registration.phone && (
              <DetailRow icon={<Phone className="h-4 w-4" />} label="Phone">
                <a href={`tel:${registration.phone.replace(/[^\d+]/g, "")}`} className="text-[#0E6B57] hover:underline">
                  {registration.phone}
                </a>
              </DetailRow>
            )}
            <DetailRow icon={<ExternalLink className="h-4 w-4" />} label="Published by">
              <a
                href={registration.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[#0E6B57] hover:underline"
              >
                {registration.source_name}
              </a>
            </DetailRow>
          </dl>

          {registration.nri && (
            <section aria-label="NRI signals" className="mt-8">
              <h3 className="text-base font-semibold text-[#12211D]">NRI signals</h3>
              <p className="mt-1 text-sm text-[#66766F]">
                Found automatically on the firm&apos;s website. Wording, not a verified claim: each signal is
                marked until someone reviews it.
              </p>
              {nriError && (
                <div role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
                  {nriError}
                </div>
              )}
              {nriDetail?.website && (
                <p className="mt-3 text-sm text-[#2A3A35]">
                  Website checked:{" "}
                  <a
                    href={nriDetail.website.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#0E6B57] hover:underline"
                  >
                    {nriDetail.website.domain}
                  </a>
                  {nriDetail.website.last_checked_at && ` on ${formatDateTime(nriDetail.website.last_checked_at)}`}
                </p>
              )}
              <ul className="mt-4 space-y-3">
                {nriDetail?.signals.map((signal) => (
                  <li key={signal.id} className="rounded-xl border border-[#DCE5E1] bg-[#FAFCFB] p-3">
                    <div className="flex flex-wrap items-center gap-2 text-xs font-medium">
                      <span className="rounded-full bg-[#DDEEE8] px-2 py-0.5 text-[#0B5846]">
                        {CONFIDENCE_LABELS[signal.confidence]} confidence
                      </span>
                      <span className="rounded-full bg-[#F0F4F2] px-2 py-0.5 text-[#4D5D57]">
                        {signal.review_status === "confirmed" ? "Reviewed: confirmed" : "Not yet reviewed"}
                      </span>
                      <span className="text-[#66766F]">
                        {signal.signal_type.replace(/_/g, " ")} in {signal.location}
                      </span>
                    </div>
                    <blockquote className="mt-2 break-words text-sm text-[#12211D]">
                      &ldquo;{signal.matched_text}&rdquo;
                    </blockquote>
                    <a
                      href={signal.page_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1.5 inline-flex max-w-full items-center gap-1 text-xs text-[#0E6B57] hover:underline"
                    >
                      <ExternalLink className="h-3 w-3 shrink-0" aria-hidden="true" />
                      <span className="truncate">{signal.page_url}</span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <h3 className="mt-8 text-base font-semibold text-[#12211D]">Change history</h3>
          <p className="mt-1 text-sm text-[#66766F]">Every time the published record changed, newest first.</p>

          {loading && (
            <div className="mt-5 space-y-3" aria-label="Loading history">
              <div className="h-4 w-2/3 animate-pulse rounded bg-[#E8F0ED] motion-reduce:animate-none" />
              <div className="h-4 w-1/2 animate-pulse rounded bg-[#E8F0ED] motion-reduce:animate-none" />
            </div>
          )}
          {error && (
            <div role="alert" className="mt-5 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
              {error}
            </div>
          )}

          {history && (
            <ol className="mt-5" aria-label="Change history">
              {history.versions.map((version, index) => (
                <li key={version.id} className="relative pb-6 pl-7 last:pb-0">
                  {index < history.versions.length - 1 && (
                    <span className="absolute left-[5px] top-4 h-full w-px bg-[#DCE5E1]" aria-hidden="true" />
                  )}
                  <span
                    className={`absolute left-0 top-1.5 h-[11px] w-[11px] rounded-full border-2 border-white ring-2 ${
                      version.is_initial ? "bg-[#0E6B57] ring-[#BFDDD3]" : "bg-[#B26A00] ring-[#F1D9B0]"
                    }`}
                    aria-hidden="true"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-sm font-medium text-[#12211D]">{formatDateTime(version.scraped_at)}</span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        version.is_initial ? "bg-[#DDEEE8] text-[#0E6B57]" : "bg-[#FBEFD9] text-[#8A5200]"
                      }`}
                    >
                      {version.is_initial ? "First recorded" : "Changed"}
                    </span>
                  </div>
                  {version.is_initial ? (
                    <p className="mt-1 text-sm text-[#66766F]">First published by {registration.source_name}.</p>
                  ) : (
                    <ul className="mt-2 space-y-1.5">
                      {version.changes.map((change) => (
                        <li key={change.field} className="text-sm text-[#2A3A35]">
                          <span className="font-medium">{FIELD_LABELS[change.field] ?? change.field}</span>
                          <span className="mt-0.5 block">
                            <span className="text-[#66766F] line-through">{formatValue(change.previous)}</span>
                            <span className="px-1.5 text-[#66766F]" aria-hidden="true">
                              →
                            </span>
                            <span className="sr-only"> changed to </span>
                            <span>{formatValue(change.current)}</span>
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
              {history.versions.length === 0 && (
                <li className="text-sm text-[#66766F]">No history recorded yet.</li>
              )}
            </ol>
          )}
        </div>
      </aside>
    </div>
  );
}
