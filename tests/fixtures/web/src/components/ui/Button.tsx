import type { ButtonHTMLAttributes } from 'react'

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger'
type Size = 'sm' | 'md'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  busy?: boolean
}

// Bouton d'action primaire du design-system.
export function Button({ variant = 'secondary', size = 'md', busy = false, children }: ButtonProps) {
  return <button data-variant={variant} data-size={size} disabled={busy}>{children}</button>
}
