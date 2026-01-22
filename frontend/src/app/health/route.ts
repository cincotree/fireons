import { NextResponse } from 'next/server';

export async function GET() {
    console.log("GET /health");
    const backendHost = process.env.BACKEND_HOST || process.env.NEXT_PUBLIC_BACKEND_HOST;
    return NextResponse.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        backend_host: backendHost,
    });
}