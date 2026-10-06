import { createRootRoute, createRoute, createRouter, Outlet } from '@tanstack/react-router'
import { AppShell } from './ui/app-shell'
import { DashboardPage } from './pages/dashboard-page'
import { DestinationsPage } from './pages/destinations-page'
import { JobDetailPage } from './pages/job-detail-page'
import { MailPage } from './pages/mail-page'
import { LogsPage } from './pages/logs-page'
import { SystemLogsPage } from './pages/system-logs-page'
import { SettingsPage } from './pages/settings-page'

const rootRoute = createRootRoute({ component: () => <AppShell><Outlet /></AppShell> })
const dashboardRoute = createRoute({ getParentRoute: () => rootRoute, path: '/', component: DashboardPage })
const mailRoute = createRoute({ getParentRoute: () => rootRoute, path: '/mail', component: MailPage })
const jobDetailRoute = createRoute({ getParentRoute: () => rootRoute, path: '/mail/$jobId', component: JobDetailPage })
const destinationsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/destinations', component: DestinationsPage })
const logsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/logs', component: LogsPage })
const systemLogsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/system-logs', component: SystemLogsPage })
const settingsRoute = createRoute({ getParentRoute: () => rootRoute, path: '/settings', component: SettingsPage })

const routeTree = rootRoute.addChildren([dashboardRoute, mailRoute, jobDetailRoute, destinationsRoute, logsRoute, systemLogsRoute, settingsRoute])
export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
