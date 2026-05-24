import { useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getProgress, getProgressForecast } from '../api';
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { Flame, Zap, TrendingUp, Target } from 'lucide-react';

const COLORS = ['#00d4ff','#8b5cf6','#10d98e','#f97316','#ec4899','#facc15'];

function MasteryBar({ topic, mastery }) {
  const pct = Math.round(mastery);
  const color = pct >= 75 ? '#10d98e' : pct >= 45 ? '#00d4ff' : '#f97316';
  return (
    <div style={{ marginBottom:10 }}>
      <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
        <span style={{ fontSize:'0.82rem', fontWeight:500, color:'var(--text-primary)' }}>
          {topic.charAt(0).toUpperCase()+topic.slice(1).replace(/_/g,' ')}
        </span>
        <span style={{ fontSize:'0.8rem', color, fontWeight:700 }}>{pct}%</span>
      </div>
      <div className="progress-bar">
        <div style={{ height:'100%', width:`${pct}%`, background:color, borderRadius:99, transition:'width 0.8s ease' }} />
      </div>
    </div>
  );
}

function TopicStatusBadge({ status }) {
  const map = {
    new: { label: 'New', color: 'var(--accent-violet)' },
    needs_practice: { label: 'Needs Practice', color: 'var(--accent-orange)' },
    improving: { label: 'Improving', color: 'var(--accent-cyan)' },
    solid: { label: 'Solid', color: 'var(--accent-green)' },
  };
  const conf = map[status] || map.new;
  return <span style={{ fontSize: '0.72rem', fontWeight: 700, color: conf.color }}>{conf.label}</span>;
}

