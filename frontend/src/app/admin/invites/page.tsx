"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getBaseHttpUrl } from "@/utils/api";

interface Invite {
  id: string;
  label: string | null;
  max_uses: number;
  use_count: number;
  expires_at: string | null;
  revoked_at: string | null;
  created_at: string;
  status: string;
  redeemed_by: string[];
}

interface CreatedInvite extends Invite {
  code: string;
}

const STATUS_STYLES: Record<string, string> = {
  active: "bg-green-100 text-green-800",
  exhausted: "bg-gray-100 text-gray-700",
  expired: "bg-yellow-100 text-yellow-800",
  revoked: "bg-red-100 text-red-800",
};

function authHeaders(): HeadersInit {
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${localStorage.getItem("token")}`,
  };
}

async function errorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : fallback;
  } catch {
    return fallback;
  }
}

export default function InvitesPage() {
  const { user, isAuthenticated, loading } = useAuth();
  const router = useRouter();
  const [invites, setInvites] = useState<Invite[]>([]);
  const [created, setCreated] = useState<CreatedInvite | null>(null);
  const [label, setLabel] = useState("");
  const [maxUses, setMaxUses] = useState("1");
  const [expiresInDays, setExpiresInDays] = useState("14");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const loadInvites = useCallback(async () => {
    const response = await fetch(`${getBaseHttpUrl()}/api/admin/invites`, { headers: authHeaders() });
    if (!response.ok) {
      setError(await errorMessage(response, "Failed to load invites"));
      return;
    }
    setInvites(await response.json());
  }, []);

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isAuthenticated, loading, router]);

  useEffect(() => {
    if (user?.is_superadmin) {
      loadInvites();
    }
  }, [user, loadInvites]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const response = await fetch(`${getBaseHttpUrl()}/api/admin/invites`, {
        method: "POST",
        headers: authHeaders(),
        body: JSON.stringify({
          label: label.trim() || null,
          max_uses: Number(maxUses),
          expires_in_days: expiresInDays.trim() ? Number(expiresInDays) : null,
        }),
      });
      if (!response.ok) {
        setError(await errorMessage(response, "Failed to create invite"));
        return;
      }
      setCreated(await response.json());
      setLabel("");
      await loadInvites();
    } finally {
      setSubmitting(false);
    }
  };

  const handleRevoke = async (inviteId: string) => {
    setError("");
    const response = await fetch(`${getBaseHttpUrl()}/api/admin/invites/${inviteId}/revoke`, {
      method: "POST",
      headers: authHeaders(),
    });
    if (!response.ok) {
      setError(await errorMessage(response, "Failed to revoke invite"));
      return;
    }
    await loadInvites();
  };

  if (loading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-lg">Loading...</p>
      </div>
    );
  }

  if (!user?.is_superadmin) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-12">
        <p className="text-lg text-gray-700">Not authorized</p>
      </div>
    );
  }

  const inviteLink = created ? `${window.location.origin}/register?invite=${created.code}` : "";

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Invites</h1>

      {error && (
        <div role="alert" className="rounded-md bg-red-50 p-4 text-sm text-red-800">
          {error}
        </div>
      )}

      <form onSubmit={handleCreate} className="bg-white rounded-lg shadow p-6 grid gap-4 sm:grid-cols-4 items-end">
        <div className="sm:col-span-2">
          <label htmlFor="invite-label" className="block text-sm font-medium text-gray-700">
            Label
          </label>
          <input
            id="invite-label"
            type="text"
            maxLength={255}
            placeholder="Who is this for?"
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="invite-max-uses" className="block text-sm font-medium text-gray-700">
            Max uses
          </label>
          <input
            id="invite-max-uses"
            type="number"
            min={1}
            max={1000}
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900"
            value={maxUses}
            onChange={(e) => setMaxUses(e.target.value)}
          />
        </div>
        <div>
          <label htmlFor="invite-expires" className="block text-sm font-medium text-gray-700">
            Expires in days
          </label>
          <input
            id="invite-expires"
            type="number"
            min={1}
            max={365}
            placeholder="No expiry"
            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md text-sm text-gray-900"
            value={expiresInDays}
            onChange={(e) => setExpiresInDays(e.target.value)}
          />
        </div>
        <div className="sm:col-span-4">
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-md disabled:opacity-50"
          >
            {submitting ? "Generating..." : "Generate invite"}
          </button>
        </div>
      </form>

      {created && (
        <div className="rounded-lg border border-green-300 bg-green-50 p-6 space-y-3">
          <p className="text-sm font-medium text-green-900">
            Copy this invite now. The code is not shown again.
          </p>
          <div className="flex items-center gap-3">
            <code data-testid="new-invite-code" className="px-3 py-1.5 bg-white border rounded text-sm">
              {created.code}
            </code>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(created.code)}
              className="text-sm text-blue-700 hover:underline"
            >
              Copy code
            </button>
          </div>
          <div className="flex items-center gap-3">
            <code data-testid="new-invite-link" className="px-3 py-1.5 bg-white border rounded text-sm break-all">
              {inviteLink}
            </code>
            <button
              type="button"
              onClick={() => navigator.clipboard.writeText(inviteLink)}
              className="text-sm text-blue-700 hover:underline"
            >
              Copy link
            </button>
          </div>
        </div>
      )}

      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-left text-gray-600">
            <tr>
              <th className="px-4 py-3 font-medium">Label</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Uses</th>
              <th className="px-4 py-3 font-medium">Expires</th>
              <th className="px-4 py-3 font-medium">Used by</th>
              <th className="px-4 py-3 font-medium">Created</th>
              <th className="px-4 py-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-gray-900">
            {invites.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-gray-500">
                  No invites yet
                </td>
              </tr>
            )}
            {invites.map((invite) => (
              <tr key={invite.id} data-testid="invite-row">
                <td className="px-4 py-3">{invite.label ?? "-"}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${STATUS_STYLES[invite.status] ?? ""}`}>
                    {invite.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {invite.use_count}/{invite.max_uses}
                </td>
                <td className="px-4 py-3">
                  {invite.expires_at ? new Date(invite.expires_at).toLocaleDateString() : "Never"}
                </td>
                <td className="px-4 py-3">{invite.redeemed_by.join(", ") || "-"}</td>
                <td className="px-4 py-3">{new Date(invite.created_at).toLocaleDateString()}</td>
                <td className="px-4 py-3 text-right">
                  {invite.status === "active" && (
                    <button
                      type="button"
                      onClick={() => handleRevoke(invite.id)}
                      className="text-red-700 hover:underline"
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
