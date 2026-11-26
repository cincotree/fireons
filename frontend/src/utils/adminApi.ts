import { getBaseHttpUrl } from "@/utils/api";
import { getAdminToken } from "@/utils/adminToken";

export class UnauthorizedError extends Error {}

export async function adminRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getAdminToken();
  if (!token) {
    throw new UnauthorizedError("Not signed in");
  }

  const { headers, ...options } = init;
  const response = await fetch(`${getBaseHttpUrl()}/api/admin${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(headers as Record<string, string> | undefined),
      Authorization: `Bearer ${token}`,
    },
  });
  if (response.status === 401) {
    throw new UnauthorizedError("Session expired");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed (${response.status})`);
  }
  return response.json();
}
