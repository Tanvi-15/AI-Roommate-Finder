import { useState } from 'react';
import { useAuth } from '@/contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '@/components/AppLayout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Slider } from '@/components/ui/slider';
import { Textarea } from '@/components/ui/textarea';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, ChevronRight, Check } from 'lucide-react';
import { toast } from 'sonner';

type Q = Record<string, any>;

const SECTIONS = [
  {
    key: 'living', title: '🏡 Living Preferences', fields: [
      { key: 'location', label: 'City/area', type: 'text', required: true, placeholder: 'e.g. Boston, Cambridge' },
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

export default function QuestionnairePage() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [data, setData] = useState<Q>(() => {
    const q = user?.questionnaire || {};
    const init: Q = {};
    SECTIONS.forEach(s => { init[s.key] = q[s.key] || {}; });
    return init;
  });

  const section = SECTIONS[step];
  const sectionData = data[section.key] || {};

  const updateField = (key: string, value: any) => {
    setData(prev => ({
      ...prev,
      [section.key]: { ...prev[section.key], [key]: value },
    }));
  };

  const toggleMulti = (key: string, value: string, max?: number) => {
    const sectionKey = section.key;
    setData(prev => {
      const raw = (prev[sectionKey] || {})[key];
      const current: string[] = Array.isArray(raw) ? [...raw] : [];
      if (current.includes(value)) {
        return { ...prev, [sectionKey]: { ...prev[sectionKey], [key]: current.filter(v => v !== value) } };
      }
      const maxNum = max != null ? Number(max) : undefined;
      if (maxNum != null && current.length >= maxNum) return prev;
      return { ...prev, [sectionKey]: { ...prev[sectionKey], [key]: [...current, value] } };
    });
  };

  const validate = () => {
    for (const f of section.fields) {
      if (!(f as any).required) continue;
      const v = sectionData[f.key];
      if (f.type === 'multiselect') {
        const arr = Array.isArray(v) ? v : [];
        if (arr.length === 0) { toast.error(`${f.label} is required`); return false; }
      } else if (v === undefined || v === '') {
        toast.error(`${f.label} is required`); return false;
      }
    }
    if (section.key === 'living') {
      const min = Number(sectionData.budget_min);
      const max = Number(sectionData.budget_max);
      if (min && max && min > max) { toast.error('Min budget must be ≤ Max budget'); return false; }
    }
    return true;
  };

  const next = () => { if (validate()) setStep(s => Math.min(s + 1, SECTIONS.length - 1)); };
  const prev = () => setStep(s => Math.max(s - 1, 0));

  const finish = () => {
    if (!validate()) return;
    const updatedUser = { ...user!, questionnaire: data };
    setUser(updatedUser);
    toast.success('Profile saved!');
    navigate('/');
  };

  const renderField = (f: any) => {
    const val = sectionData[f.key];
    switch (f.type) {
      case 'text':
        return <Input value={val || ''} onChange={e => updateField(f.key, e.target.value)} placeholder={f.placeholder} />;
      case 'textarea':
        return <Textarea value={val || ''} onChange={e => updateField(f.key, e.target.value)} placeholder={f.placeholder} rows={3} />;
      case 'number':
        return <Input type="number" value={val ?? f.default ?? ''} onChange={e => updateField(f.key, e.target.value)} min={f.min} max={f.max} />;
      case 'select':
        return (
          <Select value={val || ''} onValueChange={v => updateField(f.key, v)}>
            <SelectTrigger><SelectValue placeholder="Select…" /></SelectTrigger>
            <SelectContent>
              {f.options.map((o: string) => <SelectItem key={o} value={o}>{o}</SelectItem>)}
            </SelectContent>
          </Select>
        );
      case 'slider':
        return (
          <div className="flex items-center gap-4">
            <Slider
              value={[val ?? f.default ?? f.min]}
              onValueChange={([v]) => updateField(f.key, v)}
              min={f.min} max={f.max} step={1}
              className="flex-1"
            />
            <span className="w-8 text-center font-semibold">{val ?? f.default ?? f.min}</span>
          </div>
        );
      case 'multiselect': {
        const multiVal = Array.isArray(val) ? val : [];
        return (
          <div className="flex flex-wrap gap-2">
            {f.options.map((o: string) => {
              const checked = multiVal.includes(o);
              return (
                <button
                  key={o}
                  type="button"
                  className={`flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2 text-sm transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 ${
                    checked ? 'border-primary bg-accent text-accent-foreground' : 'border-border hover:bg-muted'
                  }`}
                  onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleMulti(f.key, o, f.max); }}
                >
                  <span className={`flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border ${checked ? 'border-primary bg-primary text-primary-foreground' : 'border-muted-foreground'}`}>
                    {checked ? <Check className="h-3 w-3" /> : null}
                  </span>
                  {o}
                </button>
              );
            })}
          </div>
        );
      }
      default:
        return null;
    }
  };

  return (
    <AppLayout>
      <div className="mx-auto max-w-2xl space-y-6">
        {/* Progress */}
        <div className="flex items-center gap-2">
          {SECTIONS.map((s, i) => (
            <div key={s.key} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
          ))}
        </div>
        <p className="text-sm text-muted-foreground">Step {step + 1} of {SECTIONS.length}</p>

        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{ opacity: 0, x: 30 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -30 }} transition={{ duration: 0.2 }}>
            <Card className="border-0 shadow-card">
              <CardHeader>
                <CardTitle className="font-display text-xl">{section.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-5">
                {section.fields.map(f => (
                  <div key={f.key} className="space-y-1.5">
                    <Label className="text-sm">
                      {f.label} {f.required && <span className="text-destructive">*</span>}
                    </Label>
                    {renderField(f)}
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>
        </AnimatePresence>

        <div className="flex justify-between">
          <Button variant="outline" onClick={prev} disabled={step === 0}>
            <ChevronLeft size={16} /> Back
          </Button>
          {step < SECTIONS.length - 1 ? (
            <Button onClick={next}>
              Next <ChevronRight size={16} />
            </Button>
          ) : (
            <Button onClick={finish} className="gap-2">
              <Check size={16} /> Save Profile
            </Button>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
