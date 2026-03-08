import { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { StatusBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useWebSocket, WsMessage } from '@/hooks/useWebSocket';
import { Play, Square, BarChart3, RotateCcw, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

type ChatMsg = { speaker: string; speaker_id: string; message: string; turn: number; phase: string };

export default function AgentChatPage() {
  const { roomId } = useParams<{ roomId: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const room = (location.state as any)?.room;
  const { connected, messages, connect, send, disconnect, clearMessages } = useWebSocket(roomId || null);
  const [chatMessages, setChatMessages] = useState<(ChatMsg | { type: 'phase'; label: string })[]>([]);
  const [outcome, setOutcome] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [started, setStarted] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { if (roomId && !connected) connect(); }, [roomId]);

  useEffect(() => {
    const last = messages[messages.length - 1];
    if (!last) return;
    switch (last.type) {
      case 'started':
        setStarted(true);
        break;
      case 'phase_start':
        setChatMessages(prev => [...prev, { type: 'phase', label: last.label }]);
        break;
      case 'agent_message':
        setChatMessages(prev => [...prev, last.data]);
        break;
      case 'chat_complete':
        setOutcome(last.outcome);
        setStarted(false);
        break;
      case 'analyzing':
        setAnalyzing(true);
        break;
      case 'analysis':
        setAnalysis(last);
        setAnalyzing(false);
        break;
      case 'stopped':
        setStarted(false);
        break;
    }
  }, [messages]);

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatMessages]);

  const handleReset = () => {
    disconnect();
    clearMessages();
    setChatMessages([]);
    setOutcome(null);
    setAnalysis(null);
    setStarted(false);
    navigate('/match/setup');
  };

  const analysisData = analysis?.result?.structured ? analysis.result.data : null;

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="font-display text-xl font-bold">
              {room?.agent_a || 'Agent A'} ↔ {room?.agent_b || 'Agent B'}
            </h1>
            <p className="text-sm text-muted-foreground">Room: {roomId}</p>
          </div>
          <div className="flex gap-2">
            {!started && !outcome && (
              <Button onClick={() => send({ action: 'start' })} disabled={!connected} className="gap-1">
                <Play size={14} /> Start Chat
              </Button>
            )}
            {started && (
              <Button variant="destructive" onClick={() => send({ action: 'stop' })} className="gap-1">
                <Square size={14} /> Stop
              </Button>
            )}
            {outcome && !analysis && (
              <Button onClick={() => send({ action: 'analyze' })} disabled={analyzing} className="gap-1">
                {analyzing ? <Loader2 size={14} className="animate-spin" /> : <BarChart3 size={14} />}
                Analyze
              </Button>
            )}
            <Button variant="outline" onClick={handleReset} className="gap-1">
              <RotateCcw size={14} /> Reset
            </Button>
          </div>
        </div>

        {/* Chat stream */}
        <Card className="border-0 shadow-card">
          <CardContent className="max-h-[50vh] overflow-y-auto p-4 space-y-3">
            {chatMessages.length === 0 && (
              <p className="text-center text-muted-foreground py-8">Start the chat to see the AI conversation</p>
            )}
            {chatMessages.map((msg, i) => {
              if ('type' in msg && msg.type === 'phase') {
                return (
                  <div key={i} className="flex items-center gap-2 py-2">
                    <div className="h-px flex-1 bg-border" />
                    <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">{msg.label}</span>
                    <div className="h-px flex-1 bg-border" />
                  </div>
                );
              }
              const m = msg as ChatMsg;
              const isA = m.speaker_id === 'a';
              return (
                <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                  className={`flex ${isA ? 'justify-start' : 'justify-end'}`}>
                  <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm ${
                    isA ? 'bg-accent text-accent-foreground rounded-bl-sm' : 'bg-primary text-primary-foreground rounded-br-sm'
                  }`}>
                    <p className="text-xs font-semibold mb-1 opacity-70">{m.speaker}</p>
                    <p>{m.message}</p>
                  </div>
                </motion.div>
              );
            })}
            {started && <div className="flex justify-center"><Loader2 size={20} className="animate-spin text-muted-foreground" /></div>}
            <div ref={chatEndRef} />
          </CardContent>
        </Card>

        {/* Outcome */}
        {outcome && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="border-0 shadow-card">
              <CardContent className="p-5 space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="font-display font-semibold">Outcome</h3>
                  <StatusBadge status={outcome.status} />
                </div>
                {outcome.reason && <p className="text-sm text-muted-foreground">{outcome.reason}</p>}
                {outcome.unresolved_topics?.length > 0 && (
                  <div>
                    <p className="text-sm font-medium mb-1">Unresolved Topics:</p>
                    <div className="flex flex-wrap gap-1">
                      {outcome.unresolved_topics.map((t: string) => (
                        <span key={t} className="rounded-full bg-muted px-2 py-0.5 text-xs">{t}</span>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Analysis */}
        {analysisData && (
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
            <Card className="border-0 shadow-card">
              <CardHeader><CardTitle className="font-display text-lg">Compatibility Analysis</CardTitle></CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-4">
                  <div className="text-center">
                    <p className="font-display text-4xl font-bold text-primary">{analysisData.scores?.overall ?? '–'}</p>
                    <p className="text-xs text-muted-foreground">Overall Score</p>
                  </div>
                  <StatusBadge status={analysisData.recommendation || analysis.status} />
                </div>

                {/* Sub-scores */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {['finances', 'lifestyle', 'personality', 'logistics'].map(k => (
                    <div key={k} className="rounded-lg bg-muted p-3 text-center">
                      <p className="font-display text-2xl font-bold">{analysisData.scores?.[k] ?? '–'}</p>
                      <p className="text-xs capitalize text-muted-foreground">{k}</p>
                    </div>
                  ))}
                </div>

                {analysisData.dealbreaker_detected && (
                  <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3">
                    <p className="text-sm font-semibold text-destructive">⚠️ Dealbreaker Detected</p>
                    <p className="text-sm text-destructive/80">{analysisData.dealbreaker_detail}</p>
                  </div>
                )}

                {analysisData.highlights?.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-1">✅ Highlights</p>
                    <ul className="text-sm text-muted-foreground space-y-1">{analysisData.highlights.map((h: string, i: number) => <li key={i}>• {h}</li>)}</ul>
                  </div>
                )}
                {analysisData.concerns?.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-1">⚠️ Concerns</p>
                    <ul className="text-sm text-muted-foreground space-y-1">{analysisData.concerns.map((c: string, i: number) => <li key={i}>• {c}</li>)}</ul>
                  </div>
                )}
                {analysisData.middle_ground?.length > 0 && (
                  <div>
                    <p className="text-sm font-semibold mb-1">🤝 Middle Ground</p>
                    <ul className="text-sm text-muted-foreground space-y-1">{analysisData.middle_ground.map((m: string, i: number) => <li key={i}>• {m}</li>)}</ul>
                  </div>
                )}
                {analysisData.recommendation_summary && (
                  <div className="rounded-lg bg-accent p-3">
                    <p className="text-sm font-semibold mb-1">Summary</p>
                    <p className="text-sm text-muted-foreground">{analysisData.recommendation_summary}</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        )}

        {/* Unstructured fallback */}
        {analysis && !analysisData && (
          <Card className="border-0 shadow-card">
            <CardContent className="p-5">
              <h3 className="font-display font-semibold mb-2">Analysis (Raw)</h3>
              <pre className="whitespace-pre-wrap text-sm text-muted-foreground">{JSON.stringify(analysis.result?.data, null, 2)}</pre>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
