"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { getBaseHttpUrl } from "@/utils/api";

export default function IngestionTestPage() {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<unknown>(null);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  const handleSubmit = async () => {
    if (!file) {
      setError("Choose a PDF to upload.");
      return;
    }

    setError(null);
    setResult(null);
    setIsSubmitting(true);
    try {
      const baseUrl = await getBaseHttpUrl();
      const token = localStorage.getItem("token");

      const formData = new FormData();
      formData.append("file", file);
      formData.append("password", password);

      const response = await fetch(`${baseUrl}/api/ingestion-test/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Ingestion failed");
      }
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ingestion failed");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto p-8 space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Ingestion Test</h1>
        <p className="text-sm text-gray-500">
          Dev-only tool. Uploads a single statement straight through the new LLM-based{" "}
          <code>ingest()</code> pipeline and shows the raw <code>NetWorth</code> result. No
          account is created, nothing is saved.
        </p>
      </div>

      <div className="space-y-3">
        <div>
          <label className="block text-sm font-medium mb-1">Statement PDF</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">
            PDF password (leave blank if unencrypted)
          </label>
          <input
            type="password"
            className="border rounded px-3 py-2 w-full max-w-sm"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {error && <p className="text-red-600 text-sm">{error}</p>}

        <Button onClick={handleSubmit} disabled={isSubmitting}>
          {isSubmitting ? "Ingesting..." : "Ingest"}
        </Button>
      </div>

      {result !== null && (
        <div>
          <h2 className="text-lg font-medium mb-2">Result</h2>
          <pre className="bg-gray-100 rounded p-4 text-sm overflow-auto whitespace-pre-wrap">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
