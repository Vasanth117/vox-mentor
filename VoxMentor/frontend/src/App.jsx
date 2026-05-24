import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Sidebar from './components/Sidebar';
import AuthPage from './pages/AuthPage';
import Dashboard from './pages/Dashboard';
import Chat from './pages/Chat';
import Playground from './pages/Playground';
import Visualizer from './pages/Visualizer';
import ProgressPage from './pages/ProgressPage';
import SkillTree from './pages/SkillTree';
import Practice from './pages/Practice';
import Journal from './pages/Journal';
import Settings from './pages/Settings';
import LearningPlus from './pages/LearningPlus';
import MockInterviews from './pages/MockInterviews';
import SystemStatusBanner from './components/SystemStatusBanner';
import './index.css';

function ProtectedLayout() {
  const { user, loading } = useAuth();
  if (loading) return (
    <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh', flexDirection:'column', gap:16 }}>
      <div className="spinner spinner-lg" />
      <p style={{ color:'var(--text-muted)' }}>Loading VoxMentor…</p>
    </div>
  );
  if (!user) return <Navigate to="/auth" replace />;
  return (
    <div className="app-layout">
      <Sidebar />
      <main className="main-content">
        <SystemStatusBanner />
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/chat"       element={<Chat />} />
          <Route path="/playground" element={<Playground />} />
          <Route path="/visualizer" element={<Visualizer />} />
          <Route path="/progress"   element={<ProgressPage />} />
          <Route path="/skill-tree" element={<SkillTree />} />
          <Route path="/practice"   element={<Practice />} />
          <Route path="/journal"    element={<Journal />} />
          <Route path="/learning-plus" element={<LearningPlus />} />
          <Route path="/mock-interviews" element={<MockInterviews />} />
          <Route path="/settings"   element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/auth" element={<><SystemStatusBanner /><AuthPage /></>} />
          <Route path="/*"   element={<ProtectedLayout />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
