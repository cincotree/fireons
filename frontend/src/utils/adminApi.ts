import { getBaseHttpUrl } from "@/utils/api";
import { getAdminToken } from "@/utils/adminToken";

export class UnauthorizedError extends Error {}

export async function adminRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${getBaseHttpUrl()}/api/admin${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${getAdminToken()}`,
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
