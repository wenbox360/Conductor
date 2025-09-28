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
      const res = await jsonFetch<{ reply: string }>("/api/mcp/call/agent/chat", {
        method: "POST",
        body: JSON.stringify({ text: q }),
      });
      say('bot', res.reply);
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
