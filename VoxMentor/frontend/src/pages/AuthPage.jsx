import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { Navigate, useNavigate } from 'react-router-dom';
import { Mail, Lock, User, BookOpen, Target, Code, Eye, EyeOff } from 'lucide-react';
import './AuthPage.css';

export default function AuthPage() {
  const { user, login, register } = useAuth();
  const navigate = useNavigate();
  const [isRightPanelActive, setIsRightPanelActive] = useState(false);
  
  // separate loadings
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  const [loginForm, setLoginForm] = useState({ email: '', password: '' });
  const [regForm, setRegForm] = useState({
    name: '', email: '', password: '', 
    skill_level: 'beginner', preferred_language: 'english', career_goal: ''
  });

  const [showLoginPassword, setShowLoginPassword] = useState(false);
  const [showRegPassword, setShowRegPassword] = useState(false);

  // Clear errors when switching panels
  useEffect(() => {
    setError('');
  }, [isRightPanelActive]);

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError(''); 
    setLoading(true);
    try {
      await login(loginForm.email, loginForm.password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Invalid credentials');
    } finally { 
      setLoading(false); 
    }
  };

  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    setError(''); 
    setLoading(true);
    try {
      await register(regForm);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err?.response?.data?.detail || 'Registration failed');
    } finally { 
      setLoading(false); 
    }
  };

  if (user) return <Navigate to="/" replace />;

  return (
    <div className="auth-wrapper">
      <div className={`auth-container ${isRightPanelActive ? 'right-panel-active' : ''}`}>
        
        {/* Sign Up Container - Left panel but slides right when active */}
        <div className="form-container sign-up-container">
          <form className="auth-form" onSubmit={handleRegisterSubmit}>
            <h1 className="auth-title">Create Account</h1>
            
            <span className="auth-helper-text">Use your email for registration</span>
            
            <div className="auth-input-group">
              <User className="auth-input-icon" size={18} />
              <input type="text" className="auth-input" placeholder="Name" required 
                value={regForm.name} onChange={e => setRegForm({...regForm, name: e.target.value})} />
            </div>

            <div className="auth-input-group">
              <Mail className="auth-input-icon" size={18} />
              <input type="email" className="auth-input" placeholder="Email" required 
                value={regForm.email} onChange={e => setRegForm({...regForm, email: e.target.value})} />
            </div>

            <div className="auth-input-group">
              <Lock className="auth-input-icon" size={18} />
              <input type={showRegPassword ? "text" : "password"} className="auth-input" placeholder="Password" required 
                value={regForm.password} onChange={e => setRegForm({...regForm, password: e.target.value})} />
              <div className="password-toggle" onClick={() => setShowRegPassword(!showRegPassword)}>
                {showRegPassword ? <EyeOff size={18}/> : <Eye size={18}/>}
              </div>
            </div>
            
            <div className="auth-input-group">
              <BookOpen className="auth-input-icon" size={18} />
              <select className="auth-input select" value={regForm.skill_level}
                onChange={e => setRegForm({...regForm, skill_level: e.target.value})}>
                <option value="beginner">Beginner</option>
                <option value="intermediate">Intermediate</option>
                <option value="advanced">Advanced</option>
              </select>
            </div>

            <div className="auth-input-group">
              <Code className="auth-input-icon" size={18} />
              <select className="auth-input select" value={regForm.preferred_language}
                onChange={e => setRegForm({...regForm, preferred_language: e.target.value})}>
                <option value="english">English 🇬🇧</option>
                <option value="tamil">Tamil 🇮🇳</option>
                <option value="hindi">Hindi 🇮🇳</option>
              </select>
            </div>

            <div className="auth-input-group">
              <Target className="auth-input-icon" size={18} />
              <input type="text" className="auth-input" placeholder="Career Goal (e.g. Web Dev)" 
                value={regForm.career_goal} onChange={e => setRegForm({...regForm, career_goal: e.target.value})} />
            </div>

            {isRightPanelActive && error && <div className="auth-error">{error}</div>}

            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Processing...' : 'Sign Up'}
            </button>
            <button type="button" className="mobile-switch" onClick={() => setIsRightPanelActive(false)}>
              Already have an account? <span>Sign In</span>
            </button>
          </form>
        </div>

        {/* Sign In Container - Right panel but slides left when active */}
        <div className="form-container sign-in-container">
          <form className="auth-form" onSubmit={handleLoginSubmit}>
            <h1 className="auth-title">Sign In</h1>
            
            <span className="auth-helper-text">Use your email account</span>
            
            <div className="auth-input-group">
              <Mail className="auth-input-icon" size={18} />
              <input type="email" className="auth-input" placeholder="Email" required 
                value={loginForm.email} onChange={e => setLoginForm({...loginForm, email: e.target.value})} />
            </div>
            
            <div className="auth-input-group">
              <Lock className="auth-input-icon" size={18} />
              <input type={showLoginPassword ? "text" : "password"} className="auth-input" placeholder="Password" required 
                value={loginForm.password} onChange={e => setLoginForm({...loginForm, password: e.target.value})} />
              <div className="password-toggle" onClick={() => setShowLoginPassword(!showLoginPassword)}>
                {showLoginPassword ? <EyeOff size={18}/> : <Eye size={18}/>}
              </div>
            </div>
            
            <button type="button" className="auth-forgot">Forgot your password?</button>
            
            {!isRightPanelActive && error && <div className="auth-error">{error}</div>}

            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Processing...' : 'Sign In'}
            </button>
            
            <button type="button" className="mobile-switch" onClick={() => setIsRightPanelActive(true)}>
              Don't have an account? <span>Sign Up</span>
            </button>
          </form>
        </div>

        {/* Overlay Container */}
        <div className="overlay-container">
          <div className="overlay">
            
            <div className="overlay-panel overlay-left">
              <h1 className="overlay-heading">Welcome Back!</h1>
              <p className="overlay-desc">To keep connected with us please login with your personal info</p>
              <button className="overlay-btn" onClick={() => setIsRightPanelActive(false)}>Sign In</button>
            </div>
            
            <div className="overlay-panel overlay-right">
              <h1 className="overlay-heading">Hello, Friend!</h1>
              <p className="overlay-desc">Enter your personal details and start your journey with VoxMentor</p>
              <button className="overlay-btn" onClick={() => setIsRightPanelActive(true)}>Sign Up</button>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
