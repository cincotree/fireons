"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { AdminJobs } from "@/components/AdminJobs";

export default function AdminJobsPage() {
  const { user, isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  if (loading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  if (!user?.is_admin) {
    return (
      <div className="max-w-3xl mx-auto p-8">
        <p role="alert" className="text-red-600">
          Admin access required
        </p>
      </div>
    );
  }

  return <AdminJobs />;
}
