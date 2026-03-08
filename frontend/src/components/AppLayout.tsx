import { useAuth } from '@/contexts/AuthContext';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { LogOut, Home, Users, MessageSquare, FileText, Bot } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/', icon: Home, label: 'Home' },
    { to: '/questionnaire', icon: FileText, label: 'Profile' },
    { to: '/clone', icon: Bot, label: 'My Clone' },
    { to: '/match/setup', icon: Users, label: 'Match' },
    { to: '/matches', icon: MessageSquare, label: 'Matches' },
  ];

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 border-b border-border bg-card/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <Link to="/" className="font-display text-xl font-bold text-primary flex items-center gap-2">
            <img src="/roommate.png" alt="RoommateFinder" className="h-8 w-8 object-contain" />
            RoommateFinder
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {navItems.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  location.pathname === item.to
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                <item.icon size={16} />
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="flex items-center gap-3">
            {user && (
              <span className="hidden text-sm text-muted-foreground sm:inline">
                {user.name}
              </span>
            )}
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut size={16} />
            </Button>
          </div>
        </div>
      </header>
      {/* Mobile nav */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 flex border-t border-border bg-card/95 backdrop-blur-md md:hidden">
        {navItems.map((item) => (
          <Link
            key={item.to}
            to={item.to}
            className={`flex flex-1 flex-col items-center gap-1 py-2 text-xs ${
              location.pathname === item.to ? 'text-primary' : 'text-muted-foreground'
            }`}
          >
            <item.icon size={18} />
            {item.label}
          </Link>
        ))}
      </nav>
      <main className="mx-auto max-w-6xl px-4 py-6 pb-20 md:pb-6">{children}</main>
    </div>
  );
}
