import { NextResponse } from 'next/server';


export async function POST(req: Request) {
    const base = process.env.MCP_BRIDGE_BASE || 'http://127.0.0.1:5057';
    const url = base.replace(/\/$/, '') + '/call';
    try {
        const body = await req.text();
        const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body });
        const responseBody = await r.text();
        let data: unknown;
        try {
            data = JSON.parse(responseBody);
        } catch {
            data = { error: responseBody || 'Upstream returned an empty response' };
        }
        return NextResponse.json(data, { status: r.status });
    } catch (error) {
        return NextResponse.json(
            { error: error instanceof Error ? error.message : 'MCP bridge unavailable' },
            { status: 502 },
        );
    }
}
