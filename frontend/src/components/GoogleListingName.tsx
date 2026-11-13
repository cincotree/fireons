"use client";

import { useEffect, useState } from "react";
import { ExternalLink } from "lucide-react";
import { Monogram } from "@/components/Monogram";
import { authFetch, getBaseHttpUrl } from "@/utils/api";
import { Registration } from "@/types/professionals";

interface GoogleDetails {
  name: string | null;
  address: string | null;
  maps_url: string | null;
}

interface GoogleListingNameProps {
  registration: Registration;
}

export function GoogleListingName({ registration }: GoogleListingNameProps) {
  const [details, setDetails] = useState<GoogleDetails | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setDetails(null);
    setFailed(false);
    (async () => {
      try {
        const baseUrl = await getBaseHttpUrl();
        const response = await authFetch(`${baseUrl}/registrations/${registration.id}/google`);
        if (!response.ok) throw new Error("unavailable");
        const body: GoogleDetails = await response.json();
        if (!cancelled) setDetails(body);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [registration.id]);

  const name = details?.name ?? null;
  const mapsUrl = details?.maps_url ?? registration.source_url;

  return (
    <div className="flex items-center gap-3" data-testid="google-listing">
      <Monogram name={name ?? "Google listing"} />
      <div className="min-w-0">
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="group inline-flex max-w-full items-center gap-1.5 rounded text-left text-[15px] font-semibold text-[#12211D] hover:text-[#0E6B57] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57]"
        >
          <span className="break-words">
            {name ?? (failed ? "View on Google Maps" : "Loading from Google Maps...")}
          </span>
          <ExternalLink className="h-3.5 w-3.5 shrink-0 text-[#0E6B57]" aria-hidden="true" />
        </a>
        {details?.address && <p className="text-xs text-[#66766F]">{details.address}</p>}
        <p className="flex flex-wrap items-center gap-x-2 text-xs text-[#66766F]">
          <span className="rounded-full border border-[#E2D3B3] bg-[#FBF5E6] px-2 py-0.5 font-semibold text-[#7A5A12]">
            Unverified
          </span>
          <span>Details from Google Maps</span>
        </p>
      </div>
    </div>
  );
}
