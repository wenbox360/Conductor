'use client';
import { useRef, useState } from 'react';
import type { Tool } from '@/lib/api';
import { jsonFetch } from '@/lib/api';
import { Send } from 'lucide-react';
import type { Mapping } from '@/types/mapping';

export default function CommandChat({
  tools,
  callUrl,
  mappings
}: {
  tools: Tool[];
  callUrl: string;
  mappings: Mapping[];
}) {
  type Msg = { who: 'user' | 'bot'; text: string };
  const [msgs, setMsgs] = useState<Msg[]>([
    { who: 'bot', text: 'Hi! Ask me things like “what’s the temperature?” or “turn the relay on”.' }
  ]);
  const [text, setText] = useState('');
  const boxRef = useRef<HTMLDivElement | null>(null);
  const scroll = () => { if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight; };

  function say(who: Msg['who'], t: string) {
    setMsgs(m => [...m, { who, text: t }]);
    queueMicrotask(scroll);
  }

  function findTool(re: RegExp): Tool | undefined {
    return tools.find(t => re.test(t.name));
  }

  async function handleSend(e?: React.FormEvent) {
    e?.preventDefault();
    const q = text.trim();
    if (!q) return;
    say('user', q);
    setText('');

    try {
      // --- Intent 1: Temperature ---
      if (/(temp|temperature)\b/i.test(q)) {
        const m = mappings.find(x => /temperature/i.test(x.role));
        if (!m) { say('bot', 'I couldn’t find a saved mapping with role “Temperature”. Add one in Hardware Setup.'); return; }

        // Prefer a tool that looks like it can read DHT / temperature
        const tool =
          findTool(/read.*temp|temperature|dht/i) ||
          findTool(/sensor.*read/i);

        if (!tool) {
          say('bot', 'No temperature-reading tool discovered. Expose one in your MCP bridge (e.g., `read_temperature`).');
          return;
        }

        // Common arg names handled; adapt as needed
        const args: Record<string, any> = {};
        // try typical schema fields if present
        const props = tool.input_schema?.properties || {};
        if ('pin' in props) args.pin = m.pins[0];
        else if ('gpio' in props) args.gpio = m.pins[0];
        else if ('pins' in props) args.pins = m.pins;
        else args.pin = m.pins[0];

        const res = await jsonFetch<any>(callUrl, { method: 'POST', body: JSON.stringify({ name: tool.name, args }) });
        const value = res?.temperature ?? res?.temp_c ?? res?.value ?? res?.result ?? JSON.stringify(res);
        say('bot', `Temperature${m.label ? ` (${m.label})` : ''}: ${value}`);
        return;
      }

      // --- Intent 2: Humidity ---
      if (/\b(humidity|humid)\b/i.test(q)) {
        const m = mappings.find(x => /humidity/i.test(x.role));
        if (!m) { say('bot', 'No mapping with role “Humidity”. Add one in Hardware Setup.'); return; }
        const tool = findTool(/read.*humidity|dht/i) || findTool(/sensor.*read/i);
        if (!tool) { say('bot', 'No humidity-reading tool found (try exposing `read_humidity`).'); return; }

        const props = tool.input_schema?.properties || {};
        const args: Record<string, any> =
          'pin' in props ? { pin: m.pins[0] } :
          'gpio' in props ? { gpio: m.pins[0] } :
          'pins' in props ? { pins: m.pins } :
          { pin: m.pins[0] };

        const res = await jsonFetch<any>(callUrl, { method: 'POST', body: JSON.stringify({ name: tool.name, args }) });
        const value = res?.humidity ?? res?.value ?? res?.result ?? JSON.stringify(res);
        say('bot', `Humidity${m.label ? ` (${m.label})` : ''}: ${value}`);
        return;
      }

      // --- Intent 3: Relay / Switch on/off ---
      if (/\b(relay|switch)\b/i.test(q) && /\b(on|off)\b/i.test(q)) {
        const turnOn = /\bon\b/i.test(q);
        const m = mappings.find(x => /switch/i.test(x.role));
        if (!m) { say('bot', 'No mapping with role “Switch”. Map your relay first.'); return; }
        const tool = findTool(/relay|switch|gpio.*write|digital.*write/i);
        if (!tool) { say('bot', 'No relay control tool found (expose one like `relay_set` or `gpio_write`).'); return; }

        const props = tool.input_schema?.properties || {};
        const args: Record<string, any> = {
          ...( 'pin'  in props ? { pin: m.pins[0] } :
              'gpio' in props ? { gpio: m.pins[0] } :
              'pins' in props ? { pins: m.pins } : { pin: m.pins[0] })
        };

        // Value field name heuristics
        if ('state' in props) args.state = turnOn ? 'on' : 'off';
        else if ('value' in props) args.value = turnOn ? 1 : 0;
        else if ('level' in props) args.level = turnOn ? 1 : 0;
        else args.value = turnOn ? 1 : 0;

        await jsonFetch<any>(callUrl, { method: 'POST', body: JSON.stringify({ name: tool.name, args }) });
        say('bot', `Relay ${turnOn ? 'ON' : 'OFF'} on pin ${m.pins[0]}${m.label ? ` (${m.label})` : ''}.`);
        return;
      }

      // Fallback
      say('bot', 'I didn’t recognize that. Try: “what’s the temperature?”, “humidity?”, or “turn the relay on/off”.');

    } catch (err: any) {
      say('bot', `Error: ${err.message || String(err)}`);
    }
  }

  return (
    <div className="card shine flex flex-col gap-3">
      <h3 className="text-lg font-semibold">Chat to Hardware</h3>
      <div ref={boxRef} className="scrollbox" style={{height: 220}}>
        <ul className="space-y-2">
          {msgs.map((m, i) => (
            <li key={i} className={`text-sm ${m.who==='user' ? 'text-right' : ''}`}>
              <span className={`inline-block px-3 py-2 rounded-xl ${m.who==='user' ? 'bg-white/10' : 'bg-white/5'}`}>
                {m.text}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          className="input"
          placeholder="Ask for temperature, humidity, or relay on/off…"
          value={text}
          onChange={e=>setText(e.target.value)}
        />
        <button className="btn btn-primary" type="submit"><Send className="w-4 h-4 mr-2" />Send</button>
      </form>
    </div>
  );
}
