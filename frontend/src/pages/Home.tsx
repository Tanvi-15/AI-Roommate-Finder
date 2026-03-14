import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { healthApi, matchesApi } from '@/lib/api';
import { CheckCircle, XCircle, Users, MessageSquare, FileText, Zap, Bot } from 'lucide-react';
import { motion } from 'framer-motion';

export default function HomePage() {
  const { user, hasQuestionnaire } = useAuth();
  const navigate = useNavigate();
  const [health, setHealth] = useState<string | null>(null);
  const [matchCount, setMatchCount] = useState(0);

  useEffect(() => {
    if (!hasQuestionnaire) {
      navigate('/questionnaire');
      return;
    }
    healthApi.check().then(r => setHealth(r.status)).catch(() => setHealth('error'));
    if (user) {
      matchesApi.counts(user.email).then(r => setMatchCount(r.total)).catch(() => {});
    }
  }, [user, hasQuestionnaire]);

  const cards = [
    { to: '/questionnaire', icon: FileText, title: 'Edit Profile', desc: 'Update your questionnaire', color: 'text-primary' },
    { to: '/clone', icon: Bot, title: 'Chat with My Clone', desc: 'Talk to your AI clone to verify it represents you', color: 'text-primary' },
    { to: '/match/setup', icon: Zap, title: 'Setup Match', desc: 'Browse & like profiles near you', color: 'text-secondary' },
    { to: '/matches', icon: Users, title: `My Matches (${matchCount})`, desc: 'View your match results', color: 'text-primary' },
  ];

  return (
    <AppLayout>
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
        <div className="space-y-1">
          <h1 className="font-display text-3xl font-bold">Welcome back, {user?.name} 👋</h1>
          <p className="text-muted-foreground">Your AI roommate matching dashboard</p>
        </div>

        <div className="flex items-center gap-2 text-sm">
          {health === 'healthy' ? (
            <span className="flex items-center gap-1 text-match-strong"><CheckCircle size={14} /> Backend connected</span>
          ) : health === 'error' ? (
            <span className="flex items-center gap-1 text-destructive"><XCircle size={14} /> Backend offline</span>
          ) : (
            <span className="text-muted-foreground">Checking backend…</span>
          )}
          {hasQuestionnaire && (
            <span className="flex items-center gap-1 text-match-strong ml-4"><CheckCircle size={14} /> Profile complete</span>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {cards.map((c, i) => (
            <motion.div key={c.to} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
              <Link to={c.to}>
                <Card className="cursor-pointer border-0 shadow-card transition-shadow hover:shadow-elevated">
                  <CardContent className="flex items-center gap-4 p-5">
                    <div className={`rounded-xl bg-accent p-3 ${c.color}`}>
                      <c.icon size={22} />
                    </div>
                    <div>
                      <p className="font-display font-semibold">{c.title}</p>
                      <p className="text-sm text-muted-foreground">{c.desc}</p>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      </motion.div>
    </AppLayout>
  );
}
