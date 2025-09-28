import { NextResponse } from 'next/server';

const base = (process.env.NEXT_PUBLIC_MAPPING_REGISTRY_BASE || '').replace(/\/$/,'');

export async function POST(req: Request) {
  if (!base) {
    return NextResponse.json({ error: 'NEXT_PUBLIC_MAPPING_REGISTRY_BASE not set' }, { status: 500 });
  }

  try {
    const body = await req.text();
    const r = await fetch(`${base}/generate-code`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body,
    });

    let data: any = null;
    try { 
      data = await r.json(); 
    } catch { 
      data = { error: 'Upstream returned non-JSON response' }; 
    }

    return NextResponse.json(data, { status: r.status });
  } catch (error) {
    return NextResponse.json({ 
      error: 'Failed to generate code', 
      details: error instanceof Error ? error.message : 'Unknown error' 
    }, { status: 500 });
  }
}
