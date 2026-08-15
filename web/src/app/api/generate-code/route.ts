import { NextResponse } from 'next/server';

const base = (process.env.MAPPING_REGISTRY_BASE || 'http://127.0.0.1:5057').replace(/\/$/,'');

export async function POST(req: Request) {
  try {
    const body = await req.text();
    const r = await fetch(`${base}/generate-code`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body,
    });

    let data: unknown = null;
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
