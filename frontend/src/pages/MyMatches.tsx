import { useEffect, useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { AppLayout } from '@/components/AppLayout';
import { StatusBadge } from '@/components/StatusBadge';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { matchesApi, API_URL } from '@/lib/api';
import { Mail, Calendar, ChevronDown, ChevronUp, User } from 'lucide-react';
import { motion } from 'framer-motion';
import { format } from 'date-fns';

export default function MyMatchesPage() {
  const { user } = useAuth();
  const [matches, setMatches] = useState<any[]>([]);
  const [counts, setCounts] = useState<any>(null);
  const [showIncompat, setShowIncompat] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    matchesApi.counts(user.email).then(setCounts).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!user) return;
    matchesApi.list(user.email, showIncompat).then(setMatches).catch(() => setMatches([]));
  }, [user, showIncompat]);

  const otherName = (m: any) => m.user_a_id === user?.email ? m.user_b_name : m.user_a_name;
  const otherEmail = (m: any) => m.user_a_id === user?.email ? m.user_b_id : m.user_a_id;
  const otherPhoto = (m: any) => {
    const photos = m.other_photos || [];
    if (photos.length > 0) return `${API_URL}${photos[0]}`;
    return m.other_profile_picture || null;
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <h1 className="font-display text-2xl font-bold">My Matches {counts ? `(${counts.total})` : ''}</h1>
          <div className="flex items-center gap-2">
            <Switch id="incompat" checked={showIncompat} onCheckedChange={setShowIncompat} />
            <Label htmlFor="incompat" className="text-sm">Show incompatible</Label>
          </div>
        </div>

        {counts && (
          <div className="flex gap-3 text-sm">
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-match-strong" /> {counts.strong} strong</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-match-conditional" /> {counts.conditional} conditional</span>
            <span className="flex items-center gap-1"><span className="h-2 w-2 rounded-full bg-match-incompatible" /> {counts.incompatible} incompatible</span>
          </div>
        )}

        {matches.length === 0 && (
          <p className="text-center text-muted-foreground py-12">No matches yet. Run a compatibility match to see results here.</p>
        )}

        <div className="space-y-3">
          {matches.map((m, i) => {
            const isExpanded = expanded === m.match_id;
            const scores = m.analysis?.structured && m.analysis?.data?.scores;
            return (
              <motion.div key={m.match_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                <Card className="border-0 shadow-card overflow-hidden">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1">
                        {otherPhoto(m) ? (
                          <img src={otherPhoto(m)} alt={otherName(m)} className="w-12 h-12 rounded-full object-cover shrink-0" />
                        ) : (
                          <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center shrink-0">
                            <User size={20} className="text-muted-foreground" />
                          </div>
                        )}
                        <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-3">
                          <p className="font-display font-semibold text-lg">{otherName(m)}</p>
                          <StatusBadge status={m.status} />
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1"><Calendar size={12} /> {m.created_at ? format(new Date(m.created_at), 'MMM d, yyyy') : '–'}</span>
                          {scores && <span>Score: {scores.overall}/100</span>}
                        </div>
                        {m.status === 'conditional' && m.unresolved_topics?.length > 0 && (
                          <div className="mt-2 flex flex-wrap gap-1">
                            {m.unresolved_topics.map((t: string) => (
                              <span key={t} className="rounded-full bg-match-conditional/20 text-match-conditional-foreground px-2 py-0.5 text-xs">{t}</span>
                            ))}
                          </div>
                        )}
                        {m.status === 'incompatible' && m.reason && (
                          <p className="mt-1 text-sm text-destructive">{m.reason}</p>
                        )}
                        </div>
                      </div>
                      <Button variant="ghost" size="sm" onClick={() => setExpanded(isExpanded ? null : m.match_id)}>
                        {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                      </Button>
                    </div>

                    {isExpanded && (
                      <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} className="mt-4 border-t pt-4 space-y-3">
                        <div className="flex items-center gap-2 text-sm">
                          <Mail size={14} className="text-primary" />
                          <span>{otherEmail(m)}</span>
                        </div>
                        {scores && (
                          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                            {['finances', 'lifestyle', 'personality', 'logistics'].map(k => (
                              <div key={k} className="rounded-lg bg-muted p-2 text-center">
                                <p className="font-bold">{scores[k] ?? '–'}</p>
                                <p className="text-xs capitalize text-muted-foreground">{k}</p>
                              </div>
                            ))}
                          </div>
                        )}
                      </motion.div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
}
