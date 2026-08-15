import { NextResponse } from 'next/server';

export async function POST(req: Request) {
  const body = await req.json();
  const base = (process.env.MAPPING_REGISTRY_BASE || 'http://127.0.0.1:5057').replace(/\/$/, '');

  let res: Response;
  try {
    res = await fetch(`${base}/agent/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Agent service unavailable' },
      { status: 502 },
    );
  }

  if (!res.ok) {
    return NextResponse.json({ error: await res.text() }, { status: res.status });
  }

  const data = await res.json();
  return NextResponse.json(data);
}
