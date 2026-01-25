
import FireDashboardClient from "@/components/fire-dashboard/FireDashboardClient";
import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "FIRE Dashboard | Net Worth Tracker",
    description: "Track your journey to Financial Independence",
};

export default function FireDashboardPage() {
    return <FireDashboardClient />;
}
