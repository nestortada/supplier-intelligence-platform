import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom'
import AppShell from './components/AppShell'
import ProfileProvider from './components/ProfileProvider'
import ToastProvider from './components/ToastProvider'
import { useProfile } from './hooks/useProfile'
import DashboardPage from './pages/DashboardPage'
import EmailCampaignsPage from './pages/EmailCampaignsPage'
import ProductAnalysisDetailPage from './pages/ProductAnalysisDetailPage'
import OpportunityRankingPage from './pages/OpportunityRankingPage'
import ProfileSelectionPage from './pages/ProfileSelectionPage'
import SettingsPage from './pages/SettingsPage'

function ProtectedShell() {
  const { activeProfile, loading } = useProfile()

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-6 text-muted">
        Cargando perfiles
      </div>
    )
  }

  if (!activeProfile) {
    return <Navigate replace to="/profiles" />
  }

  return (
    <AppShell>
      <Routes>
        <Route element={<Navigate replace to="/dashboard" />} path="/" />
        <Route element={<DashboardPage />} path="/dashboard" />
        <Route element={<EmailCampaignsPage />} path="/emails" />
        <Route element={<OpportunityRankingPage />} path="/ranking" />
        <Route element={<ProductAnalysisDetailPage />} path="/ranking/:productId" />
        <Route element={<SettingsPage />} path="/settings" />
        <Route element={<Navigate replace to="/emails" />} path="*" />
      </Routes>
    </AppShell>
  )
}

function App() {
  return (
    <ToastProvider>
      <Router>
        <ProfileProvider>
          <Routes>
            <Route element={<ProfileSelectionPage />} path="/profiles" />
            <Route element={<ProtectedShell />} path="/*" />
          </Routes>
        </ProfileProvider>
      </Router>
    </ToastProvider>
  )
}

export default App
