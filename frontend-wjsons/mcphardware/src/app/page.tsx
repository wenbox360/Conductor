// File: mcphardware/src/app/page.tsx
'use client';

import { useEffect, useRef, useState } from 'react';
import type { Tool } from '@/lib/api';
import { jsonFetch } from '@/lib/api';
import { Bolt, Radio, Cable, Webhook, Lightbulb } from 'lucide-react';
import dynamic from 'next/dynamic';
import { motion } from 'framer-motion';
import HardwareMapper from '@/components/HardwareMapper';
import CommandChat from '@/components/CommandChat';


const Scene3D = dynamic(() => import('@/components/Scene3D'), { ssr: false });

function Badge({ ok, label }: { ok: boolean; label?: string }) {
  return <span className={`badge ${ok ? 'border-cyan-700 bg-cyan-600/30' : ''}`}>{label ?? (ok? 'OK':'—')}</span>;
}

function SchemaForm({ schema, value, onChange }: { schema: any; value: any; onChange: (v:any)=>void }) {
  const props = schema?.properties || {};
  const required: string[] = schema?.required || [];
  return (
    <div className="grid md:grid-cols-2 gap-3">
      {Object.entries(props).map(([k, spec]: any) => {
        const isReq = required.includes(k);
        const title = spec.title || k;
        const type = spec.type;
        const enums = spec.enum as any[] | undefined;
        const val = value?.[k] ?? spec.default ?? (type==='number'?0:type==='boolean'?false:'');
        const set = (v:any)=>onChange({ ...(value||{}), [k]: v });
        return (
          <div key={k}>
            <label className="block mb-1 text-sm opacity-80">{title}{isReq && <span className="text-rose-400"> *</span>}</label>
            {enums?.length ? (
              <select className="input" value={val} onChange={(e)=>set(e.target.value)}>
                {enums.map((o)=> <option key={String(o)} value={o}>{String(o)}</option>)}
              </select>
            ) : type==='boolean' ? (
              <input type="checkbox" checked={!!val} onChange={(e)=>set(e.target.checked)} />
            ) : type==='number' || type==='integer' ? (
              <input className="input" type="number" value={val} onChange={(e)=>set(Number(e.target.value))} />
            ) : (
              <input className="input" value={val} onChange={(e)=>set(e.target.value)} />
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function Page() {
  const [toolsUrl, setToolsUrl] = useState('/api/mcp/tools');
  const [callUrl, setCallUrl] = useState('/api/mcp/call');
  const [piBase, setPiBase] = useState<string>(process.env.NEXT_PUBLIC_PI_FASTAPI_BASE || 'http://raspberrypi.local:8000');

  const [tools, setTools] = useState<Tool[]>([]);
  const [toolsOk, setToolsOk] = useState(false);
  const [loading, setLoading] = useState(false);

  const [selected, setSelected] = useState<Tool | null>(null);
  const [args, setArgs] = useState<Record<string, any>>({});

  const [period, setPeriod] = useState(0.5);
  const [cycles, setCycles] = useState(8);

  // near other state
  const [savedMappings, setSavedMappings] = useState<any[]>([]);

  const [log, setLog] = useState<{ id:string; t:string; text:string; meta?:any; level:'ok'|'err'|'info' }[]>([]);
  const logRef = useRef<HTMLDivElement | null>(null);
  useEffect(()=>{ if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight; }, [log]);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch('/api/registry/mappings', { cache: 'no-store' });
        if (r.ok) {
          const data = await r.json();
          setSavedMappings(data.mappings || []);
        }
      } catch {}
    })();
  }, []);

  async function loadTools() {
    setLoading(true);
    try {
      const data = await jsonFetch<any>(toolsUrl);
      const list: Tool[] = Array.isArray(data) ? data : data.tools || [];
      setTools(list);
      setToolsOk(list.length>0);
      if (list[0]) {
        setSelected(list[0]);
        const seed: Record<string, any> = {};
        const props = list[0].input_schema?.properties || {};
        for (const [k, v] of Object.entries<any>(props)) if (v.default !== undefined) seed[k] = v.default;
        setArgs(seed);
      }
    } catch (e:any) {
      setToolsOk(false);
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`Tools error: ${e.message}`,level:'err'}]);
    } finally { setLoading(false); }
  }

  useEffect(()=>{ loadTools(); }, []);

  async function callTool() {
    if (!selected) return;
    setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`→ ${selected.name}`,meta:args,level:'info'}]);
    try {
      const res = await jsonFetch<any>(callUrl, { method:'POST', body: JSON.stringify({ name: selected.name, args }) });
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`✓ ${selected.name}`,meta:res,level:'ok'}]);
    } catch (e:any) {
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`✗ ${selected.name}: ${e.message}`,level:'err'}]);
    }
  }

  async function restLed(action:'on'|'off'|'blink') {
    if (!piBase) { setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`Set Pi base to use REST fallback`,level:'err'}]); return; }
    const payload:any = { action };
    if (action==='blink') { payload.period = period; payload.cycles = cycles; }
    try {
      const r = await jsonFetch<any>(`${piBase.replace(/\/$/,'')}/led`, { method:'POST', body: JSON.stringify(payload) });
      if (!r?.ok) throw new Error(r?.error || 'unknown');
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`✓ REST /led ${action}`,meta:r,level:'ok'}]);
    } catch (e:any) {
      setLog(l=>[...l,{id:crypto.randomUUID(),t:new Date().toLocaleTimeString(),text:`✗ REST /led: ${e.message}`,level:'err'}]);
    }
  }

  return (
    <div className="space-y-14">
      {/* BACKGROUNDS */}
      <div className="bg-gradient-mesh pointer-events-none" />
      <div className="bg-noise" />

      {/* HERO */}
      <section className="section-grid items-center gap-10">
        <motion.div
          initial={{opacity:0, y:8}} animate={{opacity:1, y:0}} transition={{duration:.6, ease:'easeOut'}}
          className="space-y-4"
        >
          <h1 className="tracking-tight">
            Let AI <span className="text-[hsl(var(--accent))]">discover</span> and use your tools.
          </h1>
          <p className="opacity-80 max-w-[54ch]">
            MCP standardizes capability discovery, safe execution, and streaming for AI agents.
            Point this dashboard at your FastMCP bridge and control real hardware in minutes.
          </p>
          <div className="flex gap-2">
            <a className="btn btn-primary" href="#discover"><Bolt className="w-4 h-4 mr-2"/>Get Started</a>
            <a className="btn btn-ghost" href="#control">Try Controls</a>
          </div>
        </motion.div>

        <motion.div initial={{opacity:0, scale:.98}} animate={{opacity:1, scale:1}} transition={{duration:.7, ease:'easeOut'}}>
          <Scene3D />
        </motion.div>
      </section>


      {/* SETUP / MAPPER */}
      <section id="setup" className="section-grid">
        <HardwareMapper tools={tools} callUrl={callUrl} onSaved={setSavedMappings} initialMappings={savedMappings}/>
        <div className="card shine">
          <h3 className="text-lg font-semibold mb-3">What this does</h3>
          <p className="opacity-80 text-sm">
            Choose your board, pick a part type, then click the GPIO header to select pins.
            Assign a role (e.g., <b>Temperature</b>) and save. If your FastMCP server exposes a
            <code className="font-mono">register_mapping</code> tool, the mappings will be sent automatically
            so the LLM can call the right tool with the right pins—no if/else spaghetti.
          </p>
          <ul className="opacity-80 text-sm mt-3 list-disc pl-5 space-y-1">
            <li><b>DHT22</b> uses one data pin (power/ground assumed from wiring).</li>
            <li><b>HC-SR04</b> uses two pins (Trigger/Echo).</li>
            <li>Add more boards/components later without code changes.</li>
          </ul>
        </div>
      </section>
      <section className="section-grid">
        <CommandChat tools={tools} callUrl={callUrl} mappings={savedMappings as any}/>
        <div className="card shine">
          <h3 className="text-lg font-semibold mb-2">Tips</h3>
          <ul className="text-sm opacity-80 list-disc pl-5 space-y-1">
            <li>Map a DHT22 to a pin with role <b>Temperature</b> (and optionally <b>Humidity</b>), then ask for readings.</li>
            <li>Map your relay as role <b>Switch</b>, then say “turn the relay on”.</li>
          </ul>
        </div>
      </section>


      {/* DISCOVER + CALL */}
      <section id="discover" className="section-grid">
        <motion.div initial={{opacity:0, y:10}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{duration:.5}} className="card shine">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold flex items-center gap-2"><Webhook className="w-5 h-5"/> Discovered Tools</h3>
            <Badge ok={toolsOk} label={toolsOk? 'Tools OK':'No tools'} />
          </div>
          <div className="flex gap-2 mb-3">
            <input className="input" value={toolsUrl} onChange={(e)=>setToolsUrl(e.target.value)} placeholder="/api/mcp/tools"/>
            <button
              className="btn btn-ghost"
              onClick={async () => {
                const r = await fetch('/api/registry/mappings', { cache: 'no-store' });
                const data = await r.json();
                setSavedMappings(data.mappings || []);
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
                className={`w-full text-left card p-3 bg-white/5 hover:bg-white/[.08] transition ${selected?.name===t.name?'ring-1 ring-cyan-600':''}`}
              >
                <div className="font-mono text-sm font-semibold">{t.name}</div>
                {t.description && <div className="opacity-80 text-sm mt-1">{t.description}</div>}
              </button>
            ))}
            {!tools.length && <div className="opacity-70 text-sm">Start your MCP bridge and expose /tools.</div>}
          </div>
        </motion.div>

        <motion.div initial={{opacity:0, y:10}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{duration:.5, delay:.1}} className="card shine">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-semibold flex items-center gap-2"><Cable className="w-5 h-5"/> Call a Tool</h3>
            <span className="badge">Schema-driven</span>
          </div>
          {!selected ? (
            <div className="opacity-70 text-sm">Select a tool.</div>
          ) : (
            <>
              {selected.input_schema ? (
                <SchemaForm schema={selected.input_schema} value={args} onChange={setArgs}/>
              ) : (
                <div className="opacity-70 text-sm">This tool has no schema; pass args in your client.</div>
              )}
              <div className="mt-4 flex justify-end">
                <button className="btn btn-primary" onClick={callTool}>Run Tool</button>
              </div>
            </>
          )}
        </motion.div>
      </section>

      {/* CONTROL + EVENTS */}
      <section id="control" className="section-grid">
        <motion.div initial={{opacity:0, y:10}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{duration:.5}} className="card shine">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Lightbulb className="w-5 h-5"/> LED Controls (REST)</h3>
          <div className="grid grid-cols-3 gap-2 mb-4">
            <button className="btn btn-primary" onClick={()=>restLed('on')}>On</button>
            <button className="btn btn-ghost" onClick={()=>restLed('off')}>Off</button>
            <button className="btn btn-ghost" onClick={()=>restLed('blink')}>Blink</button>
          </div>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block mb-1 text-sm opacity-80">Blink period (s)</label>
              <input className="input" type="number" step="0.05" min={0.05} max={2} value={period} onChange={(e)=>setPeriod(Number(e.target.value))}/>
            </div>
            <div>
              <label className="block mb-1 text-sm opacity-80">Blink cycles</label>
              <input className="input" type="number" min={1} max={40} value={cycles} onChange={(e)=>setCycles(Number(e.target.value))}/>
            </div>
          </div>
          <label className="block mb-1 text-sm opacity-80">FastAPI base</label>
          <input className="input" value={piBase} onChange={(e)=>setPiBase(e.target.value)} placeholder="http://raspberrypi.local:8000"/>
        </motion.div>

        <motion.div id="events" initial={{opacity:0, y:10}} whileInView={{opacity:1, y:0}} viewport={{once:true}} transition={{duration:.5, delay:.1}} className="card shine">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2"><Radio className="w-5 h-5"/> Stream & Logs</h3>
          <div ref={logRef} className="scrollbox">
            {!log.length && <div className="opacity-70 text-sm">No events yet. Call a tool or use LED controls.</div>}
            <ul className="space-y-2">
              {log.map(row => (
                <li key={row.id} className="text-sm">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs opacity-70">{row.t}</span>
                    <span className={`badge ${row.level==='ok'?'border-emerald-700 bg-emerald-600/30': row.level==='err'?'border-rose-700 bg-rose-600/30':''}`}>{row.level}</span>
                  </div>
                  <div className="font-mono mt-1">{row.text}</div>
                  {row.meta && <div className="text-xs opacity-80 break-all">{JSON.stringify(row.meta)}</div>}
                </li>
              ))}
            </ul>
          </div>
        </motion.div>
      </section>
    </div>
  );
}
