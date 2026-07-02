import { Badge } from '@/components/ui'

// Panneau Gate (fixture) — consomme Badge + un token danger littéral.
export function GatePanel() {
  return (
    <span style={{ borderColor: 'var(--color-danger-500)' }}>
      <Badge tone="danger" label="gate" />
    </span>
  )
}
