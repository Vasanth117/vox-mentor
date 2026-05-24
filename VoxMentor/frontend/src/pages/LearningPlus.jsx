import { useEffect, useState } from 'react';
import { ChevronDown, ChevronRight, Zap, Map, FolderGit2, RefreshCw, TrendingUp, AlertCircle, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  createGoalRoadmap,
  getAdaptivePath,
  getGoalRoadmaps,
  getProgressForecast,
  getSpacedRevisionQueue,
  reviewProjectLearning,
  startProjectLearning,
} from '../api';

/* ─── helpers ─────────────────────────────────────────────── */
const diffColor = (d) =>
  d === 'beginner' ? '#10d98e' : d === 'intermediate' ? '#f59e0b' : '#f87171';

const accuracyColor = (pct) =>
  pct >= 70 ? '#10d98e' : pct >= 40 ? '#f59e0b' : '#f87171';

const masteryBar = (val) => {
  const w = Math.min(100, Math.max(0, val));
  const col = w >= 70 ? '#10d98e' : w >= 40 ? '#4F8CFF' : '#f87171';
  return (
    <div style={{ background: 'var(--border)', borderRadius: 4, height: 6, width: '100%', overflow: 'hidden' }}>
      <div style={{ width: `${w}%`, height: '100%', background: col, borderRadius: 4, transition: 'width .4s' }} />
    </div>
  );
};

