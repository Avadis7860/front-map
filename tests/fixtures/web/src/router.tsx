import { createRootRoute, createRoute, createRouter } from '@tanstack/react-router'
import { AppShell } from './App'
import { Home } from './pages/Home'
import { Workspace } from './pages/Workspace'
import { GatePanel } from './pages/GatePanel'

const rootRoute = createRootRoute({ component: AppShell })
const indexRoute = createRoute({ getParentRoute: () => rootRoute, path: '/', component: Home })
const wsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/$project', component: Workspace })
const gateRoute = createRoute({ getParentRoute: () => wsRoute, path: 'gate', component: GatePanel })

export const router = createRouter({
  routeTree: rootRoute.addChildren([indexRoute, wsRoute.addChildren([gateRoute])]),
})
