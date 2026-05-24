import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, Globe, Brain, Target, Volume2, Code2, Save, LogOut, Zap } from 'lucide-react';

const SKILL_LEVELS = ['beginner', 'intermediate', 'advanced'];
const LANGUAGES    = [
  { value: 'english', label: 'English 🇬🇧' },
  { value: 'tamil',   label: 'Tamil 🇮🇳' },
  { value: 'hindi',   label: 'Hindi 🇮🇳' },
];
const CAREER_GOALS = [
  'Web Developer', 'Software Engineer', 'Data Scientist', 'AI/ML Engineer',
  'Backend Developer', 'Frontend Developer', 'Mobile Developer', 'DevOps Engineer', 'Other',
];
const AI_STYLES = [
  { id: 'structured', label: '📚 Structured', desc: 'Step-by-step explanations with clear sections' },
  { id: 'conversational', label: '💬 Conversational', desc: 'Casual, chat-like responses' },
  { id: 'socratic', label: '🤔 Socratic', desc: 'AI asks questions to guide you' },
];

function SettingSection({ icon, title, children }) {
  const Icon = icon;
  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 'var(--radius-md)',
          background: 'rgba(0,212,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={18} color="var(--accent-cyan)" />
        </div>
        <h3 style={{ fontSize: '0.95rem', fontWeight: 700 }}>{title}</h3>
      </div>
      {children}
    </div>
  );
}

export default function Settings() {
  const { user, logout, updateUser } = useAuth();
  const [form, setForm] = useState({
    skill_level:        user?.skill_level        || 'beginner',
    preferred_language: user?.preferred_language || 'english',
    career_goal:        user?.career_goal        || '',
    ai_style:           user?.ai_style           || 'structured',
    voice_enabled:      user?.voice_enabled      ?? true,
  });
  const [saving, setSaving] = useState(false);
  const [saved,  setSaved]  = useState(false);

  const set = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      // Persist locally (backend update optional — user router can be extended)
      if (updateUser) updateUser({ ...user, ...form });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch {}
    setSaving(false);
  };

  const handleLogout = () => logout();

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Settings</h1>
        <p className="page-subtitle">Personalise your VoxMentor experience</p>
      </div>

      {/* Profile info */}
      <div className="card card-glow" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{
          width: 56, height: 56, borderRadius: '50%', background: 'var(--grad-primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          fontSize: '1.4rem', fontWeight: 800, color: '#fff',
        }}>
          {user?.name?.slice(0, 2).toUpperCase() || 'VM'}
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>{user?.name}</div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{user?.email}</div>
          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <span className="badge badge-cyan"><Zap size={9} /> {user?.xp || 0} XP</span>
            <span className="badge badge-violet">{user?.skill_level || 'Beginner'}</span>
          </div>
        </div>
      </div>

      <form onSubmit={handleSave}>
        {/* Learning preferences */}
        <SettingSection icon={Brain} title="Learning Preferences">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Skill Level</span>
              <select className="input select" value={form.skill_level} onChange={e => set('skill_level', e.target.value)}>
                {SKILL_LEVELS.map(l => <option key={l} value={l}>{l.charAt(0).toUpperCase() + l.slice(1)}</option>)}
              </select>
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 500 }}>Career Goal</span>
              <select className="input select" value={form.career_goal} onChange={e => set('career_goal', e.target.value)}>
                <option value="">Select goal…</option>
                {CAREER_GOALS.map(g => <option key={g} value={g}>{g}</option>)}
              </select>
            </label>
          </div>
        </SettingSection>

        {/* Language */}
        <SettingSection icon={Globe} title="Language">
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {LANGUAGES.map(({ value, label }) => (
              <button key={value} type="button"
                onClick={() => set('preferred_language', value)}
                style={{
                  padding: '10px 18px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                  background: form.preferred_language === value ? 'rgba(0,212,255,0.1)' : 'var(--bg-secondary)',
                  border: `1px solid ${form.preferred_language === value ? 'var(--accent-cyan)' : 'var(--border)'}`,
                  color: form.preferred_language === value ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  fontWeight: 600, fontSize: '0.85rem', transition: 'var(--transition)',
                }}
              >{label}</button>
            ))}
          </div>
        </SettingSection>

        {/* AI Teaching Style */}
        <SettingSection icon={Brain} title="AI Teaching Style">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {AI_STYLES.map(s => (
              <button key={s.id} type="button"
                onClick={() => set('ai_style', s.id)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px',
                  background: form.ai_style === s.id ? 'rgba(0,212,255,0.08)' : 'var(--bg-secondary)',
                  border: `1px solid ${form.ai_style === s.id ? 'var(--accent-cyan)' : 'var(--border)'}`,
                  borderRadius: 'var(--radius-md)', cursor: 'pointer', textAlign: 'left',
                  transition: 'var(--transition)',
                }}
              >
                <div style={{
                  width: 18, height: 18, borderRadius: '50%', flexShrink: 0,
                  background: form.ai_style === s.id ? 'var(--accent-cyan)' : 'var(--border)',
                  border: `2px solid ${form.ai_style === s.id ? 'var(--accent-cyan)' : 'var(--border)'}`,
                }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.875rem', color: form.ai_style === s.id ? 'var(--text-primary)' : 'var(--text-secondary)' }}>{s.label}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>{s.desc}</div>
                </div>
              </button>
            ))}
          </div>
        </SettingSection>

        {/* Voice */}
        <SettingSection icon={Volume2} title="Voice Interaction">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.875rem' }}>Enable Voice Features</div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: 2 }}>
                Use browser Speech API for voice input and text-to-speech output
              </div>
            </div>
            <button type="button"
              onClick={() => set('voice_enabled', !form.voice_enabled)}
              style={{
                width: 52, height: 28, borderRadius: 99, cursor: 'pointer', flexShrink: 0,
                background: form.voice_enabled ? 'var(--accent-cyan)' : 'var(--bg-secondary)',
                border: `2px solid ${form.voice_enabled ? 'var(--accent-cyan)' : 'var(--border)'}`,
                position: 'relative', transition: 'var(--transition)',
              }}
            >
              <div style={{
                width: 20, height: 20, borderRadius: '50%', background: '#fff',
                position: 'absolute', top: 2,
                left: form.voice_enabled ? 28 : 2, transition: 'var(--transition)',
              }} />
            </button>
          </div>
        </SettingSection>

        {/* Save */}
        <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
          <button type="button" className="btn btn-secondary"
            onClick={handleLogout} style={{ gap: 8, color: '#f87171' }}>
            <LogOut size={16} />Logout
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving} style={{ minWidth: 140, justifyContent: 'center' }}>
            {saving ? <div className="spinner" style={{ width: 16, height: 16 }} />
              : saved ? '✓ Saved!' : <><Save size={16} />Save Settings</>}
          </button>
        </div>
      </form>
    </div>
  );
}
