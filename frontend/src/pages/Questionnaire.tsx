import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm, Controller } from 'react-hook-form';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '@/contexts/AuthContext';
import { authApi, photosApi, API_URL } from '@/lib/api';
import { AppLayout } from '@/components/AppLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Check, Loader2, Upload, X, Bot } from 'lucide-react';
import { toast } from 'sonner';


type Q = Record<string, Record<string, unknown>>;

const CITY_OPTIONS = [
  'Boston', 'Cambridge', 'Somerville', 'Brookline', 'Allston', 'Brighton',
  'Medford', 'Watertown', 'Newton', 'Quincy',
  'New York', 'Brooklyn', 'Queens', 'Manhattan', 'Bronx',
  'San Francisco', 'Oakland', 'Berkeley', 'San Jose', 'Palo Alto',
  'Los Angeles', 'Chicago', 'Seattle', 'Austin', 'Denver',
  'Portland', 'Philadelphia', 'Washington DC', 'Miami', 'Atlanta',
  'Other',
];

const SECTIONS = [
  {
    key: 'living', title: '🏡 Living Preferences', fields: [
      { key: 'city', label: 'City', type: 'select', required: true, options: CITY_OPTIONS },
      { key: 'neighborhood', label: 'Neighborhood (optional)', type: 'text', placeholder: 'e.g. South Boston, Back Bay, Downtown' },
      { key: 'occupation', label: 'Occupation', type: 'select', required: true, options: ['Student', 'Working Professional', 'Freelancer / Self-employed', 'Between jobs', 'Other'] },
      { key: 'gender', label: 'Your gender', type: 'select', required: true, options: ['Man', 'Woman', 'Non-binary', 'Prefer not to say'] },
      { key: 'move_in_date', label: 'Move-in date', type: 'select', options: ['ASAP', 'Within 1 month', '1–3 months', '3–6 months', 'Flexible'] },
      { key: 'lease_type', label: 'Lease preference', type: 'select', options: ['Month-to-month', '6-month lease', '1-year lease', 'No preference'] },
      { key: 'budget_min', label: 'Min budget ($)', type: 'number', required: true, min: 300, max: 5000, default: 800 },
      { key: 'budget_max', label: 'Max budget ($)', type: 'number', required: true, min: 300, max: 5000, default: 1500 },
      { key: 'budget_flexibility', label: 'Budget flexibility', type: 'select', required: true, options: ['Hard limit', 'Can flex ~$100', 'Can flex ~$200', 'Fairly flexible'] },
      { key: 'room_type', label: 'Room type', type: 'select', required: true, options: ['Private room', 'Shared room', 'Either is fine'] },
      { key: 'bathroom_preference', label: 'Bathroom', type: 'select', options: ['Private', 'Shared with 1', 'Shared 2+', 'No preference'] },
      { key: 'roommate_gender', label: 'Roommate gender pref', type: 'select', required: true, options: ['Same gender only', 'Any gender', 'No preference'] },
      { key: 'pets', label: 'Pets', type: 'select', required: true, options: ['I have pets', 'I love pets', 'No pets please', 'Allergic'] },
      { key: 'smoking', label: 'Smoking', type: 'select', required: true, options: ['I smoke', 'Okay with smokers', 'Non-smoking only'] },
      { key: 'drinking', label: 'Drinking', type: 'select', required: true, options: ['Never', 'Socially', 'Regularly'] },
    ]
  },
  {
    key: 'financial', title: '💰 Financial & Utilities', fields: [
      { key: 'utilities_split', label: 'Split utilities', type: 'select', options: ['Split equally', 'Split by usage/room size', 'Included in rent', 'Discuss case by case'] },
      { key: 'groceries_split', label: 'Shared groceries', type: 'select', options: ['Completely separate', 'Split basics', 'Fully shared', 'Open to discussing'] },
      { key: 'security_deposit', label: 'Security deposit', type: 'select', options: ['Yes up to 1 month', 'Yes up to 2 months', 'Need to split', 'Not sure'] },
      { key: 'payment_style', label: 'Shared payments', type: 'select', options: ['One pays + Venmo/Zelle', 'Each pays share', 'Shared app', 'No preference'] },
    ]
  },
  {
    key: 'routines', title: '⏰ Daily Routines', fields: [
      { key: 'sleep_schedule', label: 'Sleep schedule', type: 'select', required: true, options: ['Early bird', 'Night owl', 'In between', 'Varies a lot'] },
      { key: 'wake_time', label: 'Wake time', type: 'select', options: ['Before 6am', '6–8am', '8–10am', 'After 10am', 'Varies'] },
      { key: 'cooking_habits', label: 'Cooking frequency', type: 'select', options: ['Daily', 'A few times/week', 'Rarely/takeout', 'Meal prep weekends'] },
      { key: 'kitchen_sharing', label: 'Kitchen sharing', type: 'select', options: ['Happy to share/cook together', 'Separate times', 'No preference', 'Barely use'] },
      { key: 'bathroom_time', label: 'Morning bathroom time', type: 'select', options: ['Under 15 min', '15–30', '30–45', 'Over 45 min'] },
      { key: 'common_space_usage', label: 'Common space use', type: 'select', options: ['Lots in common areas', 'Mostly in room', 'Balanced', 'Depends'] },
      { key: 'cleanliness', label: 'Cleanliness (1=Relaxed, 5=Spotless)', type: 'slider', required: true, min: 1, max: 5, default: 3 },
      { key: 'cleaning_schedule', label: 'Cleaning approach', type: 'select', options: ['Chore chart', 'Clean as you go', 'Hire cleaner', 'Discuss together'] },
    ]
  },
  {
    key: 'social', title: '🎉 Guests & Social', fields: [
      { key: 'noise_level', label: 'Noise/social at home', type: 'select', required: true, options: ['Very quiet', 'Occasional friends', 'Social/lively', 'Balance'] },
      { key: 'overnight_guests', label: 'Overnight guests', type: 'select', required: true, options: ['Never', 'Occasionally', 'Regularly', 'Partner often'] },
      { key: 'guest_notice', label: 'Guest notice', type: 'select', options: ['Always', 'Usually for 1–2+', 'No strong opinion', 'Spontaneous'] },
      { key: 'parties', label: 'Parties at home', type: 'select', options: ['Yes', 'Small only (<10)', 'Rarely with notice', 'No'] },
      { key: 'introvert_extrovert', label: 'Social spectrum (1=Intro, 5=Extro)', type: 'slider', min: 1, max: 5, default: 3 },
    ]
  },
  {
    key: 'lifestyle', title: '💼 Work & Lifestyle', fields: [
      { key: 'work_from_home', label: 'Work from home', type: 'select', options: ['Full-time remote', 'Hybrid', 'No/office daily', 'Varies'] },
      { key: 'quiet_hours_needed', label: 'Quiet hours for calls', type: 'select', options: ['Yes frequently', 'Occasionally', 'Rarely/headphones', 'No'] },
      { key: 'schedule_predictability', label: 'Schedule predictability', type: 'select', options: ['Very consistent', 'Mostly consistent', 'Unpredictable/shift', 'Changes by season'] },
      { key: 'temperature_preference', label: 'Thermostat', type: 'select', options: ['Cool', 'Moderate', 'Warm', 'No preference'] },
      { key: 'hobbies', label: 'Hobbies/interests', type: 'text', placeholder: 'gaming, cooking, hiking…' },
      { key: 'lifestyle_notes', label: 'Other notes', type: 'textarea' },
    ]
  },
  {
    key: 'personality', title: '🧠 Personality & Conflict', fields: [
      { key: 'conflict_style', label: 'Handle conflicts', type: 'select', options: ['Direct conversation', 'Cool off then discuss', 'Write it out', 'Prefer to avoid'] },
      { key: 'communication_style', label: 'Communication style', type: 'select', options: ['Group chat/text', 'Talk in person', 'Minimal/respect space', 'Mix'] },
      { key: 'roommate_relationship', label: 'Roommate relationship', type: 'select', options: ['Close friends', 'Friendly but independent', 'Cordial/separate', 'No preference'] },
    ]
  },
  {
    key: 'dealbreakers', title: '🚫 Dealbreakers & Priorities', fields: [
      { key: 'non_negotiables', label: 'Non-negotiables (select at least 1)', type: 'multiselect', required: true, options: ['No smoking indoors', 'No pets', 'No overnight guests', 'Strict quiet hours', 'Kitchen very clean', 'No parties ever', 'Same gender only', 'Budget hard cap', 'Must be okay with my pet(s)', 'Non-smoking only'] },
      { key: 'top_priorities', label: 'Top 3 priorities (max 3)', type: 'multiselect', required: true, max: 3, options: ['Compatible sleep', 'Cleanliness', 'Quiet/work time', 'Budget', 'Pet-friendly', 'Social energy', 'Location', 'Communication', 'Guest/party preferences'] },
      { key: 'flexible_on', label: 'Most flexible on', type: 'multiselect', options: ['Budget', 'Move-in date', 'Lease length', 'Chore split', 'Grocery', 'Guest frequency', 'Noise', 'Temperature'] },
      { key: 'custom_dealbreaker', label: 'Other dealbreakers', type: 'text', placeholder: 'Anything else?' },
    ]
  },
];

