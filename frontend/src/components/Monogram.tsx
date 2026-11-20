const PALETTE: { background: string; color: string }[] = [
  { background: "#DDEEE8", color: "#0E6B57" },
  { background: "#E3EAF6", color: "#2F4F8F" },
  { background: "#F3EBDD", color: "#7A5B1E" },
  { background: "#EDE6F2", color: "#5B3F7A" },
  { background: "#F5E4E4", color: "#8A3B3B" },
  { background: "#E1EEF2", color: "#26606F" },
];

export function initialsFor(name: string): string {
  const words = name.split(/\s+/).filter((word) => /[A-Za-z0-9]/.test(word));
  const wordsStartingWithLetter = words.filter((word) => /^[^A-Za-z0-9]*[A-Za-z]/.test(word));
  const chosen = wordsStartingWithLetter.length > 0 ? wordsStartingWithLetter : words;
  const letters = chosen.slice(0, 2).map((word) => word.match(/[A-Za-z0-9]/)?.[0] ?? "");
  return letters.join("").toUpperCase() || "?";
}

function paletteFor(name: string) {
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

interface MonogramProps {
  name: string;
  size?: "md" | "lg";
}

export function Monogram({ name, size = "md" }: MonogramProps) {
  const { background, color } = paletteFor(name);
  const dimensions = size === "lg" ? "h-14 w-14 text-lg" : "h-10 w-10 text-sm";
  return (
    <span
      aria-hidden="true"
      className={`inline-flex shrink-0 items-center justify-center rounded-xl font-semibold tracking-tight ${dimensions}`}
      style={{ background, color }}
    >
      {initialsFor(name)}
    </span>
  );
}
