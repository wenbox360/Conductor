import { NextResponse } from 'next/server';

const base = (process.env.MAPPING_REGISTRY_BASE || 'http://127.0.0.1:5057').replace(/\/$/,'');

async function forwardJson(response: Response) {
  const body = await response.text();
  let data: unknown;
  try { data = JSON.parse(body); }
  catch { data = { error: body || 'Upstream returned an empty response' }; }
  return NextResponse.json(data, { status: response.status });
}

function unavailable(error: unknown) {
  return NextResponse.json(
    { error: error instanceof Error ? error.message : 'Mapping registry unavailable' },
    { status: 502 },
  );
}

export async function GET() {
  try {
    return forwardJson(await fetch(`${base}/mappings`, { cache: 'no-store' }));
  } catch (error) {
    return unavailable(error);
  }
}

export async function POST(req: Request) {
  const body = await req.text();
  try {
    const response = await fetch(`${base}/mappings`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body,
    });
    return forwardJson(response);
  } catch (error) {
    return unavailable(error);
  }
}

export async function DELETE(req: Request) {
  const { searchParams } = new URL(req.url);
  const id = searchParams.get('id');
  if (!id) return NextResponse.json({ error: 'id required' }, { status: 400 });

  try {
    const response = await fetch(`${base}/mappings/${encodeURIComponent(id)}`, { method: 'DELETE' });
    return forwardJson(response);
  } catch (error) {
    return unavailable(error);
  }
}
