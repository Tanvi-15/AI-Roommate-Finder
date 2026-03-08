import { useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';

export default function AuthCallback() {
  const [params] = useSearchParams();
  const { googleCallback } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    const code = params.get('code');
    const state = params.get('state');
    if (code && state) {
      googleCallback(code, state)
        .then(() => navigate('/'))
        .catch(() => navigate('/login'));
    } else {
      navigate('/login');
    }
  }, []);

  return (
    <div className="flex min-h-screen items-center justify-center">
      <p className="text-muted-foreground">Completing sign in…</p>
    </div>
  );
}
