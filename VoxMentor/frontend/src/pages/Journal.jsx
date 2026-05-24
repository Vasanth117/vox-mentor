import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { saveJournal, getJournal } from '../api';
import { BookOpen, PenSquare, Calendar, ChevronDown, ChevronUp, Lightbulb } from 'lucide-react';

const MOODS = [
  { id:'great',       emoji:'🚀', label:'Great' },
  { id:'good',        emoji:'😊', label:'Good' },
  { id:'neutral',     emoji:'😐', label:'Neutral' },
  { id:'stuck',       emoji:'🤔', label:'Stuck' },
  { id:'frustrated',  emoji:'😤', label:'Frustrated' },
];

const MOOD_COLORS = {
  great:'var(--accent-green)', good:'var(--accent-cyan)', neutral:'var(--text-secondary)',
  stuck:'var(--accent-orange)', frustrated:'var(--accent-pink)',
};

function EntryCard({ entry }) {
  const [open, setOpen] = useState(false);
  const mood = MOODS.find(m => m.id === (entry.mood_assessment || entry.mood)) || MOODS[2];
  return (
    <div className="card" style={{ marginBottom:12 }}>
      <div onClick={() => setOpen(p => !p)}
        style={{ display:'flex', justifyContent:'space-between', alignItems:'center', cursor:'pointer' }}>
        <div>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span style={{ fontSize:'1.1rem' }}>{mood.emoji}</span>
            <h4 style={{ fontSize:'0.9rem' }}>{entry.title}</h4>
          </div>
          <div style={{ fontSize:'0.72rem', color:'var(--text-muted)', marginTop:2 }}>
            <Calendar size={10} style={{ marginRight:4 }} />
            {new Date(entry.created_at).toLocaleDateString('en-US',{weekday:'short',month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
          </div>
        </div>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          {entry.topics_covered?.map(t => (
            <span key={t} className="badge badge-violet" style={{ fontSize:'0.65rem' }}>{t}</span>
          ))}
          {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </div>

      {open && (
        <div style={{ marginTop:14, paddingTop:14, borderTop:'1px solid var(--border)' }}>
          <p style={{ fontSize:'0.85rem', lineHeight:1.7, marginBottom:14 }}>{entry.content}</p>

          {entry.key_learnings?.length > 0 && (
            <div style={{ marginBottom:12 }}>
              <div style={{ fontSize:'0.75rem', fontWeight:700, color:'var(--accent-green)', marginBottom:6 }}>✅ Key Learnings</div>
              {entry.key_learnings.map((k, i) => (
                <div key={i} style={{ padding:'5px 10px', background:'rgba(16,217,142,0.08)', borderRadius:'var(--radius-sm)',
                  fontSize:'0.8rem', color:'var(--text-secondary)', marginBottom:4 }}>
                  {k}
                </div>
              ))}
            </div>
          )}

          {entry.encouragement && (
            <div style={{ padding:'10px 14px', background:'rgba(139,92,246,0.08)', border:'1px solid rgba(139,92,246,0.2)',
              borderRadius:'var(--radius-md)', fontSize:'0.82rem', color:'var(--accent-violet)' }}>
              <Lightbulb size={13} style={{ marginRight:6 }} />
              {entry.encouragement}
            </div>
          )}

          {entry.suggested_next_topics?.length > 0 && (
            <div style={{ marginTop:10 }}>
              <div style={{ fontSize:'0.72rem', color:'var(--text-muted)', marginBottom:6 }}>Suggested Next Topics:</div>
              <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
                {entry.suggested_next_topics.map(t => (
                  <span key={t} className="badge badge-cyan">{t}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function Journal() {
  const { user } = useAuth();
  const [entries, setEntries]         = useState([]);
  const [loading, setLoading]         = useState(true);
  const [saving, setSaving]           = useState(false);
  const [showForm, setShowForm]       = useState(false);
  const [form, setForm]               = useState({ title:'', content:'', mood:'neutral', topics_covered:'' });

  const loadEntries = useCallback(() => {
    if (!user?.user_id) return;
    getJournal(user.user_id)
      .then(r => setEntries(r.data?.entries || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [user?.user_id]);

  useEffect(() => { loadEntries(); }, [loadEntries]);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await saveJournal({
        user_id: user.user_id,
        title: form.title,
        content: form.content,
        mood: form.mood,
        topics_covered: form.topics_covered.split(',').map(t => t.trim()).filter(Boolean),
      });
      setForm({ title:'', content:'', mood:'neutral', topics_covered:'' });
      setShowForm(false);
      loadEntries();
    } catch {}
    setSaving(false);
  };

  return (
    <div className="fade-in">
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:24 }}>
        <div>
          <h1 className="page-title">Learning Journal</h1>
          <p className="page-subtitle">Reflect on your learning — the AI will analyze and encourage you</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(p => !p)}>
          <PenSquare size={16} />
          {showForm ? 'Cancel' : 'New Entry'}
        </button>
      </div>

      {/* Entry form */}
      {showForm && (
        <div className="card card-glow" style={{ marginBottom:24 }}>
          <h3 style={{ marginBottom:16 }}>✍️ New Reflection</h3>
          <form onSubmit={handleSave} style={{ display:'flex', flexDirection:'column', gap:14 }}>
            <input className="input" placeholder="Entry title (e.g. Understanding Recursion)"
              value={form.title} onChange={e => setForm(p => ({...p, title:e.target.value}))} required />

            <textarea className="input textarea" rows={5}
              placeholder="What did you learn today? What clicked? What confused you?"
              value={form.content} onChange={e => setForm(p => ({...p, content:e.target.value}))} required />

            <div>
              <div style={{ fontSize:'0.8rem', color:'var(--text-secondary)', marginBottom:8 }}>How are you feeling?</div>
              <div style={{ display:'flex', gap:8 }}>
                {MOODS.map(m => (
                  <button key={m.id} type="button"
                    className={`mood-btn ${form.mood===m.id?'selected':''}`}
                    onClick={() => setForm(p => ({...p, mood:m.id}))}>
                    {m.emoji}
                  </button>
                ))}
              </div>
            </div>

            <input className="input" placeholder="Topics covered (comma-separated, e.g. recursion, loops)"
              value={form.topics_covered} onChange={e => setForm(p => ({...p, topics_covered:e.target.value}))} />

            <button className="btn btn-primary" type="submit" disabled={saving}>
              {saving ? <div className="spinner" style={{ width:16,height:16 }} /> : '✨ Save & Get AI Insights'}
            </button>
          </form>
        </div>
      )}

      {/* Entries list */}
      {loading ? (
        <div style={{ display:'flex', justifyContent:'center', padding:60 }}><div className="spinner spinner-lg" /></div>
      ) : entries.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-icon">📓</div>
          <h3>No journal entries yet</h3>
          <p>Reflect on your learning sessions to track growth and get personalized encouragement</p>
          <button className="btn btn-primary" style={{ marginTop:16 }} onClick={() => setShowForm(true)}>
            Write Your First Entry
          </button>
        </div>
      ) : (
        <>
          <div style={{ fontSize:'0.8rem', color:'var(--text-muted)', marginBottom:14 }}>
            {entries.length} reflection{entries.length!==1?'s':''} · sorted by newest first
          </div>
          {entries.map(e => <EntryCard key={e._id} entry={e} />)}
        </>
      )}
    </div>
  );
}
