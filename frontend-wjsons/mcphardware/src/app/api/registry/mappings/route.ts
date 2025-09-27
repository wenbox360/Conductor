import { NextResponse } from 'next/server';

const base = (process.env.NEXT_PUBLIC_MAPPING_REGISTRY_BASE || '').replace(/\/$/,'');

export async function GET() {
  if (!base) return NextResponse.json({ error: 'NEXT_PUBLIC_MAPPING_REGISTRY_BASE not set' }, { status: 500 });
  const r = await fetch(`${base}/mappings`, { cache: 'no-store' });
  const data = await r.json();
  return NextResponse.json(data, { status: r.status });
}

export async function POST(req: Request) {
  if (!base) return NextResponse.json({ error: 'NEXT_PUBLIC_MAPPING_REGISTRY_BASE not set' }, { status: 500 });
  const body = await req.text();
  const r = await fetch(`${base}/mappings`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });

  let data: any = null;
  try { data = await r.json(); }
  catch { data = { error: 'Upstream returned non-JSON response' }; }

  return NextResponse.json(data, { status: r.status });
}

export async function DELETE(req: Request) {
  if (!base) return NextResponse.json({ error: 'NEXT_PUBLIC_MAPPING_REGISTRY_BASE not set' }, { status: 500 });
  const { searchParams } = new URL(req.url);
  const id = searchParams.get('id');
  if (!id) return NextResponse.json({ error: 'id required' }, { status: 400 });

  const r = await fetch(`${base}/mappings/${encodeURIComponent(id)}`, { method: 'DELETE' });
  let data:any = null; try { data = await r.json(); } catch { data = {}; }
  return NextResponse.json(data, { status: r.status });
}
