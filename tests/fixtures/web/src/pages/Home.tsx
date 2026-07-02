import { Badge, Button } from '@/components/ui'
import { greet } from '@/lib/util'

// Écran d'accueil (fixture) — consomme Button + Badge et un token accent littéral.
export function Home() {
  return (
    <div style={{ color: 'var(--color-accent-500)' }}>
      <Button variant="primary">{greet()}</Button>
      <Badge label="ok" />
    </div>
  )
}
