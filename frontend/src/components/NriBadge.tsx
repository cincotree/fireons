import { Globe2 } from "lucide-react";
import { NriSummary } from "@/types/professionals";

const STYLES: Record<NriSummary["confidence"], string> = {
  high: "border-[#BFDDD3] bg-[#DDEEE8] text-[#0B5846]",
  medium: "border-[#F1D9B0] bg-[#FBEFD9] text-[#8A5200]",
  low: "border-[#D3DFDA] bg-[#F0F4F2] text-[#4D5D57]",
};

export const CONFIDENCE_LABELS: Record<NriSummary["confidence"], string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

interface Props {
  nri: NriSummary;
  onClick: () => void;
  name: string;
}

export function NriBadge({ nri, onClick, name }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={`NRI signals for ${name}: ${CONFIDENCE_LABELS[nri.confidence]} confidence, ${nri.signal_count} found`}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-semibold hover:brightness-95 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#0E6B57] ${STYLES[nri.confidence]}`}
    >
      <Globe2 className="h-3.5 w-3.5" aria-hidden="true" />
      NRI {CONFIDENCE_LABELS[nri.confidence]}
      <span className="tabular-nums opacity-80">({nri.signal_count})</span>
    </button>
  );
}
