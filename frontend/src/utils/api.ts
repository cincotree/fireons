export const SESSION_EXPIRED_EVENT = "fireons:session-expired";

export function getBaseHttpUrl(): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!baseUrl) {
        throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured. Please set it in your .env.local file.");
    }
    return baseUrl.replace(/\/+$/, "");
}

export async function authFetch(url: string, init: RequestInit = {}): Promise<Response> {
    const token = localStorage.getItem("token");
    const headers = new Headers(init.headers);
    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await fetch(url, { ...init, headers });
    const currentToken = localStorage.getItem("token");
    if (response.status === 401 && (currentToken === token || currentToken === null)) {
        localStorage.removeItem("token");
        window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
    }
    return response;
}
