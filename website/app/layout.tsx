import type { Metadata } from "next";
import { Raleway } from "next/font/google";
import "./globals.css";
import SiteChrome from "@/components/SiteChrome";
import { SITE_URL } from "@/lib/config";

const raleway = Raleway({
  variable: "--font-raleway",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

const DEFAULT_TITLE = "Fireons - Your Path to Financial Independence";
const DEFAULT_DESCRIPTION =
  "Join the FIRE community. Track your net worth, share your journey, and connect with financial professionals.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: DEFAULT_TITLE,
  description: DEFAULT_DESCRIPTION,
  keywords: "FIRE, financial independence, retire early, net worth tracking, finance community",
  openGraph: {
    type: "website",
    siteName: "Fireons",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
  twitter: {
    card: "summary_large_image",
    title: DEFAULT_TITLE,
    description: DEFAULT_DESCRIPTION,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={raleway.variable}>
      <body className="antialiased font-sans">
        <SiteChrome>{children}</SiteChrome>
      </body>
    </html>
  );
}
