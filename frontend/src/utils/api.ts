export function getBaseHttpUrl(): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!baseUrl) {
        throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured. Please set it in your .env.local file.");
    }
    return baseUrl.replace(/\/+$/, "");
}

export async function authFetch(url: string): Promise<Response> {
    const token = localStorage.getItem("token");
    const response = await fetch(url, token ? { headers: { Authorization: `Bearer ${token}` } } : undefined);
    if (response.status === 401 || response.status === 403) {
        localStorage.removeItem("token");
        window.location.assign("/login/");
    }
    return response;
}
