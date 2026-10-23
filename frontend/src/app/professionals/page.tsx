import type { Metadata } from "next";
import { Public_Sans } from "next/font/google";
import { ProfessionalDirectory } from "@/components/ProfessionalDirectory";

const publicSans = Public_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: "Find a registered financial professional",
  description:
    "Search registered financial professionals by name, registration number or city, and see their contact details.",
};

export default function ProfessionalsPage() {
  return (
    <div className={publicSans.className}>
      <ProfessionalDirectory />
    </div>
  );
}
