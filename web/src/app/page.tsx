'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import type { SchemaValue, Tool, ToolInputSchema } from '@/lib/api';
import { jsonFetch } from '@/lib/api';
import { Bolt, Radio, Cable, Webhook } from 'lucide-react';
import dynamic from 'next/dynamic';
import HardwareMapper from '@/components/HardwareMapper';
import CommandChat from '@/components/CommandChat';
import type { Mapping } from '@/types/mapping';


const Scene3D = dynamic(() => import('@/components/Scene3D'), { ssr: false });

function Badge({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span className={`badge ${
      ok 
        ? 'border-status-success/30 bg-status-success/10 text-status-success' 
        : 'border-status-error/30 bg-status-error/10 text-status-error'
    }`}>
      {label ?? (ok ? 'OK' : '—')}
    </span>
  );
}

function SchemaForm({
  schema,
  value,
  onChange,
}: {
  schema: ToolInputSchema;
  value: Record<string, SchemaValue>;
  onChange: (value: Record<string, SchemaValue>) => void;
}) {
  const props = schema.properties ?? {};
  const required = schema.required ?? [];
  return (
    <div className="grid md:grid-cols-2 gap-3">
      {Object.entries(props).map(([k, spec]) => {
        const isReq = required.includes(k);
        const title = spec.title || k;
        const type = spec.type;
        const enums = spec.enum;
        const val = value[k] ?? spec.default ?? (type==='number'?0:type==='boolean'?false:'');
        const set = (nextValue: SchemaValue) => onChange({ ...value, [k]: nextValue });
        return (
          <div key={k}>
            <label className="block mb-1 text-sm text-muted">{title}{isReq && <span className="text-status-error"> *</span>}</label>
            {enums?.length ? (
              <select className="input" value={String(val)} onChange={(e)=>set(e.target.value)}>
                {enums.map((o)=> <option key={String(o)} value={String(o)}>{String(o)}</option>)}
              </select>
            ) : type==='boolean' ? (
              <input type="checkbox" checked={!!val} onChange={(e)=>set(e.target.checked)} />
            ) : type==='number' || type==='integer' ? (
              <input
                className="input"
                type="number"
                min={spec.minimum}
                max={spec.maximum}
                value={String(val)}
                onChange={(e)=>set(Number(e.target.value))}
              />
            ) : (
              <input className="input" value={String(val)} onChange={(e)=>set(e.target.value)} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function Page() {
  const [toolsUrl, setToolsUrl] = useState('/api/mcp/tools');
  const callUrl = '/api/mcp/call';

  const [tools, setTools] = useState<Tool[]>([]);
  const [toolsOk, setToolsOk] = useState(false);

  const [selected, setSelected] = useState<Tool | null>(null);
  const [args, setArgs] = useState<Record<string, SchemaValue>>({});

  const [savedMappings, setSavedMappings] = useState<Mapping[]>([]);
  const [mapperRevision, setMapperRevision] = useState(0);

  const [log, setLog] = useState<{ id:string; t:string; text:string; meta?:unknown; level:'ok'|'err'|'info' }[]>([]);
  const logRef = useRef<HTMLDivElement | null>(null);
  useEffect(()=>{ if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [log]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/registry/mappings', { cache: 'no-store' });
        if (r.ok) {
          const data: { mappings?: Mapping[] } = await r.json();
          setSavedMappings(data.mappings || []);
          setMapperRevision(revision => revision + 1);
        }
      } catch {}
    })();
  }, []);

  const loadTools = useCallback(async (url: string) => {
    try {
      const data = await jsonFetch<Tool[] | { tools?: Tool[] }>(url);
      const list: Tool[] = Array.isArray(data) ? data : data.tools || [];
      setTools(list);
      setToolsOk(true);
      if (list[0]) {
        setSelected(list[0]);
        const seed: Record<string, SchemaValue> = {};
        const props = list[0].input_schema?.properties || {};
        for (const [k, v] of Object.entries(props)) if (v.default !== undefined) seed[k] = v.default;
        setArgs(seed);
      } else {
        setSelected(null);
        setArgs({});
      }
    } catch (error: unknown) {
      setToolsOk(false);
      setSelected(null);
      setArgs({});
      const message = error instanceof Error ? error.message : String(error);
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`Tools error: ${message}`,level:'err'}]);
    }
  }, []);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      void loadTools('/api/mcp/tools');
    }, 0);
    return () => window.clearTimeout(timeout);
  }, [loadTools]);

  async function callTool() {
    if (!selected) return;
    setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`→ ${selected.name}`,meta:args,level:'info'}]);
    try {
      const res = await jsonFetch<unknown>(callUrl, { method:'POST', body: JSON.stringify({ name: selected.name, args }) });
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`✓ ${selected.name}`,meta:res,level:'ok'}]);
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : String(error);
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`✗ ${selected.name}: ${message}`,level:'err'}]);
    }
  }

  return (
    <div className="space-y-14">
      {/* BACKGROUNDS */}
      <div className="bg-gradient-mesh pointer-events-none" />
      <div className="bg-noise" />

      {/* HERO */}
      <section className="section-grid items-center gap-10">
        <div className="space-y-4">
          <h1 className="tracking-tight">
            Connect and <span className="text-[hsl(var(--accent))]">control</span> your hardware devices.
          </h1>
          <p className="text-muted max-w-[54ch] text-lg leading-relaxed">
            Conductor turns visual pin mappings and natural-language requests into
            hardware actions, Arduino firmware, and Raspberry Pi GPIO scaffolds.
          </p>
          <div className="flex gap-2">
            <a className="btn btn-primary" href="#setup"><Bolt className="w-4 h-4 mr-2"/>Get Started</a>
            <a className="btn btn-ghost" href="#discover">View Tools</a>
          </div>
        </div>

        <div>
          <Scene3D />
        </div>
      </section>


      {/* SETUP / MAPPER */}
      <section id="setup" className="section-grid">
        <HardwareMapper
          key={mapperRevision}
          onSaved={(mappings) => {
            setSavedMappings(mappings);
            void loadTools(toolsUrl);
          }}
          initialMappings={savedMappings}
        />
        <div className="card shine">
          <h3 className="text-lg font-semibold mb-3">What this does</h3>
          <p className="text-muted text-sm leading-relaxed">
            Choose your board, pick a part type, then click the GPIO header to select pins.
            Assign a capability and save it to the shared registry. The MCP server uses those mappings to expose
            matching tools and resources, while the generator produces board-specific starter firmware.
          </p>
          <ul className="text-muted text-sm mt-3 list-disc pl-5 space-y-1">
            <li><b className="text-accent-purple">Piezo buzzer</b> mappings expose a beep tool.</li>
            <li><b className="text-accent-emerald">SG90 servo</b> mappings expose position control.</li>
            <li><b className="text-accent">Sharp IR sensor</b> mappings expose a distance resource.</li>
          </ul>
        </div>
      </section>
      <section className="section-grid">
        <CommandChat tools={tools} mappings={savedMappings}/>
        <div className="card shine">
          <h3 className="text-lg font-semibold mb-2">Tips</h3>
          <ul className="text-sm text-muted list-disc pl-5 space-y-1">
            <li>Map a piezo buzzer, then ask &ldquo;beep for 500 milliseconds.&rdquo;</li>
            <li>Map an SG90 servo, then ask &ldquo;set the servo to 90 degrees.&rdquo;</li>
            <li>MCP clients can read the mapped Sharp IR distance resource.</li>
          </ul>
        </div>
      </section>


      {/* DISCOVER + CALL */}
      <section id="discover" className="section-grid">
        <div className="card shine">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold flex items-center gap-2"><Webhook className="w-5 h-5"/> Available Tools</h3>
            <Badge ok={toolsOk} label={toolsOk ? 'Registry online' : 'Unavailable'} />
          </div>
          <div className="flex gap-2 mb-3">
            <input className="input" value={toolsUrl} onChange={(e)=>setToolsUrl(e.target.value)} placeholder="/api/mcp/tools"/>
            <button className="btn btn-ghost" onClick={() => void loadTools(toolsUrl)}>
              Load tools
            </button>
            <button
              className="btn btn-ghost"
              onClick={async () => {
                const r = await fetch('/api/registry/mappings', { cache: 'no-store' });
                const data = await r.json();
                setSavedMappings(data.mappings || []);
                setMapperRevision(revision => revision + 1);
                void loadTools(toolsUrl);
              }}
            >
              Reload mappings
            </button>
          </div>
          <div className="space-y-2 max-h-72 overflow-auto">
            {tools.map(t=> (
              <button
                key={t.name}
                onClick={()=>{setSelected(t); setArgs({});}}
                className={`w-full text-left card p-3 bg-surface-subtle hover:bg-surface-hover transition ${selected?.name===t.name?'ring-1 ring-accent':''}`}
              >
                <div className="font-mono text-sm font-semibold">{t.name}</div>
                {t.description && <div className="text-muted text-sm mt-1">{t.description}</div>}
              </button>
            ))}
            {!tools.length && <div className="text-muted-foreground text-sm">No control tools are configured. Save a Leonardo piezo or servo mapping to expose one.</div>}
          </div>
        </div>

        <div className="card shine">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold flex items-center gap-2"><Cable className="w-5 h-5"/> Call a Tool</h3>
            <span className="badge">Schema-driven</span>
          </div>
          {!selected ? (
            <div className="text-muted-foreground text-sm">Select a tool.</div>
          ) : (
            <>
              {selected.input_schema ? (
                <SchemaForm schema={selected.input_schema} value={args} onChange={setArgs}/>
              ) : (
                <div className="text-muted-foreground text-sm">This tool has no schema; pass args in your client.</div>
              )}
              <div className="mt-4 flex justify-end">
                <button className="btn btn-primary" onClick={callTool}>Run Tool</button>
              </div>
            </>
          )}
        </div>
      </section>

      {/* TOOL EVENTS */}
      <section id="events" className="mb-8">
        <div className="card shine">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Radio className="w-5 h-5"/> Tool Call Log</h3>
          <div ref={logRef} className="scrollbox">
            {!log.length && <div className="text-muted-foreground text-sm">No calls yet. Select and run an available MCP tool to see its result here.</div>}
            <ul className="space-y-2">
              {log.map(row => (
                <li key={row.id} className="text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-muted-foreground">{row.t}</span>
                    <span className={`badge ${
                      row.level==='ok'
                        ?'border-status-success/30 bg-status-success/10 text-status-success'
                        : row.level==='err'
                        ?'border-status-error/30 bg-status-error/10 text-status-error'
                        :'border-status-info/30 bg-status-info/10 text-status-info'
                    }`}>{row.level}</span>
                  </div>
                  <div className="font-mono mt-1">{row.text}</div>
                  {row.meta !== undefined && row.meta !== null && (
                    <div className="text-xs text-muted break-all">{JSON.stringify(row.meta)}</div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}
