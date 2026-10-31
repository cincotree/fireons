export function getBaseHttpUrl(): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
    if (!baseUrl) {
        throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured. Please set it in your .env.local file.");
    }
    return baseUrl.replace(/\/+$/, "");
}
