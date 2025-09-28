// File: mcphardware/src/components/HardwareMapper.tsx
'use client';
import { useMemo, useState } from 'react';
import BoardMap from './BoardMap';
import { BOARDS, PARTS, type BoardDef, type PartDef } from '@/lib/boards';
import type { Tool } from '@/lib/api';
import { jsonFetch } from '@/lib/api';
import { Plug, Plus, Save, Download } from 'lucide-react';
import type { Mapping } from '@/types/mapping';

export default function HardwareMapper({
  tools, callUrl,
  onSaved, initialMappings = []

}: {
  tools: Tool[];
  callUrl: string;
  onSaved?: (mappings: Mapping[]) => void;
  initialMappings?: Mapping[];
}) {
  const [boardId, setBoardId] = useState<string>(BOARDS[0].id);
  const [partId, setPartId] = useState<string>(PARTS[0].id);
  const [role, setRole] = useState<string>(PARTS[0].roles[0]);
  const [label, setLabel] = useState<string>('');
  const [selectedPins, setSelectedPins] = useState<number[]>([]);
  const [mappings, setMappings] = useState<Mapping[]>(initialMappings);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string>('');

  const board: BoardDef = useMemo(()=> BOARDS.find(b=>b.id===boardId)!, [boardId]);
  const part: PartDef = useMemo(()=> PARTS.find(p=>p.id===partId)!, [partId]);

  // Convert board position to actual pin number/name
  function getActualPin(boardPosition: number): number | string {
    if (board.pinMapping) {
      const mapped = board.pinMapping[boardPosition];
      // Return the mapped value (could be number like 13 or string like 'A0')
      return mapped !== undefined ? mapped : boardPosition;
    }
    return boardPosition;
  }

  // Support both legacy pinCount and new minPins/maxPins
  const minPins: number = part.minPins ?? part.pinCount ?? 1;
  const maxPins: number = part.maxPins ?? part.pinCount ?? 1;

  // Pins already claimed by other mappings (to disable on the map)
  // Convert actual pins back to board positions for UI display
  const usedPins = useMemo(() => {
    const actualPins = mappings.flatMap(m => m.pins);
    const boardPositions: number[] = [];
    
    // For each actual pin, find its board position
    if (board.pinMapping) {
      Object.entries(board.pinMapping).forEach(([boardPos, actualPin]) => {
        // Check if this actual pin (number or string) is in use
        if (actualPins.includes(actualPin)) {
          boardPositions.push(parseInt(boardPos));
        }
      });
    } else {
      // If no mapping, actual pins are the same as board positions
      boardPositions.push(...(actualPins as number[]));
    }
    
    return boardPositions;
  }, [mappings, board.pinMapping]);
  // Power & ground (always disabled for selection)
  const powerAndGnd = useMemo(
    () => [ ...(board.v5 ?? []), ...(board.v33 ?? []), ...(board.gnd ?? []) ],
    [board]
  );
  const disabledPins = useMemo(
    () => Array.from(new Set([...powerAndGnd, ...usedPins])),
    [powerAndGnd, usedPins]
  );

  function togglePin(n:number){
    if (disabledPins.includes(n)) return;
    setSelectedPins(prev => (prev[0] === n ? [] : [n])); // one or none
    setMsg('');
  }

  function clearSelection(){
    setSelectedPins([]);
    setMsg('');
  }

  function addMapping(){
    if (selectedPins.length !== 1) {
      setMsg(`Select exactly 1 pin for ${part.name}.`);
      return;
    }
    const boardPosition = selectedPins[0];
    const actualPin = getActualPin(boardPosition);
    
    // Check if the actual pin is already used
    const usedActualPins = mappings.flatMap(m => m.pins);
    if (usedActualPins.includes(actualPin)) {
      setMsg(`Pin ${actualPin} is already used by another mapping.`);
      return;
    }
    
    const m: Mapping = {
      id: crypto.randomUUID(),
      boardId, partId, role,
      pins: [actualPin],                // Store the actual pin number, not board position
      label: label || undefined
    };
    setMappings(prev=>[...prev, m]);
    setSelectedPins([]);
    setLabel('');
    setMsg('');
  }

async function saveAll(){
  setBusy(true); setMsg('');
  
  // Check if there are any mappings to save
  if (mappings.length === 0) {
    setMsg('No mappings to save. Add some hardware mappings first.');
    setBusy(false);
    return;
  }
  
  try {
    const reg = tools.find(t => /register[_-]?mapping/i.test(t.name));
    if (reg) {
      await jsonFetch(callUrl, { method:'POST', body: JSON.stringify({ name: reg.name, args: { mappings } }) });
      setMsg('Mappings sent to MCP (register_mapping).');
    } else {
      setMsg('No register_mapping tool found — mappings kept locally.');
    }

    // Persist through Next proxy (no CORS / no client env leak)
    const resp = await fetch('/api/registry/mappings', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ mappings }),
    });
    if (!resp.ok) {
      const err = await resp.text().catch(()=> '');
      throw new Error(`Registry POST failed (${resp.status}) ${err}`);
    }

    onSaved?.(mappings);
  } catch (e:any) {
    setMsg(`Save failed: ${e.message}`);
  } finally {
    setBusy(false);
  }
}

