"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AdminJobs } from "@/components/AdminJobs";
import { clearAdminToken, getAdminToken } from "@/utils/adminToken";

export default function AdminJobsPage() {
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (getAdminToken()) {
      setReady(true);
    } else {
      router.replace("/admin/login");
    }
  }, [router]);

  const signOut = useCallback(() => {
    clearAdminToken();
    router.replace("/admin/login");
  }, [router]);

  if (!ready) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  return <AdminJobs onUnauthorized={signOut} onSignOut={signOut} />;
}
