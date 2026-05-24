import { useEffect, useMemo, useRef, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  askModuleDoubt,
  getModuleExplanation,
  getSkillModules,
  startFinalSkillTest,
  startModuleTest,
  submitFinalSkillTest,
  submitModuleTest,
} from '../api';
import { BookOpen, CheckCircle2, Lock, MessageSquare, Trophy, Unlock, X } from 'lucide-react';

function ModuleStatusBadge({ status }) {
  const map = {
    locked: { label: 'Locked', color: 'var(--text-muted)' },
    active: { label: 'Active', color: 'var(--accent-cyan)' },
    completed: { label: 'Completed', color: 'var(--accent-green)' },
  };
  const conf = map[status] || map.locked;
  return <span style={{ fontSize: '0.72rem', fontWeight: 700, color: conf.color }}>{conf.label}</span>;
}

export default function SkillTree() {
  const { user, refreshUser } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedSkill, setSelectedSkill] = useState(null);
  const [selectedModule, setSelectedModule] = useState(null);
  const [learningOpen, setLearningOpen] = useState(false);

  const [explanation, setExplanation] = useState('');
  const [expLoading, setExpLoading] = useState(false);

  const [doubt, setDoubt] = useState('');
  const [chat, setChat] = useState([]);
  const [chatLoading, setChatLoading] = useState(false);
  const chatContainerRef = useRef(null);

  const [moduleTest, setModuleTest] = useState(null);
  const [moduleChoice, setModuleChoice] = useState(-1);
  const [moduleTestResult, setModuleTestResult] = useState(null);
  const [moduleTestLoading, setModuleTestLoading] = useState(false);

  const [finalTest, setFinalTest] = useState(null);
  const [finalChoices, setFinalChoices] = useState([]);
  const [finalResult, setFinalResult] = useState(null);
  const [finalLoading, setFinalLoading] = useState(false);

  const reload = async () => {
    if (!user?.user_id) return;
    setLoading(true);
    try {
      const { data: payload } = await getSkillModules(user.user_id);
      setData(payload);

      const firstUnlocked = (payload.skills || []).find((skill) => skill.unlocked) || payload.skills?.[0] || null;
      setSelectedSkill((prev) => {
        if (!prev) return firstUnlocked;
        const updated = (payload.skills || []).find((skill) => skill.skill_id === prev.skill_id);
        return updated || firstUnlocked;
      });
    } catch {
      setData({ skills: [] });
    }
    setLoading(false);
  };

  useEffect(() => {
    reload();
  }, [user?.user_id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [chat, chatLoading]);

  const skills = useMemo(() => data?.skills || [], [data]);

  const currentSkill = useMemo(() => {
    if (!selectedSkill) return null;
    return skills.find((skill) => skill.skill_id === selectedSkill.skill_id) || null;
  }, [skills, selectedSkill]);

  const onSelectSkill = (skill) => {
    setSelectedSkill(skill);
    setFinalTest(null);
    setFinalResult(null);
  };

  const openLearning = async (module) => {
    if (!currentSkill || module.status === 'locked') return;
    setSelectedModule(module);
    setLearningOpen(true);
    setExplanation('');
    setChat([]);
    setModuleTest(null);
    setModuleTestResult(null);

    setExpLoading(true);
    try {
      const { data: payload } = await getModuleExplanation(user.user_id, currentSkill.skill_id, module.module_id);
      setExplanation(payload.explanation || 'No explanation generated.');
    } catch {
      setExplanation('Explanation unavailable right now.');
    }
    setExpLoading(false);
  };

  const closeLearning = () => {
    setLearningOpen(false);
    setSelectedModule(null);
    setExplanation('');
    setChat([]);
    setDoubt('');
    setModuleTest(null);
    setModuleTestResult(null);
    setModuleChoice(-1);
  };

  const handleAskDoubt = async () => {
    if (!doubt.trim() || !currentSkill || !selectedModule || chatLoading) return;
    const text = doubt.trim();
    setDoubt('');
    setChat((prev) => [...prev, { role: 'user', content: text }]);
    setChatLoading(true);
    try {
      const { data: payload } = await askModuleDoubt(user.user_id, currentSkill.skill_id, selectedModule.module_id, text);
      setChat((prev) => [...prev, { role: 'assistant', content: payload.reply || 'No reply' }]);
    } catch {
      setChat((prev) => [...prev, { role: 'assistant', content: 'Doubt assistant is unavailable, please retry.' }]);
    }
    setChatLoading(false);
  };

  const handleStartModuleTest = async () => {
    if (!currentSkill || !selectedModule) return;
    setModuleTestLoading(true);
    setModuleChoice(-1);
    setModuleTestResult(null);
    try {
      const { data: payload } = await startModuleTest(user.user_id, currentSkill.skill_id, selectedModule.module_id);
      setModuleTest(payload);
    } catch {
      setModuleTest(null);
    }
    setModuleTestLoading(false);
  };

  const handleSubmitModuleTest = async () => {
    if (!currentSkill || !selectedModule || moduleChoice < 0) return;
    setModuleTestLoading(true);
    try {
      const { data: payload } = await submitModuleTest(user.user_id, currentSkill.skill_id, selectedModule.module_id, moduleChoice);
      setModuleTestResult(payload);
      if (payload.passed) {
        await refreshUser();
        await reload();
      }
    } catch {
      setModuleTestResult({ passed: false, explanation: 'Submission failed.' });
    }
    setModuleTestLoading(false);
  };

  const handleStartFinal = async () => {
    if (!currentSkill) return;
    setFinalLoading(true);
    setFinalResult(null);
    try {
      const { data: payload } = await startFinalSkillTest(user.user_id, currentSkill.skill_id);
      setFinalTest(payload);
      setFinalChoices(new Array((payload.questions || []).length).fill(-1));
    } catch {
      setFinalTest(null);
    }
    setFinalLoading(false);
  };

  const handleSubmitFinal = async () => {
    if (!currentSkill || !finalTest) return;
    setFinalLoading(true);
    try {
      const { data: payload } = await submitFinalSkillTest(user.user_id, currentSkill.skill_id, finalChoices);
      setFinalResult(payload);
      if (payload.passed) {
        await refreshUser();
        await reload();
      }
    } catch {
      setFinalResult({ passed: false, score: 0, pass_score: 0 });
    }
    setFinalLoading(false);
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Skill Modules</h1>
        <p className="page-subtitle">Learn concept modules, clear tests, and pass final skill assessments to unlock next skills.</p>
      </div>

      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 60 }}><div className="spinner spinner-lg" /></div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          {skills.map((skill) => (
            <div key={skill.skill_id} className="card" style={{ opacity: skill.unlocked ? 1 : 0.65 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                <div>
                  <h3 style={{ fontSize: '1rem' }}>{skill.title}</h3>
                  <p style={{ fontSize: '0.82rem' }}>{skill.description}</p>
                </div>
                <span>{skill.unlocked ? (skill.completed ? <CheckCircle2 size={18} color="var(--accent-green)" /> : <Unlock size={18} color="var(--accent-cyan)" />) : <Lock size={18} />}</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {skill.modules.map((module, index) => (
                  <button
                    key={module.module_id}
                    onClick={() => { setSelectedSkill(skill); openLearning(module); }}
                    className="btn btn-secondary"
                    disabled={!skill.unlocked || module.status === 'locked'}
                    style={{ justifyContent: 'space-between' }}
                  >
                    <span style={{ textAlign: 'left' }}>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>Module {index + 1}</div>
                      <div style={{ fontWeight: 700 }}>{module.title}</div>
                    </span>
                    <ModuleStatusBadge status={module.status} />
                  </button>
                ))}
              </div>

              {skill.ready_for_final && !skill.final_passed && (
                <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                  <h4 style={{ fontSize: '0.9rem', marginBottom: 8 }}><Trophy size={14} style={{ marginRight: 6 }} />Final Skill Assessment</h4>
                  {!finalTest || selectedSkill?.skill_id !== skill.skill_id ? (
                    <button className="btn btn-primary" onClick={async () => { setSelectedSkill(skill); await handleStartFinal(); }} disabled={finalLoading}>
                      {finalLoading ? 'Loading...' : 'Start Final Test'}
                    </button>
                  ) : (
                    <>
                      {finalTest.questions?.map((q, qIdx) => (
                        <div key={qIdx} style={{ marginBottom: 10 }}>
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>{qIdx + 1}. {q.question}</div>
                          {q.options?.map((opt, oIdx) => (
                            <label key={oIdx} style={{ display: 'block', marginBottom: 4, fontSize: '0.82rem' }}>
                              <input
                                type="radio"
                                name={`final-${qIdx}`}
                                checked={finalChoices[qIdx] === oIdx}
                                onChange={() => {
                                  const next = [...finalChoices];
                                  next[qIdx] = oIdx;
                                  setFinalChoices(next);
                                }}
                                style={{ marginRight: 6 }}
                              />
                              {opt}
                            </label>
                          ))}
                        </div>
                      ))}
                      <button className="btn btn-green" onClick={handleSubmitFinal} disabled={finalLoading}>
                        {finalLoading ? 'Submitting...' : 'Submit Final Test'}
                      </button>
                      {finalResult && (
                        <div style={{ marginTop: 8, fontSize: '0.84rem', color: finalResult.passed ? 'var(--accent-green)' : '#f87171' }}>
                          {finalResult.passed ? 'Final passed ✅' : 'Final not passed ❌'} · Score: {finalResult.score}/{finalResult.pass_score}
                          {finalResult.unlocked_next_skill && (
                            <div style={{ color: 'var(--accent-cyan)' }}>Next skill unlocked: {finalResult.unlocked_next_skill}</div>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {learningOpen && selectedModule && currentSkill && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.65)',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 24,
          }}
          onClick={closeLearning}
        >
          <div
            className="card"
            onClick={(e) => e.stopPropagation()}
            style={{ width: 'min(980px, 95vw)', maxHeight: '90vh', overflow: 'auto', background: 'var(--bg-primary)' }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{currentSkill.title}</div>
                <h3 style={{ fontSize: '1.15rem' }}>{selectedModule.title}</h3>
              </div>
              <button className="btn btn-ghost btn-icon" onClick={closeLearning}><X size={18} /></button>
            </div>

            <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <BookOpen size={16} />
                <h4 style={{ fontSize: '0.92rem' }}>Dynamic Explanation</h4>
              </div>
              {expLoading ? (
                <div className="spinner" />
              ) : (
                <div style={{ fontSize: '0.84rem', lineHeight: 1.7 }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p style={{ marginBottom: '0.8rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>{children}</p>,
                      h1: ({ children }) => <h3 style={{ marginBottom: '0.5rem', marginTop: '0.3rem' }}>{children}</h3>,
                      h2: ({ children }) => <h4 style={{ marginBottom: '0.45rem', marginTop: '0.25rem' }}>{children}</h4>,
                      h3: ({ children }) => <h5 style={{ marginBottom: '0.4rem' }}>{children}</h5>,
                      ul: ({ children }) => <ul style={{ paddingLeft: 20, marginBottom: '0.75rem' }}>{children}</ul>,
                      ol: ({ children }) => <ol style={{ paddingLeft: 20, marginBottom: '0.75rem' }}>{children}</ol>,
                      li: ({ children }) => <li style={{ marginBottom: '0.35rem', color: 'var(--text-secondary)' }}>{children}</li>,
                      code: ({ className, children, ...props }) => {
                        const isBlock = String(className || '').includes('language-');
                        if (isBlock) {
                          return (
                            <pre style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: 10, padding: 10, overflowX: 'auto', marginBottom: '0.8rem' }}>
                              <code {...props}>{children}</code>
                            </pre>
                          );
                        }
                        return <code style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: 5 }} {...props}>{children}</code>;
                      },
                    }}
                  >
                    {explanation}
                  </ReactMarkdown>
                </div>
              )}
            </div>

            <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <MessageSquare size={16} />
                <h4 style={{ fontSize: '0.92rem' }}>Doubt Chatbot</h4>
              </div>
              <div ref={chatContainerRef} style={{ maxHeight: 280, overflowY: 'auto', marginBottom: 8, paddingRight: 4 }}>
                {chat.length === 0 && <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Ask a doubt about this module.</div>}
                {chat.map((m, i) => (
                  <div key={i} style={{ marginBottom: 7, fontSize: '0.82rem' }}>
                    <div style={{ color: m.role === 'user' ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                      <strong>{m.role === 'user' ? 'You' : 'Tutor'}:</strong>
                    </div>
                    {m.role === 'assistant' ? (
                      <div style={{ marginTop: 2, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ children }) => <p style={{ marginBottom: '0.55rem', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>{children}</p>,
                            ul: ({ children }) => <ul style={{ paddingLeft: 18, marginBottom: '0.6rem' }}>{children}</ul>,
                            ol: ({ children }) => <ol style={{ paddingLeft: 18, marginBottom: '0.6rem' }}>{children}</ol>,
                            li: ({ children }) => <li style={{ marginBottom: '0.3rem' }}>{children}</li>,
                            code: ({ className, children, ...props }) => {
                              const isBlock = String(className || '').includes('language-');
                              if (isBlock) {
                                return (
                                  <pre style={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border)', borderRadius: 10, padding: 10, overflowX: 'auto', marginBottom: '0.6rem' }}>
                                    <code {...props}>{children}</code>
                                  </pre>
                                );
                              }
                              return <code style={{ background: 'rgba(255,255,255,0.08)', padding: '2px 6px', borderRadius: 5 }} {...props}>{children}</code>;
                            },
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <div style={{ marginTop: 2, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{m.content}</div>
                    )}
                  </div>
                ))}
                {chatLoading && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Tutor is thinking...</div>}
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <input className="input" value={doubt} onChange={(e) => setDoubt(e.target.value)} placeholder="Ask your doubt..." />
                <button className="btn btn-primary" onClick={handleAskDoubt} disabled={chatLoading}>{chatLoading ? '...' : 'Ask'}</button>
              </div>
            </div>

            <div className="card" style={{ background: 'var(--bg-secondary)', border: '1px solid var(--border)' }}>
              <h4 style={{ fontSize: '0.92rem', marginBottom: 8 }}>Module Test (required to proceed)</h4>
              {!moduleTest ? (
                <button className="btn btn-primary" onClick={handleStartModuleTest} disabled={moduleTestLoading}>
                  {moduleTestLoading ? 'Loading...' : 'Start Module Test'}
                </button>
              ) : (
                <>
                  <p style={{ fontSize: '0.85rem', marginBottom: 8 }}>{moduleTest.question}</p>
                  {moduleTest.options?.map((option, idx) => (
                    <label key={idx} style={{ display: 'block', marginBottom: 6, fontSize: '0.82rem' }}>
                      <input
                        type="radio"
                        name="module-test"
                        checked={moduleChoice === idx}
                        onChange={() => setModuleChoice(idx)}
                        style={{ marginRight: 6 }}
                      />
                      {option}
                    </label>
                  ))}
                  <button className="btn btn-green" onClick={handleSubmitModuleTest} disabled={moduleTestLoading || moduleChoice < 0}>
                    {moduleTestLoading ? 'Submitting...' : 'Submit Module Test'}
                  </button>
                  {moduleTestResult && (
                    <div style={{ marginTop: 8, fontSize: '0.82rem', color: moduleTestResult.passed ? 'var(--accent-green)' : '#f87171' }}>
                      {moduleTestResult.passed ? 'Passed ✅' : 'Not passed ❌'}
                      <div style={{ color: 'var(--text-secondary)', marginTop: 4 }}>{moduleTestResult.explanation}</div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
