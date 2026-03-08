import { cva } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold tracking-wide',
  {
    variants: {
      status: {
        strong: 'bg-match-strong text-match-strong-foreground',
        conditional: 'bg-match-conditional text-match-conditional-foreground',
        incompatible: 'bg-match-incompatible text-match-incompatible-foreground',
      },
    },
  }
);

const labels: Record<string, string> = {
  strong: 'Strong Match',
  conditional: 'Conditional Match',
  incompatible: 'Incompatible',
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  return (
    <span className={cn(badgeVariants({ status: status as any }), className)}>
      {labels[status] || status}
    </span>
  );
}