const BACKEND_TO_FRONTEND: Record<string, string> = {
  'Hard limit — cannot go over': 'Hard limit',
  'Can flex up to ~$100': 'Can flex ~$100',
  'Can flex up to ~$200': 'Can flex ~$200',
  'Fairly flexible if the fit is right': 'Fairly flexible',
  'Private bathroom': 'Private',
  'Shared with 1 person': 'Shared with 1',
  'Shared with 2+ people': 'Shared 2+',
  'I love pets but don\'t have any': 'I love pets',
  'Allergic to pets': 'Allergic',
  'Non-smoking household only': 'Non-smoking only',
};

function normalizeQuestionnaireForForm(q: Record<string, unknown> | null | undefined): Q {
  const defaults = getDefaultValues();
  if (!q || typeof q !== 'object') return defaults;
  const init: Q = {};
  SECTIONS.forEach(s => {
    const section = q[s.key];
    init[s.key] = { ...defaults[s.key] };
    if (section && typeof section === 'object' && !Array.isArray(section)) {
      const sectionObj = section as Record<string, unknown>;
      for (const f of s.fields) {
        const val = sectionObj[f.key];
        if (val === undefined) continue;
        if (Array.isArray(val)) {
          (init[s.key] as Record<string, unknown>)[f.key] = val.map(v =>
            typeof v === 'string' && BACKEND_TO_FRONTEND[v] !== undefined ? BACKEND_TO_FRONTEND[v] : v
          );
        } else if (typeof val === 'string' && BACKEND_TO_FRONTEND[val] !== undefined) {
          (init[s.key] as Record<string, unknown>)[f.key] = BACKEND_TO_FRONTEND[val];
        } else {
          (init[s.key] as Record<string, unknown>)[f.key] = val;
        }
      }
    }
  });
  if (!init.living?.gender) {
    (init.living as Record<string, unknown>).gender = 'Prefer not to say';
  }
  // Backward compat: old profiles have `location` instead of `city`
  const livingSection = q?.living as Record<string, unknown> | undefined;
  if (livingSection?.location && !init.living?.city) {
    const loc = String(livingSection.location);
    if (CITY_OPTIONS.includes(loc)) {
      (init.living as Record<string, unknown>).city = loc;
    } else {
      (init.living as Record<string, unknown>).city = 'Other';
      (init.living as Record<string, unknown>).neighborhood = loc;
    }
  }
  return init;
}

