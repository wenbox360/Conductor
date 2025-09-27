import { NextResponse } from 'next/server';


export async function POST(req: Request) {
const base = process.env.MCP_BRIDGE_BASE;
if (!base) return NextResponse.json({ error: 'MCP_BRIDGE_BASE not set' }, { status: 501 });
const body = await req.json();
const url = base.replace(/\/$/, '') + '/call';
const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
if (!r.ok) return NextResponse.json({ error: `Upstream ${r.status}` }, { status: 502 });
const data = await r.json();
return NextResponse.json(data);
}