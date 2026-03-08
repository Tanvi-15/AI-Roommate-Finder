import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { agentsApi, roomsApi } from '@/lib/api';
import { CheckCircle, XCircle, Loader2, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { motion } from 'framer-motion';

type UserInput = { email: string; name: string; questionnaire: any };
type ValidationResult = { validated: boolean; results: any[] } | null;

export default function SetupMatchPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [userA, setUserA] = useState<UserInput>({
    email: user?.email || '',
    name: user?.name || '',
    questionnaire: user?.questionnaire || {},
  });
  const [userB, setUserB] = useState<UserInput>({ email: '', name: '', questionnaire: {} });
  const [valA, setValA] = useState<ValidationResult>(null);
  const [valB, setValB] = useState<ValidationResult>(null);
  const [loadingA, setLoadingA] = useState(false);
  const [loadingB, setLoadingB] = useState(false);
  const [creating, setCreating] = useState(false);

  const validateClone = async (u: UserInput, setVal: (v: ValidationResult) => void, setLoading: (b: boolean) => void) => {
    setLoading(true);
    try {
      await agentsApi.create({ user_id: u.email, name: u.name, questionnaire: u.questionnaire });
      const res = await agentsApi.validate(u.email);
      setVal(res);
      if (res.validated) toast.success(`${u.name}'s clone validated!`);
      else toast.error(`${u.name}'s clone has issues`);
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const startMatch = async () => {
    setCreating(true);
    try {
      const room = await roomsApi.create({ user_a_id: userA.email, user_b_id: userB.email });
      navigate(`/match/chat/${room.room_id}`, { state: { room } });
    } catch (err: any) {
      toast.error(err.message);
    } finally {
      setCreating(false);
    }
  };

  const renderValidation = (val: ValidationResult) => {
    if (!val) return null;
    return (
      <div className="mt-3 space-y-2">
        <p className={`flex items-center gap-1 text-sm font-medium ${val.validated ? 'text-match-strong' : 'text-destructive'}`}>
          {val.validated ? <CheckCircle size={14} /> : <XCircle size={14} />}
          {val.validated ? 'Validated' : 'Validation failed'}
        </p>
        {val.results?.map((r, i) => (
          <div key={i} className="rounded-lg bg-muted p-2 text-sm">
            <p className="font-medium">{r.question}</p>
            {r.status === 'success' ? (
              <p className="text-muted-foreground">{r.response}</p>
            ) : (
              <p className="text-destructive">{r.error}</p>
            )}
          </div>
        ))}
      </div>
    );
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl space-y-6">
        <h1 className="font-display text-2xl font-bold">Setup Roommate Match</h1>
        <p className="text-muted-foreground">Validate both clones, then start the AI conversation.</p>

        <div className="grid gap-6 md:grid-cols-2">
          {/* User A */}
          <Card className="border-0 shadow-card">
            <CardHeader><CardTitle className="text-lg">User A (You)</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div><Label>Email</Label><Input value={userA.email} onChange={e => setUserA(p => ({ ...p, email: e.target.value }))} /></div>
              <div><Label>Name</Label><Input value={userA.name} onChange={e => setUserA(p => ({ ...p, name: e.target.value }))} /></div>
              <Button variant="outline" className="w-full" onClick={() => validateClone(userA, setValA, setLoadingA)} disabled={loadingA}>
                {loadingA ? <Loader2 size={14} className="animate-spin mr-2" /> : null}
                Validate Clone A
              </Button>
              {renderValidation(valA)}
            </CardContent>
          </Card>

          {/* User B */}
          <Card className="border-0 shadow-card">
            <CardHeader><CardTitle className="text-lg">User B</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div><Label>Email</Label><Input value={userB.email} onChange={e => setUserB(p => ({ ...p, email: e.target.value }))} placeholder="user-b@email.com" /></div>
              <div><Label>Name</Label><Input value={userB.name} onChange={e => setUserB(p => ({ ...p, name: e.target.value }))} placeholder="Name" /></div>
              <Button variant="outline" className="w-full" onClick={() => validateClone(userB, setValB, setLoadingB)} disabled={loadingB}>
                {loadingB ? <Loader2 size={14} className="animate-spin mr-2" /> : null}
                Validate Clone B
              </Button>
              {renderValidation(valB)}
            </CardContent>
          </Card>
        </div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <Button
            size="lg"
            className="w-full gap-2"
            onClick={startMatch}
            disabled={creating || !valA?.validated || !valB?.validated}
          >
            {creating ? <Loader2 size={16} className="animate-spin" /> : <Zap size={16} />}
            Start Agent Chat
          </Button>
        </motion.div>
      </div>
    </AppLayout>
  );
}