function getDefaultValues(): Q {
  const init: Q = {};
  SECTIONS.forEach(s => {
    init[s.key] = {};
    s.fields.forEach((f: { key: string; type: string; default?: number; min?: number; options?: string[] }) => {
      if (f.type === 'multiselect') (init[s.key] as Record<string, unknown>)[f.key] = [];
      else if (f.type === 'number' || f.type === 'slider') (init[s.key] as Record<string, unknown>)[f.key] = f.default ?? f.min ?? 0;
      else (init[s.key] as Record<string, unknown>)[f.key] = '';
    });
  });
  (init.living as Record<string, unknown>).gender = 'Prefer not to say';
  return init;
}

export default function QuestionnairePage() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const queryClient = useQueryClient();
  const skipNextProfileSyncRef = useRef(false);
  const [step, setStep] = useState(() => {
    if (typeof window === 'undefined') return 0;
    const raw = window.localStorage.getItem('questionnaire_step');
    const n = raw != null ? Number(raw) : 0;
    if (!Number.isFinite(n)) return 0;
    return Math.max(0, Math.min(n, SECTIONS.length - 1));
  });

  const { data: profileData, isLoading: profileLoading } = useQuery({
    queryKey: ['profile'],
    queryFn: () => authApi.me(),
    staleTime: 60_000,
    refetchOnWindowFocus: false, // Avoid refetch overwriting form when user returns to tab
  });

  const form = useForm<Q>({
    defaultValues: getDefaultValues(),
    mode: 'onChange',
  });

  const { reset, watch, handleSubmit, getValues, control, formState: { isDirty } } = form;

  const saveMutation = useMutation({
    mutationFn: (questionnaire: Q) => authApi.updateProfile({ questionnaire }),
    onSuccess: async (_, submittedData) => {
      const { user } = await authApi.me();
      setUser(user);
      queryClient.setQueryData(['profile'], { user });
      reset(submittedData);
      skipNextProfileSyncRef.current = true;
      if (typeof window !== 'undefined') window.localStorage.removeItem('questionnaire_draft');
      toast.success('Profile saved');
    },
    onError: (e: Error) => toast.error(e.message || 'Failed to save profile'),
  });

  // Load backend data into form when profile is fetched (only when not saving and no unsaved changes)
  useEffect(() => {
    if (!profileData?.user) return;
    setUser(profileData.user);
    if (saveMutation.isPending) return;
    if (isDirty) return;
    if (skipNextProfileSyncRef.current) {
      skipNextProfileSyncRef.current = false;
      return;
    }
    const q = profileData.user.questionnaire;
    const normalized = q && typeof q === 'object' && Object.keys(q).length > 0
      ? normalizeQuestionnaireForForm(q as Record<string, unknown>)
      : getDefaultValues();

    // Merge in any locally-saved draft values so mid-edit refreshes don't lose work
    const draft = typeof window !== 'undefined' ? window.localStorage.getItem('questionnaire_draft') : null;
    if (draft) {
      try {
        const parsed = JSON.parse(draft) as Q;
        SECTIONS.forEach(s => {
          if (parsed[s.key] && typeof parsed[s.key] === 'object') {
            Object.entries(parsed[s.key]).forEach(([k, v]) => {
              if (v !== undefined && v !== '' && !(Array.isArray(v) && v.length === 0)) {
                (normalized[s.key] as Record<string, unknown>)[k] = v;
              }
            });
          }
        });
      } catch { /* ignore corrupt data */ }
    }

    reset(normalized);
  }, [profileData?.user, reset, setUser, saveMutation.isPending, isDirty]);

  // Persist draft form values to localStorage on every change so mid-edit refreshes are safe
  useEffect(() => {
    if (!isDirty) return;
    const sub = watch((values) => {
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('questionnaire_draft', JSON.stringify(values));
      }
    });
    return () => sub.unsubscribe();
  }, [watch, isDirty]);

  const safeStep = Math.max(0, Math.min(step, SECTIONS.length - 1));
  const section = SECTIONS[safeStep];
  const sectionValues = watch(section?.key) || {};

  const validateStep = useCallback(() => {
    for (const f of section.fields) {
      if (!(f as { required?: boolean }).required) continue;
      const v = sectionValues[f.key];
      if ((f as { type: string }).type === 'multiselect') {
        const arr = Array.isArray(v) ? v : [];
        if (arr.length === 0) {
          toast.error(`${(f as { label: string }).label} is required`);
          return false;
        }
      } else if (v === undefined || v === '' || v === null) {
        toast.error(`${(f as { label: string }).label} is required`);
        return false;
      }
    }
    if (section.key === 'living') {
      const min = Number(sectionValues.budget_min);
      const max = Number(sectionValues.budget_max);
      if (min != null && max != null && min > max) {
        toast.error('Min budget must be ≤ Max budget');
        return false;
      }
    }
    return true;
  }, [section, sectionValues]);

  const updateStep = (updater: (prev: number) => number) => {
    setStep(prev => {
      const next = Math.max(0, Math.min(updater(prev), SECTIONS.length - 1));
      if (typeof window !== 'undefined') {
        window.localStorage.setItem('questionnaire_step', String(next));
      }
      return next;
    });
  };

  const next = () => {
    if (!validateStep()) return;
    const data = getValues();
    // Navigate immediately; save runs in background
    updateStep(s => s + 1);
    saveMutation.mutate(data);
  };
  const prev = () => {
    saveMutation.mutate(getValues()); // save in background when going back
    updateStep(s => s - 1);
  };

  const [isFinishing, setIsFinishing] = useState(false);
  const [showAgentOverlay, setShowAgentOverlay] = useState(false);

  // Photo upload state
  const [photos, setPhotos] = useState<string[]>([]);
  const [uploadingPhotos, setUploadingPhotos] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (profileData?.user?.photos) {
      setPhotos(profileData.user.photos);
    }
  }, [profileData?.user?.photos]);

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length === 0) return;
    if (photos.length + files.length > 2) {
      toast.error('Maximum 2 photos allowed');
      return;
    }
    setUploadingPhotos(true);
    try {
      const result = await photosApi.upload(files);
      setPhotos(result.photos);
      toast.success('Photos uploaded');
    } catch (err: any) {
      toast.error(err.message || 'Failed to upload photos');
    } finally {
      setUploadingPhotos(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const removePhoto = (index: number) => {
    setPhotos(prev => prev.filter((_, i) => i !== index));
  };

  const onFinish = handleSubmit((data) => {
    if (isFinishing) return;
    setIsFinishing(true);
    setShowAgentOverlay(true);
    saveMutation.mutate(data, {
      onSuccess: () => {
        setTimeout(() => {
          setShowAgentOverlay(false);
          setIsFinishing(false);
          if (typeof window !== 'undefined') {
            window.localStorage.removeItem('questionnaire_step');
            window.localStorage.removeItem('questionnaire_draft');
          }
          navigate('/');
        }, 2000);
      },
      onError: () => {
        setShowAgentOverlay(false);
        setIsFinishing(false);
      },
    });
  });

  if (profileLoading) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-2xl flex items-center justify-center py-12 text-muted-foreground">
          Loading profile…
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-2xl space-y-6">
        {/* Photo upload section */}
        <Card className="border-0 shadow-card">
          <CardHeader>
            <CardTitle className="font-display text-lg">Your Photos</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-4 items-start">
              {photos.map((url, i) => (
                <div key={i} className="relative w-24 h-24 rounded-xl overflow-hidden border-2 border-border group">
                  <img src={`${API_URL}${url}`} alt={`Photo ${i + 1}`} className="w-full h-full object-cover" />
                  <button
                    type="button"
                    onClick={() => removePhoto(i)}
                    className="absolute top-1 right-1 bg-destructive text-destructive-foreground rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))}
              {photos.length < 2 && (
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploadingPhotos}
                  className="w-24 h-24 rounded-xl border-2 border-dashed border-border flex flex-col items-center justify-center gap-1 text-muted-foreground hover:border-primary hover:text-primary transition-colors"
                >
                  {uploadingPhotos ? <Loader2 size={20} className="animate-spin" /> : <Upload size={20} />}
                  <span className="text-xs">{uploadingPhotos ? 'Uploading' : 'Add photo'}</span>
                </button>
              )}
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={handlePhotoUpload}
                className="hidden"
              />
            </div>
            <p className="text-xs text-muted-foreground mt-2">Upload up to 2 photos (JPG, PNG, or WebP, max 5MB each)</p>
          </CardContent>
        </Card>

        <div className="flex items-center gap-2">
          {SECTIONS.map((s, i) => (
            <div key={s.key} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= safeStep ? 'bg-primary' : 'bg-muted'}`} />
          ))}
        </div>
        <p className="text-sm text-muted-foreground">
          Step {safeStep + 1} of {SECTIONS.length} · Saves when you go to next or previous step
          {saveMutation.isPending && <span className="ml-2 text-xs text-muted-foreground">Saving…</span>}
        </p>

        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.2 }}>
            <Card className="border-0 shadow-card">
              <CardHeader>
                <CardTitle className="font-display text-xl">{section.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                {section.fields.map((f: { key: string; label: string; type: string; required?: boolean; placeholder?: string; options?: string[]; min?: number; max?: number; default?: number }) => (
                  <div key={f.key} className="space-y-1.5">
                    <Label className="text-sm">
                      {f.label} {f.required && <span className="text-destructive">*</span>}
                    </Label>
                    {f.type === 'text' && (
                      <Input
                        {...form.register(`${section.key}.${f.key}`)}
                        placeholder={f.placeholder}
                      />
                    )}
                    {f.type === 'textarea' && (
                      <Textarea
                        {...form.register(`${section.key}.${f.key}`)}
                        placeholder={f.placeholder}
                        rows={3}
                      />
                    )}
                    {f.type === 'number' && (
                      <Input
                        type="number"
                        min={f.min}
                        max={f.max}
                        {...form.register(`${section.key}.${f.key}`, { valueAsNumber: true })}
                      />
                    )}
                    {f.type === 'select' && (
                      <Controller
                        name={`${section.key}.${f.key}` as const}
                        control={control}
                        render={({ field }) => (
                          <Select value={typeof field.value === 'string' ? field.value : ''} onValueChange={field.onChange}>
                            <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
                            <SelectContent>
                              {(f.options || []).map((o: string) => (
                                <SelectItem key={o} value={o}>{o}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        )}
                      />
                    )}
                    {f.type === 'slider' && (
                      <Controller
                        name={`${section.key}.${f.key}` as const}
                        control={control}
                        render={({ field }) => (
                          <div className="flex items-center gap-4">
                            <Slider
                              min={f.min}
                              max={f.max}
                              step={1}
                              value={[Number(field.value) ?? f.default ?? f.min]}
                              onValueChange={([v]) => field.onChange(v)}
                              className="flex-1"
                            />
                            <span className="w-8 text-center font-semibold">{Number(field.value) ?? f.default ?? f.min}</span>
                          </div>
                        )}
                      />
                    )}
                    {f.type === 'multiselect' && (
                      <Controller
                        name={`${section.key}.${f.key}` as const}
                        control={control}
                        render={({ field }) => {
                          const arr = Array.isArray(field.value) ? field.value : [];
                          const maxSelect = (f as { max?: number }).max;
                          return (
                            <div className="flex flex-wrap gap-2">
                              {(f.options || []).map((o: string) => {
                                const checked = arr.includes(o);
                                return (
                                  <label
                                    key={o}
                                    className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 ${
                                      checked ? 'border-primary bg-accent text-accent-foreground' : 'border-border hover:bg-muted'
                                    }`}
                                  >
                                    <Checkbox
                                      checked={checked}
                                      onCheckedChange={(checked) => {
                                        if (checked) {
                                          if (maxSelect != null && arr.length >= maxSelect) return;
                                          field.onChange([...arr, o]);
                                        } else {
                                          field.onChange(arr.filter(x => x !== o));
                                        }
                                      }}
                                    />
                                    <span className="pointer-events-none">{o}</span>
                                  </label>
                                );
                              })}
                            </div>
                          );
                        }}
                      />
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </AnimatePresence>

        <div className="flex justify-between">
          <Button type="button" variant="outline" onClick={prev} disabled={step === 0}>
            <ChevronLeft size={16} /> Back
          </Button>
          {step < SECTIONS.length - 1 ? (
            <Button type="button" onClick={next}>
              Next <ChevronRight size={16} />
            </Button>
          ) : (
            <Button type="button" onClick={onFinish} className="gap-2" disabled={isFinishing}>
              {isFinishing ? (
                <>
                  <Loader2 size={16} className="animate-spin" /> Saving…
                </>
              ) : (
                <>
                  <Check size={16} /> Save & finish
                </>
              )}
            </Button>
          )}
        </div>
      </div>

      {/* Agent updating overlay */}
      <AnimatePresence>
        {showAgentOverlay && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-card rounded-2xl shadow-elevated p-8 text-center max-w-sm mx-4"
            >
              <div className="mx-auto w-16 h-16 rounded-full bg-primary/10 flex items-center justify-center mb-4">
                <Bot size={32} className="text-primary animate-pulse" />
              </div>
              <h3 className="font-display text-xl font-bold mb-2">Updating Your AI Agent</h3>
              <p className="text-muted-foreground text-sm">
                Your clone is being updated with your latest preferences. This will only take a moment...
              </p>
              <div className="mt-4 flex justify-center">
                <Loader2 size={24} className="animate-spin text-primary" />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </AppLayout>
  );
}
