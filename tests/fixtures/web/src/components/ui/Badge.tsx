type Tone = 'ok' | 'warn' | 'danger'

export interface BadgeProps {
  tone?: Tone
  label: string
}

// Badge de statut coloré.
export function Badge({ tone = 'ok', label }: BadgeProps) {
  return <span data-tone={tone}>{label}</span>
}
