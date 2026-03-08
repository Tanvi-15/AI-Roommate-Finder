import { useState, useEffect, useRef } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cloneApi } from '@/lib/api';
import { Loader2, Send, Bot, User } from 'lucide-react';
import { motion } from 'framer-motion';

type ChatMessage = { role: 'user' | 'assistant'; content: string };

export default function MyClonePage() {
  const { user, hasQuestionnaire } = useAuth();
  const navigate = useNavigate();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [introLoaded, setIntroLoaded] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!hasQuestionnaire) {
      navigate('/questionnaire');
      return;
    }
    cloneApi
      .intro()
      .then(({ intro }) => {
        setMessages([{ role: 'assistant', content: intro }]);
      })
      .catch(() => {
        setMessages([
          {
            role: 'assistant',
            content: "Hey! I'm your AI clone. Ask me anything about your preferences to verify I represent you well.",
          },
        ]);
      })
      .finally(() => setIntroLoaded(true));
  }, [hasQuestionnaire, navigate]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || loading) return;
    setInput('');
    const userMsg: ChatMessage = { role: 'user', content: text };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const { reply } = await cloneApi.chat(text, history);
      setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message || 'Failed to get reply'}.` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  if (!hasQuestionnaire) return null;

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl space-y-4">
        <div>
          <h1 className="font-display text-2xl font-bold">Chat with Your Clone</h1>
          <p className="text-sm text-muted-foreground">
            Talk to your AI clone to verify it represents you before matching with others.
          </p>
        </div>

        <Card className="border-0 shadow-card">
          <CardHeader className="py-3">
            <CardTitle className="text-base font-medium flex items-center gap-2">
              <Bot size={18} className="text-primary" />
              {user?.name}&apos;s Clone
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="max-h-[50vh] overflow-y-auto space-y-3 p-1">
              {!introLoaded && (
                <div className="flex justify-center py-4">
                  <Loader2 size={24} className="animate-spin text-muted-foreground" />
                </div>
              )}
              {messages.map((msg, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`flex max-w-[85%] items-start gap-2 rounded-2xl px-4 py-2.5 text-sm ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground rounded-br-sm'
                        : 'bg-accent text-accent-foreground rounded-bl-sm'
                    }`}
                  >
                    {msg.role === 'assistant' && <Bot size={16} className="shrink-0 mt-0.5 opacity-70" />}
                    <p className="whitespace-pre-wrap">{msg.content}</p>
                    {msg.role === 'user' && <User size={16} className="shrink-0 mt-0.5 opacity-70" />}
                  </div>
                </motion.div>
              ))}
              {loading && (
                <div className="flex justify-start">
                  <div className="flex items-center gap-2 rounded-2xl bg-accent px-4 py-2.5 text-sm text-accent-foreground">
                    <Loader2 size={16} className="animate-spin" />
                    <span>Thinking…</span>
                  </div>
                </div>
              )}
              <div ref={endRef} />
            </div>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex gap-2"
            >
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask your clone something..."
                className="flex-1 rounded-lg border border-input bg-background px-4 py-2.5 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={loading}
              />
              <Button type="submit" size="icon" disabled={loading || !input.trim()} className="shrink-0">
                {loading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  );
}
