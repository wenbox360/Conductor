import { NextResponse } from 'next/server';


export async function GET() {
    const base = process.env.MCP_BRIDGE_BASE || 'http://127.0.0.1:5057';
    const url = base.replace(/\/$/, '') + '/tools';
    try {
        const r = await fetch(url, { cache: 'no-store' });
        const body = await r.text();
        let data: unknown;
        try {
            data = JSON.parse(body);
        } catch {
            data = { error: body || 'Upstream returned an empty response' };
        }
        return NextResponse.json(data, { status: r.status });
    } catch (error) {
        return NextResponse.json(
            { error: error instanceof Error ? error.message : 'MCP bridge unavailable' },
            { status: 502 },
        );
    }
}
