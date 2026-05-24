import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  Home, MessageSquare, Code2, BarChart3, GitBranch, Dumbbell,
  BookOpen, Settings, Cpu, LogOut, Zap, Route, Timer
} from 'lucide-react';

const NAV = [
  { label: 'Dashboard',   to: '/',           icon: Home },
  { label: 'AI Tutor',    to: '/chat',        icon: MessageSquare },
  { label: 'Playground',  to: '/playground',  icon: Code2 },
  { label: 'Visualizer',  to: '/visualizer',  icon: Cpu },
];
const LEARN_NAV = [
  { label: 'Practice',    to: '/practice',    icon: Dumbbell },
  { label: 'Skill Tree',  to: '/skill-tree',  icon: GitBranch },
  { label: 'Learning+',   to: '/learning-plus', icon: Route },
  { label: 'Mock Interviews', to: '/mock-interviews', icon: Timer },
  { label: 'Progress',    to: '/progress',    icon: BarChart3 },
  { label: 'Journal',     to: '/journal',     icon: BookOpen },
];

export default function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => { logout(); navigate('/auth'); };

  const initials = user?.name?.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase() || 'VM';

  return (
    <nav className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-text">VoxMentor</div>
        <div className="logo-sub">AI Coding Tutor</div>
      </div>

      {/* Main Nav */}
      <div className="nav-section">
        <div className="nav-label">Main</div>
        {NAV.map(({ label, to, icon: Icon }) => ( // eslint-disable-line no-unused-vars
          <NavLink key={to} to={to}
            end={to === '/'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon className="nav-icon" />
            {label}
          </NavLink>
        ))}
      </div>

      {/* Learn Nav */}
      <div className="nav-section">
        <div className="nav-label">Learn</div>
        {LEARN_NAV.map(({ label, to, icon: Icon }) => ( // eslint-disable-line no-unused-vars
          <NavLink key={to} to={to}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Icon className="nav-icon" />
            {label}
          </NavLink>
        ))}
      </div>

      {/* Settings */}
      <div className="nav-section">
        <NavLink to="/settings"
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
        >
          <Settings className="nav-icon" />
          Settings
        </NavLink>
      </div>

      {/* Footer */}
      <div className="sidebar-footer">
        {user && (
          <div className="user-chip">
            <div className="avatar">{initials}</div>
            <div className="user-info" style={{ flex: 1, minWidth: 0 }}>
              <div className="user-name" style={{ overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap' }}>
                {user.name}
              </div>
              <div className="user-level">
                <Zap size={10} style={{ display:'inline', marginRight:3 }} />
                {user.xp || 0} XP
              </div>
            </div>
            <button onClick={handleLogout} className="btn btn-ghost btn-icon"
              style={{ color:'var(--text-muted)' }} title="Logout">
              <LogOut size={15} />
            </button>
          </div>
        )}
      </div>
    </nav>
  );
}
