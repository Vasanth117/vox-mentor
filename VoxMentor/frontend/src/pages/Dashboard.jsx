import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getProgress, getDailyChallenge } from '../api';
import { MessageSquare, Code2, Cpu, BarChart3, GitBranch, Dumbbell, Zap, Flame, Trophy, Clock } from 'lucide-react';

const QUICK_ACTIONS = [
  { label: 'Ask AI Tutor', icon: MessageSquare, to: '/chat', color: 'var(--accent-cyan)' },
  { label: 'Code Now',     icon: Code2, to: '/playground', color: 'var(--accent-green)' },
  { label: 'Visualize',   icon: Cpu, to: '/visualizer', color: 'var(--accent-violet)' },
  { label: 'Practice',    icon: Dumbbell, to: '/practice', color: 'var(--accent-orange)' },
];

const BADGE_NAMES = {
  first_session: 'First Steps 👶',
  streak_3:      '3-Day Flame 🔥',
  streak_7:      'Week Warrior ⚔️',
  streak_30:     'Monthly Master 🏆',
  xp_500:        'XP Hunter 💎',
  xp_1000:       'XP Champion 🥇',
  debugger:      'Bug Slayer 🐛',
  speed_coder:   'Speed Coder ⚡',
};

function StatCard({ icon, value, label, color, suffix = '' }) {
  const Icon = icon;
  return (
    <div className="card" style={{ display:'flex', alignItems:'center', gap:16 }}>
      <div style={{
        width:48, height:48, borderRadius:'var(--radius-md)', flexShrink:0,
        background: `${color}22`, display:'flex', alignItems:'center', justifyContent:'center',
      }}>
        <Icon size={22} color={color} />
      </div>
      <div>
        <div className="stat-value" style={{ color }}>
          {value}{suffix}
        </div>
        <div className="stat-label">{label}</div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [progress, setProgress] = useState(null);
  const [daily, setDaily] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.user_id) return;
    Promise.all([
      getProgress(user.user_id).catch(() => null),
      getDailyChallenge(user.user_id, 'python').catch(() => null),
    ]).then(([p, d]) => {
      setProgress(p?.data);
      setDaily(d?.data);
      setLoading(false);
    });
  }, [user?.user_id]);

  const xp    = progress?.total_xp ?? user?.xp ?? 0;
  const level = progress?.level ?? { level_name:'Novice', progress_pct: 0 };
  const streak = progress?.streak ?? user?.streak ?? 0;
  const sessions = progress?.total_sessions ?? 0;
  const timeMin = Math.round(progress?.total_time_minutes ?? 0);

  return (
    <div className="fade-in">
      {/* Header */}
      <div style={{ marginBottom:32 }}>
        <h1 style={{ fontSize:'1.75rem', fontWeight:800 }}>
          Welcome back, <span className="gradient-text">{user?.name?.split(' ')[0]}</span> 👋
        </h1>
        <p style={{ color:'var(--text-muted)', marginTop:4 }}>
          {new Date().toLocaleDateString('en-US',{weekday:'long',month:'long',day:'numeric'})}
        </p>
      </div>

      {/* Level XP bar */}
      <div className="card card-glow" style={{ marginBottom:24, padding:'18px 24px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:10 }}>
          <div>
            <span className="badge badge-violet" style={{ marginBottom:6 }}>{level.level_name}</span>
            <div style={{ fontWeight:700, fontSize:'1rem', marginTop:4 }}>Level {level.level ?? 0}</div>
          </div>
          <div style={{ textAlign:'right' }}>
            <div style={{ fontWeight:800, fontSize:'1.5rem', color:'var(--accent-cyan)' }}>{xp} XP</div>
            <div style={{ fontSize:'0.75rem', color:'var(--text-muted)' }}>{level.progress_pct ?? 0}% to next level</div>
          </div>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width:`${level.progress_pct ?? 0}%` }} />
        </div>
      </div>

      {/* Stats row */}
      <div className="grid-4" style={{ marginBottom:24 }}>
        <StatCard icon={Flame} value={streak} label="Day Streak" color="var(--accent-orange)" />
        <StatCard icon={Zap} value={xp} label="Total XP" color="var(--accent-cyan)" />
        <StatCard icon={Trophy} value={sessions} label="Sessions" color="var(--accent-violet)" />
        <StatCard icon={Clock} value={timeMin} label="Minutes" color="var(--accent-green)" />
      </div>

      {/* Quick Actions */}
      <div style={{ marginBottom:24 }}>
        <h2 style={{ marginBottom:14, fontSize:'1rem', color:'var(--text-secondary)' }}>Quick Start</h2>
        <div className="grid-4">
          {QUICK_ACTIONS.map(({ label, icon, to, color }) => {
            const Icon = icon;
            return (
            <button key={to} onClick={() => navigate(to)}
              className="card" style={{
                cursor:'pointer', textAlign:'center', padding:'24px 16px', border:'none',
                background:'var(--bg-card)', transition:'var(--transition)',
              }}
              onMouseEnter={e => { e.currentTarget.style.transform='translateY(-4px)'; e.currentTarget.style.borderColor=color+'44'; }}
              onMouseLeave={e => { e.currentTarget.style.transform=''; e.currentTarget.style.borderColor=''; }}
            >
              <div style={{
                width:48, height:48, borderRadius:'var(--radius-md)',
                background: `${color}22`, display:'flex', alignItems:'center',
                justifyContent:'center', margin:'0 auto 12px',
              }}>
                <Icon size={22} color={color} />
              </div>
              <div style={{ fontWeight:600, fontSize:'0.875rem' }}>{label}</div>
            </button>
            );
          })}
        </div>
      </div>

      {/* Daily Challenge + Weak areas */}
      <div className="grid-2">
        {/* Daily Challenge */}
        <div className="card" style={{ borderColor:'rgba(249,115,22,0.2)' }}>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
            <h3>🎯 Daily Challenge</h3>
            {daily?.completed && <span className="badge badge-green">✓ Done</span>}
          </div>
          {daily?.challenge ? (
            <>
              <p style={{ fontWeight:600, color:'var(--text-primary)', marginBottom:8, fontSize:'0.9rem' }}>
                {daily.challenge.title}
              </p>
              <p style={{ fontSize:'0.82rem', marginBottom:16, lineClamp:2 }}>
                {daily.challenge.description?.slice(0, 120)}…
              </p>
              <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                <span className={`badge badge-${daily.challenge.difficulty==='beginner'?'green':daily.challenge.difficulty==='advanced'?'pink':'orange'}`}>
                  {daily.challenge.difficulty}
                </span>
                <button className="btn btn-primary" style={{ padding:'6px 14px', fontSize:'0.8rem' }}
                  onClick={() => navigate('/practice')}>
                  Solve Now
                </button>
              </div>
            </>
          ) : (
            <div style={{ color:'var(--text-muted)', fontSize:'0.85rem' }}>
              {loading ? 'Loading...' : 'Start your first session to get a daily challenge!'}
            </div>
          )}
        </div>

        {/* Weak Areas / Suggestions */}
        <div className="card">
          <h3 style={{ marginBottom:14 }}>💡 Suggested Topics</h3>
          {progress?.suggested_topics?.length > 0 ? (
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {progress.suggested_topics.slice(0, 4).map(topic => (
                <button key={topic}
                  onClick={() => navigate(`/chat?topic=${encodeURIComponent(topic)}`)}
                  style={{
                    display:'flex', alignItems:'center', justifyContent:'space-between',
                    padding:'10px 12px', background:'var(--bg-secondary)', borderRadius:'var(--radius-md)',
                    border:'1px solid var(--border)', cursor:'pointer', color:'var(--text-primary)',
                    fontSize:'0.85rem', fontWeight:500, transition:'var(--transition)',
                  }}
                  onMouseEnter={e => e.currentTarget.style.borderColor='var(--accent-cyan)44'}
                  onMouseLeave={e => e.currentTarget.style.borderColor='var(--border)'}
                >
                  {topic}
                  <span style={{ color:'var(--accent-cyan)', fontSize:'0.75rem' }}>Learn →</span>
                </button>
              ))}
            </div>
          ) : (
            <div style={{ color:'var(--text-muted)', fontSize:'0.85rem' }}>
              {loading ? 'Loading…' : 'Go practice some topics to get personalized suggestions!'}
            </div>
          )}
        </div>
      </div>

      {/* Badges */}
      {user?.badges?.length > 0 && (
        <div className="card" style={{ marginTop:20 }}>
          <h3 style={{ marginBottom:14 }}>🏆 Badges Earned</h3>
          <div style={{ display:'flex', flexWrap:'wrap', gap:10 }}>
            {user.badges.map(b => (
              <span key={b} className="badge badge-violet" style={{ padding:'6px 14px', fontSize:'0.8rem' }}>
                {BADGE_NAMES[b] || b.replace(/_/g,' ')}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
