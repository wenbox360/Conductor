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
  type Msg = { who: 'user' | 'bot'; text: string; loading?: boolean };
  const [msgs, setMsgs] = useState<Msg[]>([
    { who: 'bot', text: 'Hi! I\'m your AI hardware assistant powered by Claude. Ask me anything about your connected devices - temperature, humidity, controlling relays, or any other hardware operations!' }
  ]);
  const [text, setText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const boxRef = useRef<HTMLDivElement | null>(null);
  const scroll = () => { if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight; };

  function say(who: Msg['who'], t: string, loading = false) {
    setMsgs(m => [...m, { who, text: t, loading }]);
    queueMicrotask(scroll);
  }

  function updateLastMessage(t: string, loading = false) {
    setMsgs(m => {
      const newMsgs = [...m];
      if (newMsgs.length > 0) {
        newMsgs[newMsgs.length - 1] = { ...newMsgs[newMsgs.length - 1], text: t, loading };
      }
      return newMsgs;
    });
    queueMicrotask(scroll);
  }

  async function handleSend(e?: React.FormEvent) {
    e?.preventDefault();
    const q = text.trim();
    if (!q || isLoading) return;
    
    say('user', q);
    setText('');
    setIsLoading(true);
    
    // Add a loading message
    say('bot', 'Thinking...', true);

    try {
      // Create context about available hardware for the agent
      const hardwareContext = mappings.length > 0 
        ? `\n\nAvailable hardware mappings:\n${mappings.map(m => 
            `- ${m.role}${m.label ? ` (${m.label})` : ''}: pins ${m.pins.join(', ')}`
          ).join('\n')}`
        : '\n\nNo hardware mappings configured yet.';

      const availableTools = tools.length > 0
        ? `\n\nAvailable MCP tools:\n${tools.map(t => 
            `- ${t.name}: ${t.description || 'No description'}`
          ).join('\n')}`
        : '\n\nNo MCP tools available.';

      const contextualQuery = `${q}${hardwareContext}${availableTools}`;

      // Call the Anthropic agent
      const response = await jsonFetch<{ reply: string }>('/api/mcp/call/agent/chat', {
        method: 'POST',
        body: JSON.stringify({ 
          text: contextualQuery,
          session_id: 'hardware_chat'
        })
      });

      updateLastMessage(response.reply || 'I received your message but couldn\'t generate a response.');

    } catch (err: any) {
      console.error('Agent error:', err);
      updateLastMessage(`Sorry, I encountered an error: ${err.message || 'Unknown error'}. Please try again.`);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="card shine flex flex-col gap-3">
      <h3 className="text-lg font-semibold">Chat to Hardware</h3>
      <div ref={boxRef} className="scrollbox" style={{height: 220}}>
        <ul className="space-y-2">
          {msgs.map((m, i) => (
            <li key={i} className={`text-sm ${m.who==='user' ? 'text-right' : ''}`}>
              <span className={`inline-block px-3 py-2 rounded-xl ${m.who==='user' ? 'bg-white/10' : 'bg-white/5'} ${m.loading ? 'animate-pulse' : ''}`}>
                {m.text}
              </span>
            </li>
          ))}
        </ul>
      </div>
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          className="input"
          placeholder="Ask me anything about your hardware..."
          value={text}
          onChange={e=>setText(e.target.value)}
          disabled={isLoading}
        />
        <button 
          className="btn btn-primary" 
          type="submit" 
          disabled={isLoading || !text.trim()}
        >
          <Send className="w-4 h-4 mr-2" />
          {isLoading ? 'Sending...' : 'Send'}
        </button>
      </form>
    </div>
  );
}
