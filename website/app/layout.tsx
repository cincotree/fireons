import type { Metadata } from "next";
import { Raleway } from "next/font/google";
import "./globals.css";
import SiteChrome from "@/components/SiteChrome";

const raleway = Raleway({
  variable: "--font-raleway",
  subsets: ["latin"],
  weight: ["300", "400", "500", "600", "700"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "Fireons - Your Path to Financial Independence",
  description: "Join the FIRE community. Track your net worth, share your journey, and connect with financial professionals.",
  keywords: "FIRE, financial independence, retire early, net worth tracking, finance community",
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
