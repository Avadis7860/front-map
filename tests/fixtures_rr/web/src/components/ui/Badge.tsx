/** Badge de statut (props inline anonymes → détail props best-effort). */
export default function Badge({ tone }: { tone: 'ok' | 'bad' }) {
  return <span data-tone={tone} />
}