async function generateCode() {
  if (!mappings.length) {
    setMsg('No mappings to generate code for. Add some hardware mappings first.');
    return;
  }
  
  setBusy(true);
  setMsg('Generating code...');
  
  try {
    const resp = await fetch('/api/generate-code', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ 
        mappings, 
        boardId 
      }),
    });
    
    if (!resp.ok) {
      const err = await resp.text().catch(() => '');
      throw new Error(`Code generation failed (${resp.status}) ${err}`);
    }
    
    const data = await resp.json();
    
    if (data.code) {
      // Create a downloadable file with appropriate extension
      const fileExtension = data.fileExtension || 'txt';
      const blob = new Blob([data.code], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${boardId}_generated_code.${fileExtension}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      const codeType = fileExtension === 'py' ? 'Python' : 'Arduino';
      setMsg(`${codeType} code generated and downloaded! (${data.mappingCount} mappings)`);
    } else {
      throw new Error('No code returned from server');
    }
  } catch (e: any) {
    setMsg(`Code generation failed: ${e.message}`);
  } finally {
    setBusy(false);
  }
}


  return (
    <div className="card shine space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold flex items-center gap-2"><Plug className="w-5 h-5"/> Hardware Setup</h3>
        <span className="badge">{mappings.length} mapped</span>
      </div>

      {/* Controls */}
      <div className="grid md:grid-cols-3 gap-3">
        <div>
          <label className="block mb-1 text-sm opacity-80">Board</label>
          <select className="input" value={boardId} onChange={e=>setBoardId(e.target.value)}>
            {BOARDS.map(b=> <option key={b.id} value={b.id}>{b.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block mb-1 text-sm opacity-80">Part / Hardware</label>
          <select
            className="input"
            value={partId}
            onChange={e=>{
              const id = e.target.value;
              setPartId(id);
              const p = PARTS.find(x=>x.id===id)!;
              setRole(p.roles[0]);
              setSelectedPins([]); // reset pin selection when part changes
              setMsg('');
            }}>
            {PARTS.map(p=> <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div>
          <label className="block mb-1 text-sm opacity-80">Role / Capability</label>
          <select className="input" value={role} onChange={e=>{ setRole(e.target.value); setMsg(''); }}>
            {part.roles.map(r=> <option key={r} value={r}>{r}</option>)}
          </select>
        </div>
      </div>

      {/* Board map */}
      <BoardMap
        board={board}
        selectedPins={selectedPins}
        onToggle={togglePin}
        disabledPins={disabledPins}
      />

      {/* Single-pin helper text */}
      <div className="flex items-center justify-between text-xs opacity-80">
        <div>
          Required: <b>1</b> pin • Selected: <b>{selectedPins.length}</b> / 1
        </div>
        {selectedPins.length > 0 && (
          <button className="btn btn-ghost px-3 py-1" onClick={clearSelection}>Clear</button>
        )}
      </div>

      {/* Label + Add */}
      <div className="grid md:grid-cols-[1fr_auto] gap-3">
        <div>
          <label className="block mb-1 text-sm opacity-80">Optional label (e.g., “Living Room Temp”)</label>
          <input className="input" value={label} onChange={e=>setLabel(e.target.value)} placeholder="Name this mapping" />
        </div>
        <div className="flex items-end">
          <button className="btn btn-ghost" onClick={addMapping}><Plus className="w-4 h-4 mr-2" />Add Mapping</button>
        </div>
      </div>

      {/* Table */}
      <div className="scrollbox">
        {!mappings.length ? (
          <div className="opacity-70 text-sm">No mappings yet.</div>
        ) : (
          <ul className="space-y-2">
            {mappings.map(m=>(
              <li key={m.id} className="text-sm card p-3 bg-white/5">
                <div className="flex items-center justify-between">
                  <div className="font-semibold">{PARTS.find(p=>p.id===m.partId)?.name} • {m.role}</div>
                  <div className="flex items-center gap-2">
                    <div className="badge">Pins: {m.pins.join(', ')}</div>
                    <button
                      className="btn btn-ghost"
                      onClick={async () => {
                        // optimistic UI
                        setMappings(prev => prev.filter(x => x.id !== m.id));
                        try {
                          const r = await fetch(`/api/registry/mappings?id=${encodeURIComponent(m.id)}`, { method: 'DELETE' });
                          if (!r.ok) throw new Error(`${r.status}`);
                          setMsg('Mapping deleted.');
                        } catch (e:any) {
                          setMsg(`Delete failed: ${e.message}`);
                        }
                      }}
                    >
                      Remove
                    </button>
                  </div>
                </div>
                {m.label && <div className="opacity-80 text-xs mt-1">{m.label}</div>}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Save & Generate */}
      <div className="flex items-center gap-3 justify-end">
        {msg && <span className="text-xs opacity-80">{msg}</span>}
        <button 
          className="btn btn-secondary" 
          disabled={busy || mappings.length === 0} 
          onClick={generateCode}
        >
          <Download className="w-4 h-4 mr-2" />
          {busy ? 'Generating…' : 'Generate Code'}
        </button>
        <button 
          className="btn btn-primary" 
          disabled={busy || mappings.length === 0} 
          onClick={saveAll}
        >
          {busy ? 'Saving…' : 'Save mappings'}
        </button>
      </div>
    </div>
  );
}
