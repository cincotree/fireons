"use client";

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { useAdminSession } from "@/components/AdminShell";
import { adminRequest, UnauthorizedError } from "@/utils/adminApi";

const REFRESH_INTERVAL_MS = 3000;
const STATUSES = ["queued", "running", "succeeded", "failed"] as const;

type RunStatus = (typeof STATUSES)[number];

interface JobRun {
  id: string;
  job: string;
  payload: Record<string, unknown>;
  status: RunStatus;
  task_arn: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

function formatTime(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "-";
}

function formatDuration(run: JobRun): string {
  if (!run.started_at || !run.completed_at) {
    return "-";
  }
  const seconds = (new Date(run.completed_at).getTime() - new Date(run.started_at).getTime()) / 1000;
  return `${seconds.toFixed(1)}s`;
}

function formatPayload(payload: Record<string, unknown>): string {
  return Object.keys(payload).length === 0 ? "-" : JSON.stringify(payload);
}

export function AdminJobs() {
  const { signOut: onUnauthorized } = useAdminSession();
  const [jobs, setJobs] = useState<string[]>([]);
  const [runs, setRuns] = useState<JobRun[]>([]);
  const [job, setJob] = useState("");
  const [payload, setPayload] = useState("{}");
  const [statusFilter, setStatusFilter] = useState("");
  const [launching, setLaunching] = useState(false);
  const [launchError, setLaunchError] = useState<string | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const loadRuns = useCallback(async () => {
    try {
      const query = statusFilter ? `?status=${statusFilter}` : "";
      setRuns(await adminRequest<JobRun[]>(`/jobs/runs${query}`));
      setListError(null);
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        onUnauthorized();
        return;
      }
      setListError(error instanceof Error ? error.message : "Could not load runs");
    }
  }, [statusFilter, onUnauthorized]);

  useEffect(() => {
    adminRequest<string[]>("/jobs")
      .then((names) => {
        setJobs(names);
        setJob((current) => current || names[0] || "");
      })
      .catch((error) => {
        if (error instanceof UnauthorizedError) {
          onUnauthorized();
          return;
        }
        setListError(error.message);
      });
  }, [onUnauthorized]);

  useEffect(() => {
    loadRuns();
    const timer = setInterval(loadRuns, REFRESH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [loadRuns]);

  const launch = async (event: React.FormEvent) => {
    event.preventDefault();
    setLaunchError(null);

    let parsed: unknown;
    try {
      parsed = JSON.parse(payload || "{}");
    } catch {
      setLaunchError("Payload must be valid JSON");
      return;
    }
    if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
      setLaunchError("Payload must be a JSON object");
      return;
    }

    setLaunching(true);
    try {
      await adminRequest<JobRun>("/jobs/runs", {
        method: "POST",
        body: JSON.stringify({ job, payload: parsed }),
      });
    } catch (error) {
      if (error instanceof UnauthorizedError) {
        onUnauthorized();
        return;
      }
      setLaunchError(error instanceof Error ? error.message : "Could not launch job");
    } finally {
      setLaunching(false);
      loadRuns();
    }
  };

  return (
    <div className="max-w-5xl mx-auto p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Background jobs</h1>
        <p className="text-sm text-gray-500">Launch a job and watch its runs.</p>
      </div>

      <form onSubmit={launch} className="space-y-3">
        <div>
          <label htmlFor="job" className="block text-sm font-medium mb-1">
            Job
          </label>
          <select
            id="job"
            value={job}
            onChange={(event) => setJob(event.target.value)}
            className="border rounded px-3 py-1.5 text-sm"
          >
            {jobs.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="payload" className="block text-sm font-medium mb-1">
            Payload (JSON)
          </label>
          <textarea
            id="payload"
            value={payload}
            onChange={(event) => setPayload(event.target.value)}
            rows={3}
            className="border rounded px-3 py-1.5 text-sm font-mono w-full max-w-md"
          />
        </div>
        {launchError && (
          <p role="alert" data-testid="launch-error" className="text-red-600 text-sm">
            {launchError}
          </p>
        )}
        <Button type="submit" disabled={launching || !job}>
          {launching ? "Launching..." : "Launch job"}
        </Button>
      </form>

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">Runs</h2>
          <div className="flex items-center gap-2">
            <label htmlFor="status-filter" className="text-sm">
              Status
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="border rounded px-3 py-1.5 text-sm"
            >
              <option value="">All</option>
              {STATUSES.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
            <Button type="button" variant="outline" onClick={loadRuns}>
              Refresh
            </Button>
          </div>
        </div>
        {listError && (
          <p role="alert" className="text-red-600 text-sm">
            {listError}
          </p>
        )}
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-left border-b">
              <th className="py-2 pr-4">Job</th>
              <th className="py-2 pr-4">Status</th>
              <th className="py-2 pr-4">Run ID</th>
              <th className="py-2 pr-4">Task</th>
              <th className="py-2 pr-4">Payload</th>
              <th className="py-2 pr-4">Created</th>
              <th className="py-2 pr-4">Duration</th>
              <th className="py-2 pr-4">Error</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id} data-testid="job-run" className="border-b align-top">
                <td className="py-2 pr-4">{run.job}</td>
                <td className="py-2 pr-4" data-testid="job-run-status">
                  {run.status}
                </td>
                <td className="py-2 pr-4 font-mono text-xs" title={run.id}>
                  {run.id.slice(0, 8)}
                </td>
                <td className="py-2 pr-4 font-mono text-xs break-all" data-testid="job-run-task">
                  {run.task_arn || "-"}
                </td>
                <td className="py-2 pr-4 font-mono text-xs break-all">{formatPayload(run.payload)}</td>
                <td className="py-2 pr-4" title={`Started ${formatTime(run.started_at)}, completed ${formatTime(run.completed_at)}`}>
                  {formatTime(run.created_at)}
                </td>
                <td className="py-2 pr-4">{formatDuration(run)}</td>
                <td className="py-2 pr-4 text-red-600">{run.error_message || ""}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan={8} className="py-4 text-gray-500">
                  No runs yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
