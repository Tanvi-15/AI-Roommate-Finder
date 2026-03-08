import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import LoginPage from "./pages/Login";
import AuthCallback from "./pages/AuthCallback";
import HomePage from "./pages/Home";
import QuestionnairePage from "./pages/Questionnaire";
import SetupMatchPage from "./pages/SetupMatch";
import AgentChatPage from "./pages/AgentChat";
import MyMatchesPage from "./pages/MyMatches";
import MyClonePage from "./pages/MyClone";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center text-muted-foreground">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <div className="flex min-h-screen items-center justify-center text-muted-foreground">Loading…</div>;

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/" element={<ProtectedRoute><HomePage /></ProtectedRoute>} />
      <Route path="/questionnaire" element={<ProtectedRoute><QuestionnairePage /></ProtectedRoute>} />
      <Route path="/match/setup" element={<ProtectedRoute><SetupMatchPage /></ProtectedRoute>} />
      <Route path="/match/chat/:roomId" element={<ProtectedRoute><AgentChatPage /></ProtectedRoute>} />
      <Route path="/clone" element={<ProtectedRoute><MyClonePage /></ProtectedRoute>} />
      <Route path="/matches" element={<ProtectedRoute><MyMatchesPage /></ProtectedRoute>} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
