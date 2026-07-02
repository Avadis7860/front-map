import { ButtonHTMLAttributes } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost'
}

/** Bouton — action primaire (convention dir-scan, `export default`, `type Props`). */
export default function Button({ variant = 'primary', ...props }: Props) {
  return <button data-variant={variant} {...props} />
}
