import { useState, useMemo } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AppLayout } from '@/components/AppLayout';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { usersApi, interactionsApi, API_URL } from '@/lib/api';
import { Heart, X, MapPin, Briefcase, User, Cigarette, Wine, Dog, BedDouble, Loader2, Users, Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import { motion, AnimatePresence } from 'framer-motion';

type Candidate = {
  email: string;
  name: string;
  city: string;
  neighborhood: string;
  questionnaire: Record<string, any>;
  photos: string[];
  profile_picture_url?: string;
  same_location: boolean;
  location_match_score: number;
};

function getDisplayValue(q: Record<string, any>, section: string, key: string): string {
  return String((q?.[section] || {})[key] || '—');
}

function getSocialLabel(val: number): string {
  if (val <= 1) return 'Very introverted';
  if (val <= 2) return 'Introverted';
  if (val <= 3) return 'Balanced';
  if (val <= 4) return 'Extroverted';
  return 'Very extroverted';
}

function ProfileCard({ candidate, onLike, onPass, isActing }: {
  candidate: Candidate;
  onLike: () => void;
  onPass: () => void;
  isActing: boolean;
}) {
  const q = candidate.questionnaire;
  const living = q?.living || {};
  const social = q?.social || {};
  const lifestyle = q?.lifestyle || {};

  const photoUrl = candidate.photos?.[0]
    ? `${API_URL}${candidate.photos[0]}`
    : candidate.profile_picture_url || null;

  const introExtro = social.introvert_extrovert;

  return (
    <Card className="border-0 shadow-elevated overflow-hidden max-w-md mx-auto">
      {/* Photo section */}
      <div className="relative h-64 bg-gradient-to-br from-primary/20 to-secondary/20">
        {photoUrl ? (
          <img src={photoUrl} alt={candidate.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <User size={64} className="text-muted-foreground/30" />
          </div>
        )}
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-4">
          <h2 className="text-white font-display text-2xl font-bold">{candidate.name}</h2>
          <div className="flex items-center gap-1 text-white/80 text-sm">
            <MapPin size={14} />
            <span>{candidate.city}{candidate.neighborhood ? `, ${candidate.neighborhood}` : ''}</span>
          </div>
        </div>
      </div>

      <CardContent className="p-5 space-y-4">
        {/* Details grid */}
        <div className="grid grid-cols-2 gap-3">
          <DetailChip icon={Briefcase} label="Occupation" value={getDisplayValue(q, 'living', 'occupation')} />
          <DetailChip icon={BedDouble} label="Room type" value={getDisplayValue(q, 'living', 'room_type')} />
          <DetailChip icon={Dog} label="Pets" value={getDisplayValue(q, 'living', 'pets')} />
          <DetailChip icon={Cigarette} label="Smoking" value={getDisplayValue(q, 'living', 'smoking')} />
          <DetailChip icon={Wine} label="Drinking" value={getDisplayValue(q, 'living', 'drinking')} />
          <DetailChip
            icon={Users}
            label="Social"
            value={introExtro != null ? getSocialLabel(Number(introExtro)) : '—'}
          />
        </div>

        {/* Hobbies */}
        {lifestyle.hobbies && (
          <div>
            <p className="text-xs font-medium text-muted-foreground mb-1.5">Hobbies & Interests</p>
            <p className="text-sm">{lifestyle.hobbies}</p>
          </div>
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-2">
          <Button
            variant="outline"
            size="lg"
            className="flex-1 gap-2 border-destructive/30 text-destructive hover:bg-destructive/10 hover:text-destructive"
            onClick={onPass}
            disabled={isActing}
          >
            <X size={20} />
            Pass
          </Button>
          <Button
            size="lg"
            className="flex-1 gap-2 bg-gradient-to-r from-pink-500 to-rose-500 hover:from-pink-600 hover:to-rose-600 text-white"
            onClick={onLike}
            disabled={isActing}
          >
            {isActing ? <Loader2 size={20} className="animate-spin" /> : <Heart size={20} />}
            Like
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function DetailChip({ icon: Icon, label, value }: { icon: any; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-muted/50 p-2.5">
      <Icon size={14} className="text-muted-foreground mt-0.5 shrink-0" />
      <div className="min-w-0">
        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
        <p className="text-sm font-medium truncate">{value}</p>
      </div>
    </div>
  );
}

export default function SetupMatchPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isActing, setIsActing] = useState(false);
  const [exitDirection, setExitDirection] = useState<'left' | 'right' | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['setup-match-candidates'],
    queryFn: () => usersApi.candidates(),
    enabled: !!user,
    staleTime: 30_000,
  });

  const candidates = useMemo(() => data?.candidates ?? [], [data]);
  const currentCandidate = candidates[currentIndex] ?? null;
  const remaining = candidates.length - currentIndex;

  const advanceCard = (direction: 'left' | 'right') => {
    setExitDirection(direction);
    setTimeout(() => {
      setCurrentIndex(prev => prev + 1);
      setExitDirection(null);
    }, 300);
  };

  const handleLike = async () => {
    if (!currentCandidate || isActing) return;
    setIsActing(true);
    try {
      await interactionsApi.like(currentCandidate.email);
      toast.success(`Liked ${currentCandidate.name}! Agents are negotiating...`, {
        icon: <Sparkles size={16} />,
      });
      advanceCard('right');
    } catch (err: any) {
      toast.error(err.message || 'Failed to like');
    } finally {
      setIsActing(false);
    }
  };

  const handlePass = async () => {
    if (!currentCandidate || isActing) return;
    setIsActing(true);
    try {
      await interactionsApi.pass(currentCandidate.email);
      advanceCard('left');
    } catch (err: any) {
      toast.error(err.message || 'Failed to pass');
    } finally {
      setIsActing(false);
    }
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-lg space-y-6">
        <div>
          <h1 className="font-display text-2xl font-bold">Find Roommates</h1>
          <p className="text-muted-foreground text-sm">
            Browse profiles in your area. Like someone and your AI agents will negotiate compatibility.
          </p>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-20">
            <Loader2 size={32} className="animate-spin text-muted-foreground" />
          </div>
        )}

        {!isLoading && candidates.length === 0 && (
          <Card className="border-0 shadow-card">
            <CardContent className="py-16 text-center">
              <Users size={48} className="mx-auto text-muted-foreground/30 mb-4" />
              <h3 className="font-display text-lg font-semibold mb-2">No profiles to show</h3>
              <p className="text-muted-foreground text-sm">
                No matching profiles in your area yet. Check back later or update your location in your profile.
              </p>
            </CardContent>
          </Card>
        )}

        {!isLoading && currentCandidate && (
          <>
            <p className="text-xs text-muted-foreground text-center">
              {remaining} profile{remaining !== 1 ? 's' : ''} remaining
            </p>
            <AnimatePresence mode="wait">
              <motion.div
                key={currentCandidate.email}
                initial={{ opacity: 0, x: 50, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{
                  opacity: 0,
                  x: exitDirection === 'left' ? -200 : exitDirection === 'right' ? 200 : 0,
                  scale: 0.9,
                  transition: { duration: 0.3 },
                }}
                transition={{ duration: 0.3 }}
              >
                <ProfileCard
                  candidate={currentCandidate}
                  onLike={handleLike}
                  onPass={handlePass}
                  isActing={isActing}
                />
              </motion.div>
            </AnimatePresence>
          </>
        )}

        {!isLoading && candidates.length > 0 && !currentCandidate && (
          <Card className="border-0 shadow-card">
            <CardContent className="py-16 text-center">
              <Sparkles size={48} className="mx-auto text-primary/50 mb-4" />
              <h3 className="font-display text-lg font-semibold mb-2">You've seen everyone!</h3>
              <p className="text-muted-foreground text-sm mb-4">
                Check My Matches to see your agent negotiation results.
              </p>
              <Button
                variant="outline"
                onClick={() => {
                  setCurrentIndex(0);
                  queryClient.invalidateQueries({ queryKey: ['setup-match-candidates'] });
                }}
              >
                Refresh profiles
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </AppLayout>
  );
}
