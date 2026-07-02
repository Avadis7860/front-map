import { Outlet } from '@tanstack/react-router'

// Shell racine (fixture) — ne consomme NI primitive NI token → doit être omis de usage.
export function AppShell() {
  return <Outlet />
}
