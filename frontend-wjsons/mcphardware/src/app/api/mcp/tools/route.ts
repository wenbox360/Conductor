import { NextResponse } from 'next/server';


export async function GET() {
    const base = process.env.MCP_BRIDGE_BASE;
    if (!base) return NextResponse.json({ error: 'MCP_BRIDGE_BASE not set' }, { status: 501 });
    const url = base.replace(/\/$/, '') + '/tools';
    const r = await fetch(url, { cache: 'no-store' });
    if (!r.ok) return NextResponse.json({ error: `Upstream ${r.status}` }, { status: 502 });
    const data = await r.json();
    return NextResponse.json(data);
}