/* ─── Adaptive Path card ───────────────────────────────────── */
function AdaptivePathCard({ path }) {
  if (!path.length)
    return (
      <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '16px 0' }}>
        <AlertCircle size={16} style={{ marginRight: 6, verticalAlign: 'middle' }} />
        No practice data yet — complete a few sessions and come back.
      </div>
    );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      {path.slice(0, 6).map((item) => {
        const m = item.metrics || {};
        return (
          <div
            key={item.priority}
            style={{
              padding: '12px 14px',
              borderRadius: 10,
              border: '1px solid var(--border)',
              background: 'rgba(255,255,255,0.02)',
              display: 'grid',
              gridTemplateColumns: '28px 1fr auto',
              gap: '0 12px',
              alignItems: 'start',
            }}
          >
            {/* rank badge */}
            <div
              style={{
                width: 26, height: 26, borderRadius: '50%',
                background: 'var(--border)', display: 'flex',
                alignItems: 'center', justifyContent: 'center',
                fontWeight: 700, fontSize: '0.78rem', flexShrink: 0,
              }}
            >
              {item.priority}
            </div>

            {/* body */}
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: 3 }}>
                {String(item.topic).replace(/_/g, ' ')}
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 6, fontSize: '0.78rem' }}>
                <span style={{ color: diffColor(item.recommended_difficulty), fontWeight: 600 }}>
                  {item.recommended_difficulty}
                </span>
                <span style={{ color: 'var(--text-muted)' }}>·</span>
                <span style={{ color: 'var(--text-muted)' }}>{item.reason}</span>
              </div>
              {/* metrics row */}
              <div style={{ display: 'flex', gap: 14, fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>
                <span>
                  Accuracy:{' '}
                  <strong style={{ color: accuracyColor(m.accuracy_pct ?? 0) }}>
                    {m.accuracy_pct ?? 0}%
                  </strong>
                </span>
                <span>Attempts: <strong style={{ color: '#e2e8f0' }}>{m.attempts ?? 0}</strong></span>
                <span>Speed: <strong style={{ color: '#e2e8f0' }}>{m.speed_bucket ?? '—'}</strong></span>
              </div>
              {/* mastery bar */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-muted)', marginBottom: 3 }}>
                  <span>Mastery</span>
                  <span>{m.mastery ?? 0}%</span>
                </div>
                {masteryBar(m.mastery ?? 0)}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ─── Roadmaps card ────────────────────────────────────────── */
function RoadmapCard({ roadmaps, goal, setGoal, onCreate, busy }) {
  const [expanded, setExpanded] = useState({});
  const toggle = (id) => setExpanded((p) => ({ ...p, [id]: !p[id] }));

  return (
    <>
      {/* creator row */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        <select className="input" value={goal} onChange={(e) => setGoal(e.target.value)} style={{ flex: 1 }}>
          <option value="crack interviews">Crack Interviews</option>
          <option value="web dev">Web Dev</option>
          <option value="dsa in 30 days">DSA in 30 Days</option>
        </select>
        <button className="btn btn-primary" onClick={onCreate} disabled={busy}>
          {busy ? '…' : 'Generate'}
        </button>
      </div>

      {roadmaps.length === 0 ? (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No roadmaps yet — pick a goal and generate one.</p>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {roadmaps.map((r) => {
            const open = expanded[r._id];
            return (
              <div key={r._id} style={{ border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
                {/* header row */}
                <button
                  onClick={() => toggle(r._id)}
                  style={{
                    width: '100%', background: 'rgba(255,255,255,0.03)',
                    border: 'none', padding: '12px 14px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    cursor: 'pointer', color: 'inherit',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Map size={15} color="#4F8CFF" />
                    <span style={{ fontWeight: 700 }}>{r.goal}</span>
                    <span style={{
                      fontSize: '0.72rem', background: 'rgba(79,140,255,0.15)',
                      color: '#4F8CFF', borderRadius: 99, padding: '2px 8px'
                    }}>
                      {(r.weeks || []).length} weeks
                    </span>
                  </div>
                  {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
                </button>

                {/* body — weeks */}
                {open && (
                  <div style={{ padding: '10px 14px 14px', display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {(r.weeks || []).map((w) => (
                      <div key={w.week}>
                        <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#4F8CFF', marginBottom: 6 }}>
                          Week {w.week}
                        </div>
                        <ul style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 4 }}>
                          {(w.milestones || []).map((ms, i) => (
                            <li key={i} style={{ fontSize: '0.84rem', color: '#e2e8f0' }}>{ms}</li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </>
  );
}

/* ─── Mini Project section ─────────────────────────────────── */
function MiniProjectSection({ userId, busy, setBusy }) {
  const [projectGoal, setProjectGoal] = useState('interview prep');
  const [projectLanguage, setProjectLanguage] = useState('python');
  const [activeProject, setActiveProject] = useState(null);
  const [projectCode, setProjectCode] = useState('');
  const [review, setReview] = useState(null);
  const [specExpanded, setSpecExpanded] = useState(false);

  const startProject = async () => {
    if (!userId || busy) return;
    setBusy(true);
    setActiveProject(null);
    setReview(null);
    setProjectCode('');
    try {
      const { data } = await startProjectLearning(userId, projectGoal, projectLanguage);
      setActiveProject(data);
      setSpecExpanded(true);
    } finally {
      setBusy(false);
    }
  };

  const submitReview = async () => {
    if (!userId || !activeProject?._id || !projectCode.trim() || busy) return;
    setBusy(true);
    try {
      const { data } = await reviewProjectLearning(userId, activeProject._id, projectCode, 'Submitted from Learning+');
      setReview(data?.review || null);
    } finally {
      setBusy(false);
    }
  };

  const rubricColors = { 'Correctness': '#10d98e', 'Code quality': '#4F8CFF', 'Edge-case handling': '#f59e0b', 'Readability': '#7C5CFF' };

  return (
    <div className="card" style={{ marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
        <FolderGit2 size={18} color="#10d98e" />
        <h3 style={{ margin: 0 }}>Mini Project Generator</h3>
      </div>

      {/* config row */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 14 }}>
        <input
          className="input"
          style={{ flex: 2, minWidth: 160 }}
          value={projectGoal}
          onChange={(e) => setProjectGoal(e.target.value)}
          placeholder="Project goal (e.g. interview prep, web scraping…)"
        />
        <select className="input" style={{ flex: 1, minWidth: 120 }} value={projectLanguage} onChange={(e) => setProjectLanguage(e.target.value)}>
          <option value="python">Python</option>
          <option value="javascript">JavaScript</option>
          <option value="typescript">TypeScript</option>
          <option value="java">Java</option>
        </select>
        <button className="btn btn-primary" onClick={startProject} disabled={busy}>
          {busy ? '…' : 'Generate Project'}
        </button>
      </div>

      {/* active project spec */}
      {activeProject && (
        <div style={{ marginBottom: 16, border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
          {/* spec header */}
          <button
            onClick={() => setSpecExpanded((p) => !p)}
            style={{
              width: '100%', background: 'rgba(16,217,142,0.06)',
              border: 'none', padding: '12px 14px',
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              cursor: 'pointer', color: 'inherit',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <CheckCircle2 size={15} color="#10d98e" />
              <span style={{ fontWeight: 700 }}>
                {typeof activeProject.spec === 'string'
                  ? `Mini Project — ${activeProject.language?.toUpperCase()}`
                  : activeProject.spec?.title || 'Mini Project Spec'}
              </span>
              <span style={{ fontSize: '0.72rem', color: '#10d98e', background: 'rgba(16,217,142,0.12)', borderRadius: 99, padding: '2px 8px' }}>
                {activeProject.language}
              </span>
            </div>
            {specExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
          </button>

          {specExpanded && (
            <div style={{ padding: 14 }}>
              {/* spec body — render full AI markdown or structured spec */}
              {typeof activeProject.spec === 'string' ? (
                <pre style={{
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  fontSize: '0.83rem', lineHeight: 1.7, color: '#e2e8f0',
                  margin: 0, fontFamily: 'inherit',
                }}>
                  {activeProject.spec}
                </pre>
              ) : (
                <div style={{ fontSize: '0.84rem', lineHeight: 1.7 }}>
                  <p style={{ marginBottom: 6 }}><strong>Brief:</strong> {activeProject.spec?.brief}</p>
                  <div style={{ marginBottom: 6 }}>
                    <strong>Deliverables:</strong>
                    <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>
                      {(activeProject.spec?.deliverables || []).map((d, i) => <li key={i}>{d}</li>)}
                    </ul>
                  </div>
                </div>
              )}

              {/* rubric weight chips */}
              <div style={{ marginTop: 12 }}>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: 6 }}>Rubric criteria</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {(activeProject.rubric || []).map((r) => (
                    <span key={r.criterion} style={{
                      fontSize: '0.75rem', padding: '3px 10px', borderRadius: 99,
                      background: `${rubricColors[r.criterion] || '#4F8CFF'}22`,
                      color: rubricColors[r.criterion] || '#4F8CFF',
                      border: `1px solid ${rubricColors[r.criterion] || '#4F8CFF'}44`,
                    }}>
                      {r.criterion} ({r.weight}%)
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* code submission */}
      {activeProject && (
        <div>
          <textarea
            className="input"
            style={{ minHeight: 160, fontFamily: 'monospace', fontSize: '0.85rem', marginBottom: 10 }}
            value={projectCode}
            onChange={(e) => setProjectCode(e.target.value)}
            placeholder={`Paste your ${activeProject.language || 'project'} code here for rubric review…`}
          />
          <button
            className="btn btn-primary"
            onClick={submitReview}
            disabled={busy || !projectCode.trim()}
            style={{ marginBottom: 10 }}
          >
            {busy ? 'Reviewing…' : 'Submit for Review'}
          </button>
        </div>
      )}

      {/* review result */}
      {review && (
        <div style={{
          border: '1px solid var(--border)', borderRadius: 10,
          padding: 14, background: 'rgba(255,255,255,0.02)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
            <span style={{ fontWeight: 700, fontSize: '1rem' }}>Rubric Score</span>
            <span style={{
              fontWeight: 800, fontSize: '1.3rem',
              color: review.total >= 70 ? '#10d98e' : review.total >= 50 ? '#f59e0b' : '#f87171',
            }}>
              {review.total}<span style={{ fontSize: '0.8rem', fontWeight: 400, color: 'var(--text-muted)' }}>/100</span>
            </span>
          </div>

          {/* per-criterion scores */}
          {review.breakdown && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
              {Object.entries(review.breakdown).map(([crit, score]) => (
                <div key={crit}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', marginBottom: 3 }}>
                    <span style={{ color: rubricColors[crit] || '#4F8CFF' }}>{crit}</span>
                    <span style={{ color: '#e2e8f0' }}>{score}</span>
                  </div>
                  {masteryBar(typeof score === 'number' ? score : 0)}
                </div>
              ))}
            </div>
          )}

          {review.feedback && (
            <p style={{ fontSize: '0.84rem', color: '#e2e8f0', marginBottom: 8, lineHeight: 1.6 }}>
              {review.feedback}
            </p>
          )}
          {review.next_step && (
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
              <strong style={{ color: '#4F8CFF' }}>Next step:</strong> {review.next_step}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Spaced Revision Queue ────────────────────────────────── */
function SpacedRevisionCard({ queue }) {
  if (!queue.length)
    return <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>Revision queue is empty.</p>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {queue.slice(0, 8).map((item, idx) => (
        <div key={idx} style={{
          padding: '10px 12px', borderRadius: 8,
          border: '1px solid var(--border)', background: 'rgba(255,255,255,0.02)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{String(item.topic).replace(/_/g, ' ')}</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
              Mastery {item.mastery}% · Accuracy {item.accuracy_pct}%
            </div>
          </div>
          <span style={{
            fontSize: '0.72rem', padding: '3px 9px', borderRadius: 99,
            background: 'rgba(124,92,255,0.15)', color: '#7C5CFF',
          }}>
            P{item.priority}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ─── Page ─────────────────────────────────────────────────── */
export default function LearningPlus() {
  const { user } = useAuth();
  const [adaptivePath, setAdaptivePath] = useState([]);
  const [forecast, setForecast] = useState(null);
  const [revisionQueue, setRevisionQueue] = useState([]);
  const [roadmaps, setRoadmaps] = useState([]);
  const [goal, setGoal] = useState('crack interviews');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadAll = async () => {
    if (!user?.user_id) return;
    setLoading(true);
    try {
      const [pathResp, forecastResp, revisionResp, roadmapsResp] = await Promise.all([
        getAdaptivePath(user.user_id, 'python_fundamentals'),
        getProgressForecast(user.user_id),
        getSpacedRevisionQueue(user.user_id),
        getGoalRoadmaps(user.user_id),
      ]);
      setAdaptivePath(pathResp.data?.path || []);
      setForecast(forecastResp.data || null);
      setRevisionQueue(revisionResp.data?.queue || []);
      setRoadmaps(roadmapsResp.data?.roadmaps || []);
    } catch {
      setAdaptivePath([]);
      setRevisionQueue([]);
      setRoadmaps([]);
      setForecast(null);
    }
    setLoading(false);
  };

  useEffect(() => { loadAll(); }, [user?.user_id]); // eslint-disable-line

  const createRoadmap = async () => {
    if (!user?.user_id || busy) return;
    setBusy(true);
    try {
      await createGoalRoadmap(user.user_id, goal);
      await loadAll();
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Learning+</h1>
        <p className="page-subtitle">
          Personalised adaptive path, AI-generated projects, spaced revision, goal roadmaps, and progress forecasting.
        </p>
      </div>

      {/* ── Forecast banner ── */}
      {forecast && (
        <div className="card" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <TrendingUp size={20} color="#10d98e" style={{ flexShrink: 0 }} />
          <div style={{ flex: 1, minWidth: 200 }}>
            <div style={{ fontWeight: 700, marginBottom: 2 }}>Progress Forecast</div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>
              Days to next level: <strong style={{ color: '#e2e8f0' }}>{forecast.days_to_next_level ?? '—'}</strong>
              &nbsp;·&nbsp;
              XP needed: <strong style={{ color: '#e2e8f0' }}>{forecast.xp_to_next_level ?? '—'}</strong>
              {forecast.nudge && <>&nbsp;·&nbsp;<em>{forecast.nudge}</em></>}
            </div>
          </div>
        </div>
      )}

      {/* ── Top grid: Adaptive Path + Spaced Revision ── */}
      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <Zap size={18} color="#f59e0b" />
            <h3 style={{ margin: 0 }}>Adaptive Path 2.0</h3>
          </div>
          <AdaptivePathCard path={adaptivePath} />
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
            <RefreshCw size={18} color="#7C5CFF" />
            <h3 style={{ margin: 0 }}>Spaced Revision Queue</h3>
          </div>
          <SpacedRevisionCard queue={revisionQueue} />
        </div>
      </div>

      {/* ── Goal-Based Roadmaps ── */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <Map size={18} color="#4F8CFF" />
          <h3 style={{ margin: 0 }}>Goal-Based Roadmaps</h3>
        </div>
        <RoadmapCard
          roadmaps={roadmaps}
          goal={goal}
          setGoal={setGoal}
          onCreate={createRoadmap}
          busy={busy}
        />
      </div>

      {/* ── Mini Project Generator ── */}
      <MiniProjectSection userId={user?.user_id} busy={busy} setBusy={setBusy} />
    </div>
  );
}
