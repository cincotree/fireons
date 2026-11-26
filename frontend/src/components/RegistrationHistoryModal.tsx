"use client";

import { useEffect, useRef, useState } from "react";
import { BadgeCheck, ExternalLink, Globe, Mail, MapPin, Phone, User, X } from "lucide-react";
import { Monogram } from "@/components/Monogram";
import { authFetch, getBaseHttpUrl } from "@/utils/api";
import { CONFIDENCE_LABELS } from "@/components/NriBadge";
import { NriDetail, Registration } from "@/types/professionals";

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
  const [nriDetail, setNriDetail] = useState<NriDetail | null>(null);
  const [nriError, setNriError] = useState<string | null>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    setNriDetail(null);
    setNriError(null);
    if (!registration?.nri) return;
    let cancelled = false;
    (async () => {
      try {
        const baseUrl = await getBaseHttpUrl();
        const response = await authFetch(`${baseUrl}/api/registrations/${registration.id}/nri`);
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
            {registration.verification === "unverified" && (
              <p className="mt-1.5 inline-block rounded-full border border-[#E2D3B3] bg-[#FBF5E6] px-2 py-0.5 text-xs font-semibold text-[#7A5A12]">
                Unverified: listed on Google Maps, not confirmed by a regulator or the owner
              </p>
            )}
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
            {registration.firm_name && (
              <DetailRow icon={<BadgeCheck className="h-4 w-4" />} label="Firm">
                {registration.firm_name}
              </DetailRow>
            )}
            {registration.website && (
              <DetailRow icon={<Globe className="h-4 w-4" />} label="Website">
                <a href={registration.website} target="_blank" rel="noopener noreferrer" className="text-[#0E6B57] hover:underline">
                  {registration.website}
                </a>
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
            {registration.verification !== "unverified" && (
              <DetailRow icon={<BadgeCheck className="h-4 w-4" />} label="Registration">
                <span className="tabular-nums">{registration.registration_number}</span>
                <span className="block text-xs text-[#66766F]">{registration.source_name}</span>
              </DetailRow>
            )}
            {registration.verification === "unverified" && (
              <div>
                <a
                  href={registration.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-sm text-[#0E6B57] hover:underline"
                >
                  <ExternalLink className="h-4 w-4 shrink-0 text-[#66766F]" aria-hidden="true" />
                  Google Maps link
                </a>
              </div>
            )}
          </dl>

          {registration.nri && (
            <section aria-label="NRI signals" className="mt-8">
              <h3 className="text-base font-semibold text-[#12211D]">NRI signals</h3>
              <p className="mt-1 text-sm text-[#66766F]">
                Found automatically on the firm&apos;s website. Wording from the site, not a verified claim.
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
        </div>
      </aside>
    </div>
  );
}
