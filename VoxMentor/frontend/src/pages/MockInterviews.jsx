import { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { getMockInterviewHint, startMockInterview, submitMockInterview } from '../api';

export default function MockInterviews() {
  const { user } = useAuth();
  const [difficulty, setDifficulty] = useState('intermediate');
  const [language, setLanguage] = useState('python');
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [session, setSession] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [hints, setHints] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const beginInterview = async () => {
    if (!user?.user_id || loading) return;
    setLoading(true);
    try {
      const { data } = await startMockInterview(user.user_id, difficulty, language, Number(durationMinutes));
      setSession(data);
      setAnswers(new Array((data.questions || []).length).fill(''));
      setHints({});
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const requestHint = async (index) => {
    if (!user?.user_id || !session?.interview_id || loading) return;
    setLoading(true);
    try {
      const { data } = await getMockInterviewHint(user.user_id, session.interview_id, index);
      setHints((prev) => ({ ...prev, [index]: data.hint }));
    } finally {
      setLoading(false);
    }
  };

  const submitInterview = async () => {
    if (!user?.user_id || !session?.interview_id || loading) return;
    setLoading(true);
    try {
      const { data } = await submitMockInterview(user.user_id, session.interview_id, answers);
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Mock Interviews</h1>
        <p className="page-subtitle">Timed coding rounds with hint penalties and post-round feedback.</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 8 }}>
          <select className="input" value={difficulty} onChange={(e) => setDifficulty(e.target.value)}>
            <option value="beginner">Beginner</option>
            <option value="intermediate">Intermediate</option>
            <option value="advanced">Advanced</option>
          </select>
          <select className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
          </select>
          <input
            className="input"
            type="number"
            min={15}
            max={90}
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
          />
          <button className="btn btn-primary" onClick={beginInterview} disabled={loading}>
            {loading ? 'Starting...' : 'Start Interview'}
          </button>
        </div>
      </div>

      {session?.questions?.length > 0 && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8 }}>Interview Questions</h3>
          {session.questions.map((q, idx) => (
            <div key={idx} style={{ borderTop: idx ? '1px solid var(--border)' : 'none', paddingTop: idx ? 10 : 0, marginTop: idx ? 10 : 0 }}>
              <div style={{ fontWeight: 700, marginBottom: 6 }}>{idx + 1}. {q.title}</div>
              <p style={{ fontSize: '0.85rem', marginBottom: 8 }}>{q.prompt}</p>
              <textarea
                className="input"
                style={{ minHeight: 110, marginBottom: 8 }}
                value={answers[idx] || ''}
                onChange={(e) => {
                  const next = [...answers];
                  next[idx] = e.target.value;
                  setAnswers(next);
                }}
                placeholder="Write your approach / answer"
              />
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <button className="btn btn-secondary" onClick={() => requestHint(idx)} disabled={loading}>
                  {loading ? '...' : 'Get Hint (-5)'}
                </button>
                {hints[idx] && <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{hints[idx]}</div>}
              </div>
            </div>
          ))}

          <button className="btn btn-green" style={{ marginTop: 12 }} onClick={submitInterview} disabled={loading}>
            {loading ? 'Submitting...' : 'Submit Interview'}
          </button>
        </div>
      )}

      {result && (
        <div className="card">
          <h3 style={{ marginBottom: 8 }}>Interview Result</h3>
          <div style={{ fontSize: '0.9rem', marginBottom: 6 }}>
            Completion: <strong>{result.completion_score}</strong> · Hint penalty: <strong>{result.hint_penalty}</strong>
          </div>
          <div style={{ fontSize: '1rem', fontWeight: 700, marginBottom: 8 }}>Final Score: {result.final_score}</div>
          <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text-secondary)', fontSize: '0.84rem' }}>{result.feedback}</div>
        </div>
      )}
    </div>
  );
}