export default function ProgressPage() {
  const { user } = useAuth();
  const [progress, setProgress] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!user?.user_id) return;
    Promise.all([
      getProgress(user.user_id),
      getProgressForecast(user.user_id),
    ])
      .then(([progressResp, forecastResp]) => {
        setProgress(progressResp.data);
        setForecast(forecastResp.data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user?.user_id]);

  if (loading) return <div style={{ display:'flex', justifyContent:'center', padding:60 }}><div className="spinner spinner-lg" /></div>;

  const topics = progress?.topics || [];
  const xp = progress?.total_xp || 0;
  const level = progress?.level || { level_name:'Novice', progress_pct:0 };
  const streak = progress?.streak || 0;
  const minutes = Math.round(progress?.total_time_minutes || 0);
  const avgProficiency = Math.round(progress?.avg_proficiency || 0);
  const overallAccuracy = Math.round(progress?.overall_accuracy || 0);
  const readinessScore = Math.round(progress?.readiness_score || 0);
  const totalAttempts = progress?.total_attempts || 0;
  const overallBand = progress?.overall_band || 'beginner';
  const weak = progress?.weak_areas || [];
  const strong = progress?.strong_areas || [];

  const radarData = topics.slice(0, 6).map(t => ({
    subject: t.topic.replace(/_/g,' '),
    mastery: Math.round(t.proficiency_score ?? t.mastery ?? 0),
  }));

  const barData = topics.slice(0, 8).map(t => ({
    name: t.topic.slice(0,8),
    mastery: Math.round(t.proficiency_score ?? t.mastery ?? 0),
    attempts: t.attempts,
    accuracy: Math.round(t.accuracy_pct ?? 0),
    confidence: Math.round(t.confidence_pct ?? 0),
  }));

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Learning Progress</h1>
        <p className="page-subtitle">Your personalized growth analytics dashboard • {overallBand} profile</p>
      </div>

      {/* Stat cards */}
      <div className="grid-4" style={{ marginBottom:24 }}>
        {[
          { icon:Zap,        label:'Total XP',    value: xp,      color:'var(--accent-cyan)' },
          { icon:Flame,      label:'Day Streak',  value: streak,  color:'var(--accent-orange)' },
          { icon:TrendingUp, label:'Accuracy', value: `${overallAccuracy}%`, color:'var(--accent-violet)' },
          { icon:Target,     label:'Readiness', value: `${readinessScore}%`,  color:'var(--accent-green)' },
        ].map(({ icon, label, value, color }) => {
          const Icon = icon;
          return (
          <div key={label} className="card" style={{ display:'flex', alignItems:'center', gap:14 }}>
            <div style={{ width:44, height:44, borderRadius:'var(--radius-md)', background:`${color}22`, display:'flex', alignItems:'center', justifyContent:'center' }}>
              <Icon size={20} color={color} />
            </div>
            <div>
              <div className="stat-value" style={{ fontSize:'1.75rem', color }}>{value}</div>
              <div className="stat-label">{label}</div>
            </div>
          </div>
          );
        })}
      </div>

      <div className="card" style={{ marginBottom: 24, padding: '14px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ fontWeight: 700 }}>Practice Readiness</span>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{readinessScore}% • {totalAttempts} attempts</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${readinessScore}%` }} />
        </div>
        <div style={{ marginTop: 8, fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Based on proficiency ({avgProficiency}%), accuracy ({overallAccuracy}%), and consistency (streak).
        </div>
      </div>

      {forecast && (
        <div className="card" style={{ marginBottom: 24, padding: '14px 24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontWeight: 700 }}>Forecast</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              {forecast.days_to_next_level ?? '-'} days to next level
            </span>
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            {forecast.nudge || 'Keep practicing consistently to accelerate growth.'}
          </div>
        </div>
      )}

      {/* Level bar */}
      <div className="card card-glow" style={{ marginBottom:24, padding:'16px 24px' }}>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:10 }}>
          <div>
            <span className="badge badge-violet">{level.level_name}</span>
            <span style={{ marginLeft:10, fontWeight:700 }}>Level {level.level || 0}</span>
          </div>
          <span style={{ fontSize:'0.8rem', color:'var(--text-muted)' }}>{level.progress_pct || 0}% to next level</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width:`${level.progress_pct || 0}%` }} />
        </div>
        <div style={{ marginTop: 10, fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          Proficiency is weighted by mastery, accuracy, and confidence (number of attempts).
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom:24 }}>
        {/* Radar chart */}
        <div className="card">
          <h3 style={{ marginBottom:16 }}>📊 Skill Radar</h3>
          {radarData.length > 2 ? (
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="var(--border)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill:'var(--text-muted)', fontSize:11 }} />
                <Radar dataKey="mastery" stroke="var(--accent-cyan)" fill="var(--accent-cyan)" fillOpacity={0.2} />
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding:40 }}>
              <div className="empty-icon">📡</div>
              <h3>Not enough data yet</h3>
              <p>Study more topics to see your skill radar</p>
            </div>
          )}
        </div>

        {/* Bar chart */}
        <div className="card">
          <h3 style={{ marginBottom:16 }}>🎯 Proficiency by Topic</h3>
          {barData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={barData} margin={{ top:0, right:0, bottom:0, left:-20 }}>
                <XAxis dataKey="name" tick={{ fill:'var(--text-muted)', fontSize:10 }} />
                <YAxis domain={[0,100]} tick={{ fill:'var(--text-muted)', fontSize:10 }} />
                <Tooltip
                  contentStyle={{ background:'var(--bg-secondary)', border:'1px solid var(--border)', borderRadius:8 }}
                  labelStyle={{ color:'var(--text-primary)' }}
                  formatter={(value, name, item) => {
                    if (name === 'mastery') return [`${value}%`, 'Proficiency'];
                    if (name === 'accuracy') return [`${value}%`, 'Accuracy'];
                    if (name === 'confidence') return [`${value}%`, 'Confidence'];
                    return [value, name];
                  }}
                />
                <Bar dataKey="mastery" radius={[4,4,0,0]}>
                  {barData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} fillOpacity={0.8} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ padding:40 }}>
              <div className="empty-icon">📈</div>
              <h3>No topics yet</h3>
              <p>Complete practice sessions to track mastery</p>
            </div>
          )}
        </div>
      </div>

      {/* Topic mastery list */}
      {topics.length > 0 && (
        <div className="card" style={{ marginBottom:24 }}>
          <h3 style={{ marginBottom:16 }}>📚 Topic Proficiency</h3>
          <div className="grid-2">
            {[...topics].sort((a, b) => (a.proficiency_score ?? 0) - (b.proficiency_score ?? 0)).map(t => (
              <div key={t.topic}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Attempts {t.attempts || 0}</div>
                  <TopicStatusBadge status={t.status} />
                </div>
                <MasteryBar topic={t.topic} mastery={t.proficiency_score ?? t.mastery ?? 0} />
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: -4, marginBottom: 8 }}>
                  Accuracy {Math.round(t.accuracy_pct ?? 0)}% • Attempts {t.attempts || 0} • Confidence {Math.round(t.confidence_pct ?? 0)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weak & Strong areas */}
      {(weak.length > 0 || strong.length > 0) && (
        <div className="grid-2">
          {weak.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom:12 }}>⚠️ Areas to Improve</h3>
              {weak.map(w => (
                <div key={w} style={{ padding:'8px 12px', background:'rgba(249,115,22,0.08)', border:'1px solid rgba(249,115,22,0.2)', borderRadius:'var(--radius-md)', marginBottom:6, fontSize:'0.85rem', color:'var(--accent-orange)' }}>
                  {w.replace(/_/g,' ')}
                </div>
              ))}
            </div>
          )}
          {strong.length > 0 && (
            <div className="card">
              <h3 style={{ marginBottom:12 }}>⭐ Your Strengths</h3>
              {strong.map(s => (
                <div key={s} style={{ padding:'8px 12px', background:'rgba(16,217,142,0.08)', border:'1px solid rgba(16,217,142,0.2)', borderRadius:'var(--radius-md)', marginBottom:6, fontSize:'0.85rem', color:'var(--accent-green)' }}>
                  {s.replace(/_/g,' ')}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {topics.length === 0 && (
        <div className="card empty-state" style={{ padding:60 }}>
          <div className="empty-icon">🌱</div>
          <h3>Start Your Learning Journey</h3>
          <p>Practice coding challenges and chat with the AI tutor to see your progress here</p>
        </div>
      )}
    </div>
  );
}
