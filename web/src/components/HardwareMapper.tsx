'use client';
import { useMemo, useRef, useState } from 'react';
import BoardMap from './BoardMap';
import { BOARDS, PARTS, type BoardDef, type PartDef } from '@/lib/boards';
import { Plug, Plus, Download } from 'lucide-react';
import type { Mapping } from '@/types/mapping';

export default function HardwareMapper({
  onSaved, initialMappings = []
}: {
  onSaved?: (mappings: Mapping[]) => void;
  initialMappings?: Mapping[];
}) {
  const [boardId, setBoardId] = useState<string>(BOARDS[0].id);
  const [partId, setPartId] = useState<string>(PARTS[0].id);
  const [role, setRole] = useState<string>(PARTS[0].roles[0]);
  const [label, setLabel] = useState<string>('');
  const [selectedPins, setSelectedPins] = useState<number[]>([]);
  const [mappings, setMappings] = useState<Mapping[]>(initialMappings);
  const persistedIds = useRef(new Set(initialMappings.map(mapping => mapping.id)));
  const [operation, setOperation] = useState<'save' | 'generate' | null>(null);
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
  const pinRequirement = minPins === maxPins
    ? `${minPins} pin${minPins === 1 ? '' : 's'}`
    : `${minPins}\u2013${maxPins} pins`;
  const boardMappings = useMemo(
    () => mappings.filter(mapping => mapping.boardId === boardId),
    [boardId, mappings]
  );

  // Pins already claimed by other mappings (to disable on the map)
  // Convert actual pins back to board positions for UI display
  const usedPins = useMemo(() => {
    const actualPins = boardMappings.flatMap(mapping => mapping.pins);
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
  }, [board.pinMapping, boardMappings]);
  // Power, ground, and non-GPIO header positions are never selectable.
  const unavailablePins = useMemo(
    () => [
      ...(board.v5 ?? []),
      ...(board.v33 ?? []),
      ...(board.gnd ?? []),
      ...(board.reserved ?? []),
    ],
    [board]
  );
  const disabledPins = useMemo(
    () => Array.from(new Set([...unavailablePins, ...usedPins])),
    [unavailablePins, usedPins]
  );

  function togglePin(n: number) {
    if (disabledPins.includes(n)) return;
    setSelectedPins(previous => {
      if (previous.includes(n)) {
        return previous.filter(pin => pin !== n);
      }
      if (previous.length >= maxPins) {
        return previous;
      }
      return [...previous, n];
    });
    setMsg('');
  }

  function clearSelection(){
    setSelectedPins([]);
    setMsg('');
  }

  function addMapping(){
    if (selectedPins.length < minPins || selectedPins.length > maxPins) {
      const expected = minPins === maxPins
        ? `exactly ${minPins}`
        : `${minPins} to ${maxPins}`;
      setMsg(`Select ${expected} pin${maxPins === 1 ? '' : 's'} for ${part.name}.`);
      return;
    }
    if (boardMappings.some(mapping => mapping.partId === partId)) {
      setMsg(`${part.name} is already mapped on ${board.name}.`);
      return;
    }
    const actualPins = selectedPins.map(getActualPin);
    
    // Check if the actual pin is already used
    const usedActualPins = boardMappings.flatMap(mapping => mapping.pins);
    const duplicatePin = actualPins.find(pin => usedActualPins.includes(pin));
    if (duplicatePin !== undefined) {
      setMsg(`Pin ${duplicatePin} is already used by another mapping.`);
      return;
    }
    
    const m: Mapping = {
      id: crypto.randomUUID(),
      boardId, partId, role,
      pins: actualPins,
      label: label || undefined
    };
    setMappings(prev=>[...prev, m]);
    setSelectedPins([]);
    setLabel('');
    setMsg('');
  }

async function saveAll(){
  setOperation('save');
  setMsg('');
  
  // Check if there are any mappings to save
  if (mappings.length === 0) {
    setMsg('No mappings to save. Add some hardware mappings first.');
    setOperation(null);
    return;
  }
  
  try {
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
    persistedIds.current = new Set(mappings.map(mapping => mapping.id));
    setMsg('Mappings saved.');
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    setMsg(`Save failed: ${message}`);
  } finally {
    setOperation(null);
  }
}

async function generateCode() {
  if (!boardMappings.length) {
    setMsg(`No mappings to generate for ${board.name}. Add a mapping for this board first.`);
    return;
  }
  
  setOperation('generate');
  setMsg('Generating code...');
  
  try {
    const resp = await fetch('/api/generate-code', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ 
        mappings: boardMappings,
        boardId 
      }),
    });
    
    if (!resp.ok) {
      const err = await resp.text().catch(() => '');
      throw new Error(`Code generation failed (${resp.status}) ${err}`);
    }
    
    const data: {
      code?: string;
      fileExtension?: string;
      mappingCount?: number;
    } = await resp.json();
    
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
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    setMsg(`Code generation failed: ${message}`);
  } finally {
    setOperation(null);
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
          <select
            className="input"
            value={boardId}
            onChange={e => {
              setBoardId(e.target.value);
              setSelectedPins([]);
              setMsg('');
            }}
          >
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

      {/* Pin requirement helper text */}
      <div className="flex items-center justify-between text-xs opacity-80">
        <div>
          Required: <b>{pinRequirement}</b> • Selected: <b>{selectedPins.length}</b> / {maxPins}
          {part.pinLabels?.length ? <> • Order: <b>{part.pinLabels.join(' → ')}</b></> : null}
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
                        const deletedIndex = mappings.findIndex(mapping => mapping.id === m.id);
                        const remainingMappings = mappings.filter(mapping => mapping.id !== m.id);
                        // optimistic UI
                        setMappings(remainingMappings);
                        if (!persistedIds.current.has(m.id)) {
                          setMsg('Unsaved mapping removed.');
                          return;
                        }
                        try {
                          const r = await fetch(`/api/registry/mappings?id=${encodeURIComponent(m.id)}`, { method: 'DELETE' });
                          if (!r.ok) throw new Error(`${r.status}`);
                          persistedIds.current.delete(m.id);
                          onSaved?.(remainingMappings);
                          setMsg('Mapping deleted.');
                        } catch (error: unknown) {
                          setMappings(current => {
                            if (current.some(mapping => mapping.id === m.id)) return current;
                            const restored = [...current];
                            restored.splice(Math.min(deletedIndex, restored.length), 0, m);
                            return restored;
                          });
                          const message = error instanceof Error ? error.message : 'Unknown error';
                          setMsg(`Delete failed: ${message}`);
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
          disabled={operation !== null || boardMappings.length === 0}
          onClick={generateCode}
        >
          <Download className="w-4 h-4 mr-2" />
          {operation === 'generate' ? 'Generating…' : 'Generate Code'}
        </button>
        <button 
          className="btn btn-primary" 
          disabled={operation !== null || mappings.length === 0}
          onClick={saveAll}
        >
          {operation === 'save' ? 'Saving…' : 'Save mappings'}
        </button>
      </div>
    </div>
  );
}
