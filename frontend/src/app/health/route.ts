import { NextResponse } from 'next/server';

export async function GET() {
    const backendHost = process.env.BACKEND_HOST;
    return NextResponse.json({
        status: 'ok',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        backend_host: backendHost,
    });
}