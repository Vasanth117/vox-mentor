import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { getDailyChallenge, generateChallenge, submitSolution } from '../api';
import Editor from '@monaco-editor/react';
import { Play, RefreshCw, Trophy, Clock, Zap, Target, Star } from 'lucide-react';
import { ensureMonacoConfigured } from '../lib/monacoSetup';

const TOPICS = ['variables','loops','functions','arrays','strings','recursion','sorting','linked list','trees','dynamic programming'];
const DIFFS  = ['beginner','intermediate','advanced'];
const LANGS  = ['python','javascript','c','cpp'];

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

export default function Practice() {
  const { user, refreshUser } = useAuth();
  const [challenge, setChallenge]     = useState(null);
  const [code, setCode]               = useState('# Write your solution here\n');
  const [language, setLanguage]       = useState('python');
  const [topic, setTopic]             = useState('loops');
  const [difficulty, setDifficulty]   = useState('beginner');
  const [result, setResult]           = useState(null);
  const [loading, setLoading]         = useState(false);
  const [submitting, setSubmitting]   = useState(false);
  const [mode, setMode]               = useState('daily'); // daily | custom
  const [timer, setTimer]             = useState(0);
  const [timerActive, setTimerActive] = useState(false);
  const [challengeId, setChallengeId] = useState(null);
  const [monacoReady, setMonacoReady] = useState(false);

  useEffect(() => {
    let mounted = true;
    ensureMonacoConfigured()
      .then(() => {
        if (mounted) setMonacoReady(true);
      })
      .catch(() => {
        if (mounted) setMonacoReady(true);
      });
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    let t;
    if (timerActive) t = setInterval(() => setTimer(s => s+1), 1000);
    return () => clearInterval(t);
  }, [timerActive]);

  const fmt = (s) => `${String(Math.floor(s/60)).padStart(2,'0')}:${String(s%60).padStart(2,'0')}`;

  const loadDaily = async () => {
    setLoading(true); setResult(null);
    try {
      const { data } = await getDailyChallenge(user.user_id, language);
      setChallenge(data.challenge || data);
      setChallengeId(data._id);
      setCode(data.challenge?.starter_code || '# Write your solution here\n');
      setTimer(0); setTimerActive(true);
    } catch { setChallenge(null); }
    setLoading(false);
  };

  const generate = async () => {
    setLoading(true); setResult(null);
    try {
      const { data } = await generateChallenge({ user_id: user.user_id, topic, language, difficulty });
      setChallenge(data);
      setChallengeId(data._id);
      setCode(data.starter_code || '# Write your solution here\n');
      setTimer(0); setTimerActive(true);
    } catch { setChallenge(null); }
    setLoading(false);
  };

  const submit = async () => {
    if (!challengeId) return;
    setSubmitting(true); setTimerActive(false);
    try {
      const { data } = await submitSolution({ user_id: user.user_id, challenge_id: challengeId, code, language });
      setResult(data);
      if (data.success) {
        // Refresh user profile to sync XP, streak & badges from server
        await refreshUser();
      }
    } catch { setResult({ success:false, run_result:{ stderr:'Submission error' } }); }
    setSubmitting(false);
  };

  useEffect(() => {
    if (mode === 'daily') loadDaily();
  }, [mode]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="fade-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <div>
          <h1 className="page-title">Practice Mode</h1>
          <p className="page-subtitle">Sharpen your skills with AI-generated coding challenges</p>
        </div>
        {timerActive && (
          <div style={{ display:'flex', alignItems:'center', gap:8, padding:'8px 18px',
            background:'rgba(0,212,255,0.1)', border:'1px solid var(--accent-cyan)', borderRadius:'var(--radius-md)' }}>
            <Clock size={16} color="var(--accent-cyan)" />
            <span style={{ fontFamily:'var(--font-code)', fontWeight:700, color:'var(--accent-cyan)' }}>{fmt(timer)}</span>
          </div>
        )}
      </div>

      {/* Mode + controls */}
      <div className="card" style={{ marginBottom:20 }}>
        <div className="tab-bar" style={{ marginBottom:16 }}>
          <button className={`tab-btn ${mode==='daily'?'active':''}`} onClick={() => setMode('daily')}>🎯 Daily Challenge</button>
          <button className={`tab-btn ${mode==='custom'?'active':''}`} onClick={() => setMode('custom')}>⚡ Custom</button>
        </div>

        {mode === 'custom' && (
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr auto', gap:10, alignItems:'end' }}>
            <div>
              <div style={{ fontSize:'0.75rem', color:'var(--text-muted)', marginBottom:4 }}>Topic</div>
              <select className="input select" value={topic} onChange={e => setTopic(e.target.value)}>
                {TOPICS.map(t => <option key={t} value={t}>{t.charAt(0).toUpperCase()+t.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize:'0.75rem', color:'var(--text-muted)', marginBottom:4 }}>Difficulty</div>
              <select className="input select" value={difficulty} onChange={e => setDifficulty(e.target.value)}>
                {DIFFS.map(d => <option key={d} value={d}>{d.charAt(0).toUpperCase()+d.slice(1)}</option>)}
              </select>
            </div>
            <div>
              <div style={{ fontSize:'0.75rem', color:'var(--text-muted)', marginBottom:4 }}>Language</div>
              <select className="input select" value={language} onChange={e => setLanguage(e.target.value)}>
                {LANGS.map(l => <option key={l} value={l}>{l==='cpp'?'C++':l.charAt(0).toUpperCase()+l.slice(1)}</option>)}
              </select>
            </div>
            <button className="btn btn-primary" onClick={generate} disabled={loading}
              style={{ padding:'10px 20px' }}>
              {loading ? <div className="spinner" style={{ width:16,height:16 }} /> : <><Zap size={16} /> Generate</>}
            </button>
          </div>
        )}

        {mode === 'daily' && (
          <button className="btn btn-secondary" onClick={loadDaily} disabled={loading} style={{ gap:8 }}>
            {loading ? <div className="spinner" style={{ width:16,height:16 }} /> : <><RefreshCw size={15} /> Reload Daily Challenge</>}
          </button>
        )}
      </div>

      {/* Challenge display */}
      {loading && !challenge && (
        <div style={{ display:'flex', justifyContent:'center', padding:60 }}><div className="spinner spinner-lg" /></div>
      )}

      {challenge && (
        <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
          {/* Problem */}
          <div style={{ display:'flex', flexDirection:'column', gap:14 }}>
            <div className="card">
              <div style={{ display:'flex', gap:8, marginBottom:12, flexWrap:'wrap' }}>
                <span className={`badge badge-${challenge.difficulty==='beginner'?'green':challenge.difficulty==='advanced'?'pink':'orange'}`}>
                  {challenge.difficulty}
                </span>
                {challenge.topic && <span className="badge badge-cyan">{challenge.topic}</span>}
                {challenge.xp_reward && <span className="badge badge-violet"><Zap size={9} /> {challenge.xp_reward} XP</span>}
              </div>
              <h2 style={{ marginBottom:10, fontSize:'1.1rem' }}>{challenge.title}</h2>
              <p style={{ fontSize:'0.85rem', lineHeight:1.75, whiteSpace:'pre-wrap' }}>{challenge.description}</p>
            </div>

            {challenge.test_cases?.length > 0 && (
              <div className="card">
                <h4 style={{ marginBottom:10 }}>🧪 Test Cases</h4>
                {challenge.test_cases.map((tc, i) => (
                  <div key={i} style={{ fontFamily:'var(--font-code)', fontSize:'0.78rem', marginBottom:8,
                    padding:'8px', background:'var(--bg-secondary)', borderRadius:'var(--radius-sm)' }}>
                    <span style={{ color:'var(--text-muted)' }}>Input: </span>
                    <span style={{ color:'var(--accent-cyan)' }}>{tc.input}</span>
                    <br />
                    <span style={{ color:'var(--text-muted)' }}>Expected: </span>
                    <span style={{ color:'var(--accent-green)' }}>{tc.expected_output}</span>
                  </div>
                ))}
              </div>
            )}

            {challenge.hint && (
              <details className="card">
                <summary style={{ cursor:'pointer', fontWeight:600, fontSize:'0.85rem' }}>💡 Hint</summary>
                <p style={{ marginTop:8, fontSize:'0.82rem' }}>{challenge.hint}</p>
              </details>
            )}
          </div>

          {/* Editor + Submit */}
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            <div style={{ borderRadius:'var(--radius-lg)', overflow:'hidden', border:'1px solid var(--border)', flex:1 }}>
              <div style={{ padding:'8px 14px', background:'var(--bg-secondary)', borderBottom:'1px solid var(--border)',
                fontSize:'0.75rem', color:'var(--text-muted)', display:'flex', gap:8 }}>
                <div style={{ width:10,height:10,borderRadius:'50%',background:'#ff5f56' }} />
                <div style={{ width:10,height:10,borderRadius:'50%',background:'#ffbd2e' }} />
                <div style={{ width:10,height:10,borderRadius:'50%',background:'#27c93f' }} />
                <span style={{ marginLeft:8 }}>Solution Editor</span>
              </div>
              {monacoReady ? (
                <Editor height="300px" language={language === 'cpp' ? 'cpp' : language}
                  value={code} onChange={v => setCode(v || '')}
                  theme="vs-dark"
                  options={{ fontSize:13, fontFamily:'JetBrains Mono, monospace', minimap:{enabled:false}, scrollBeyondLastLine:false, padding:{top:12} }} />
              ) : (
                <div style={{ height: 300, display: 'grid', placeItems: 'center', color: 'var(--text-muted)' }}>
                  Loading editor…
                </div>
              )}
            </div>

            <button className="btn btn-green" onClick={submit} disabled={submitting}
              style={{ justifyContent:'center', padding:14 }}>
              {submitting ? <div className="spinner" style={{ width:18,height:18 }} /> : <><Play size={18} /> Submit Solution</>}
            </button>

            {/* Result */}
            {result && (
              <div className="card" style={{
                borderColor: result.success ? 'rgba(16,217,142,0.4)' : 'rgba(239,68,68,0.4)',
                background: result.success ? 'rgba(16,217,142,0.06)' : 'rgba(239,68,68,0.06)',
              }}>
                <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:10 }}>
                  <span style={{ fontSize:'1.4rem' }}>{result.success ? '🎉' : '❌'}</span>
                  <div style={{ flex:1 }}>
                    <div style={{ fontWeight:700, color: result.success ? 'var(--accent-green)' : '#f87171' }}>
                      {result.success ? 'Correct!' : 'Not quite right'}
                    </div>
                    {result.success && result.xp_reward > 0 && (
                      <div style={{ fontSize:'0.8rem', color:'var(--accent-cyan)', fontWeight:600 }}>
                        <Zap size={12} style={{ marginRight:3 }} />
                        +{result.xp_reward} XP earned!{result.is_daily ? ' (Daily Bonus!)' : ''}
                      </div>
                    )}
                    {result.success && result.level && (
                      <div style={{ fontSize:'0.78rem', color:'var(--text-muted)', marginTop:2 }}>
                        Level {result.level.level} — {result.level.level_name} &nbsp;·&nbsp; {result.level.progress_pct}% to next
                      </div>
                    )}
                  </div>
                </div>
                {result.success && result.new_badges?.length > 0 && (
                  <div style={{ marginBottom:10, display:'flex', flexWrap:'wrap', gap:6 }}>
                    <span style={{ fontSize:'0.75rem', color:'var(--text-muted)', width:'100%', marginBottom:2 }}>New badges earned:</span>
                    {result.new_badges.map(b => (
                      <span key={b} className="badge badge-violet" style={{ fontSize:'0.72rem' }}>
                        <Star size={10} style={{ marginRight:3 }} />{BADGE_NAMES[b] || b.replace(/_/g,' ')}
                      </span>
                    ))}
                  </div>
                )}
                <div className={`code-output ${result.success?'success':'error'}`} style={{ maxHeight:120 }}>
                  {result.run_result?.stdout || result.run_result?.stderr || 'No output'}
                </div>

                {result.ai_feedback && (
                  <div className="card" style={{ marginTop: 10, background:'var(--bg-secondary)', border:'1px solid var(--border)' }}>
                    <h4 style={{ marginBottom: 8, fontSize:'0.9rem' }}>
                      {result.feedback_mode === 'hint_only' ? '💡 AI Hint' : '🛠️ AI Improvement Suggestions'}
                    </h4>
                    <p style={{ fontSize:'0.82rem', lineHeight:1.7, color:'var(--text-secondary)', whiteSpace:'pre-wrap', margin: 0 }}>
                      {result.ai_feedback}
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
