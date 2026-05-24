import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useAuth } from '../context/AuthContext';
import { runCode, explainPlaygroundCode, helpPlaygroundCode } from '../api';
import { Play, Bug, Lightbulb, Download, RotateCcw, CheckCircle, XCircle } from 'lucide-react';
import { ensureMonacoConfigured } from '../lib/monacoSetup';

const DEFAULT_CODE = {
  python: `# VoxMentor Code Playground 🚀
# Write your Python code here

def greet(name):
    return f"Hello, {name}! Welcome to VoxMentor."

print(greet("Coder"))

# Try changing the code and clicking Run!
`,
  javascript: `// VoxMentor Code Playground
function greet(name) {
  return \`Hello, \${name}! Welcome to VoxMentor.\`;
}

console.log(greet("Coder"));
`,
  c: `#include <stdio.h>

int main() {
    printf("Hello from VoxMentor!\\n");
    return 0;
}
`,
  cpp: `#include <iostream>
using namespace std;

int main() {
    cout << "Hello from VoxMentor!" << endl;
    return 0;
}
`,
};

function MistakeTag({ m }) {
  const colors = { error:'badge-pink', warning:'badge-orange', info:'badge-cyan' };
  return (
    <div style={{ display:'flex', gap:10, padding:'8px 0', borderBottom:'1px solid var(--border)' }}>
      <span className={`badge ${colors[m.severity]||'badge-cyan'}`} style={{ flexShrink:0 }}>{m.severity}</span>
      <span style={{ fontSize:'0.8rem', color:'var(--text-secondary)' }}>
        {m.line && <span style={{ color:'var(--text-muted)' }}>Line {m.line}: </span>}
        {m.description}
      </span>
    </div>
  );
}

export default function Playground() {
  const { user } = useAuth();
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState(DEFAULT_CODE.python);
  const [output, setOutput] = useState(null);
  const [mistakes, setMistakes] = useState([]);
  const [running, setRunning] = useState(false);
  const [aiMessages, setAiMessages] = useState([
    { role: 'assistant', content: 'I can explain your code, suggest fixes, and give hints to solve errors. Ask me anything about your current code.' },
  ]);
  const [aiQuestion, setAiQuestion] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [tab, setTab] = useState('output');
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

  const handleLangChange = (lang) => {
    setLanguage(lang);
    setCode(DEFAULT_CODE[lang]);
    setOutput(null);
    setMistakes([]);
    setAiQuestion('');
    setAiMessages([
      { role: 'assistant', content: `Language switched to ${lang === 'cpp' ? 'C++' : lang}. Share your goal and I’ll help complete your code.` },
    ]);
  };

  const handleRun = async () => {
    setRunning(true);
    try {
      const { data } = await runCode(code, language, user.user_id);
      setOutput(data);
      setMistakes(data.static_analysis || []);
      if (data.static_analysis?.length > 0) setTab('issues');
      else setTab('output');
    } catch { setOutput({ stdout:'', stderr:'Backend not running', success:false }); }
    setRunning(false);
  };

  const handleExplain = async () => {
    setAiLoading(true);
    setTab('ai');
    setAiMessages(prev => [
      ...prev,
      { role: 'user', content: output?.stderr ? 'Explain this code and error.' : 'Explain this code.' },
    ]);
    try {
      const { data } = await explainPlaygroundCode({
        user_id: user.user_id,
        code,
        language,
        stderr: output?.stderr || '',
      });
      setAiMessages(prev => [...prev, { role: 'assistant', content: data?.explanation || 'No explanation generated.' }]);
    } catch {
      setAiMessages(prev => [...prev, { role: 'assistant', content: '⚠️ AI explain is unavailable right now. Please retry.' }]);
    }
    setAiLoading(false);
  };

  const handleAskAiHelp = async (forcedQuestion = '') => {
    const question = (forcedQuestion || aiQuestion).trim();
    if (!question || aiLoading) return;

    setAiLoading(true);
    setTab('ai');
    setAiMessages(prev => [...prev, { role: 'user', content: question }]);
    setAiQuestion('');

    try {
      const { data } = await helpPlaygroundCode({
        user_id: user.user_id,
        code,
        question,
        language,
        stderr: output?.stderr || '',
      });
      setAiMessages(prev => [...prev, { role: 'assistant', content: data?.help || 'No help generated.' }]);
    } catch {
      setAiMessages(prev => [...prev, { role: 'assistant', content: '⚠️ AI help is unavailable right now. Please retry.' }]);
    }

    setAiLoading(false);
  };

  const handleAiQuestionKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleAskAiHelp();
    }
  };

  const download = () => {
    const ext = { python:'.py', javascript:'.js', c:'.c', cpp:'.cpp' }[language] || '.txt';
    const a = document.createElement('a');
    a.href = 'data:text/plain;charset=utf-8,' + encodeURIComponent(code);
    a.download = `voxmentor_code${ext}`;
    a.click();
  };

  const monacoLang = language === 'cpp' ? 'cpp' : language;

  return (
    <div className="fade-in" style={{ display:'flex', flexDirection:'column', height:'calc(100vh - 48px)' }}>
      {/* Header */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <div>
          <h1 style={{ fontSize:'1.4rem', fontWeight:800 }}>Code Playground</h1>
          <p style={{ fontSize:'0.8rem', color:'var(--text-muted)', marginTop:2 }}>Write, run, and get AI feedback on your code</p>
        </div>
        <div style={{ display:'flex', gap:8 }}>
          {['python','javascript','c','cpp'].map(l => (
            <button key={l} onClick={() => handleLangChange(l)}
              className={`btn ${language===l?'btn-primary':'btn-secondary'}`}
              style={{ padding:'6px 14px', fontSize:'0.78rem' }}>
              {l === 'cpp' ? 'C++' : l.charAt(0).toUpperCase()+l.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Editor + Output split */}
      <div style={{ display:'flex', flex:1, gap:16, minHeight:0 }}>
        {/* Editor */}
        <div style={{ flex:1, borderRadius:'var(--radius-lg)', overflow:'hidden', border:'1px solid var(--border)' }}>
          {/* Toolbar */}
          <div style={{
            display:'flex', alignItems:'center', gap:8, padding:'8px 14px',
            background:'var(--bg-secondary)', borderBottom:'1px solid var(--border)',
          }}>
            <div style={{ display:'flex', gap:6 }}>
              <div style={{ width:12, height:12, borderRadius:'50%', background:'#ff5f56' }} />
              <div style={{ width:12, height:12, borderRadius:'50%', background:'#ffbd2e' }} />
              <div style={{ width:12, height:12, borderRadius:'50%', background:'#27c93f' }} />
            </div>
            <span style={{ fontSize:'0.75rem', color:'var(--text-muted)', marginLeft:6 }}>
              {monacoLang === 'cpp' ? 'C++' : monacoLang} · VoxMentor Editor
            </span>
            <div style={{ marginLeft:'auto', display:'flex', gap:8 }}>
              <button className="btn btn-ghost btn-icon" onClick={() => setCode(DEFAULT_CODE[language])} title="Reset">
                <RotateCcw size={14} />
              </button>
              <button className="btn btn-ghost btn-icon" onClick={download} title="Download">
                <Download size={14} />
              </button>
            </div>
          </div>
          {monacoReady ? (
            <Editor
              height="100%"
              language={monacoLang}
              value={code}
              onChange={v => setCode(v || '')}
              theme="vs-dark"
              options={{
                fontSize: 14,
                fontFamily: 'JetBrains Mono, Fira Code, monospace',
                minimap: { enabled: false },
                lineNumbers: 'on',
                renderLineHighlight: 'gutter',
                scrollBeyondLastLine: false,
                padding: { top: 12, bottom: 12 },
                cursorBlinking: 'smooth',
                smoothScrolling: true,
              }}
            />
          ) : (
            <div style={{ height: '100%', display: 'grid', placeItems: 'center', color: 'var(--text-muted)' }}>
              Loading editor…
            </div>
          )}
        </div>

        {/* Right panel */}
        <div style={{ width:380, display:'flex', flexDirection:'column', gap:12 }}>
          {/* Run buttons */}
          <div style={{ display:'flex', gap:8 }}>
            <button className="btn btn-green" onClick={handleRun} disabled={running}
              style={{ flex:1, justifyContent:'center' }}>
              {running ? <div className="spinner" style={{ width:16,height:16 }} /> : <Play size={16} />}
              {running ? 'Running…' : 'Run Code'}
            </button>
            <button className="btn btn-secondary" onClick={handleExplain} disabled={aiLoading}
              style={{ flex:1, justifyContent:'center' }}>
              {aiLoading ? <div className="spinner" style={{ width:16,height:16 }} /> : <Lightbulb size={16} />}
              AI Explain
            </button>
          </div>

          {/* Tabs */}
          <div className="tab-bar">
            <button className={`tab-btn ${tab==='output'?'active':''}`} onClick={() => setTab('output')}>Output</button>
            <button className={`tab-btn ${tab==='issues'?'active':''}`} onClick={() => setTab('issues')}>
              Issues {mistakes.length > 0 && <span className="badge badge-orange" style={{ marginLeft:4, padding:'1px 7px' }}>{mistakes.length}</span>}
            </button>
            <button className={`tab-btn ${tab==='ai'?'active':''}`} onClick={() => setTab('ai')}>AI Help</button>
          </div>

          {/* Panel content */}
          <div style={{ flex:1, overflow:'hidden', display:'flex', flexDirection:'column' }}>
            {tab === 'output' && (
              <div style={{ display:'flex', flexDirection:'column', height:'100%', gap:8 }}>
                {output && (
                  <div style={{ display:'flex', gap:8, alignItems:'center' }}>
                    {output.success
                      ? <><CheckCircle size={16} color="var(--accent-green)" /> <span style={{ fontSize:'0.8rem', color:'var(--accent-green)' }}>Executed successfully</span></>
                      : <><XCircle size={16} color="#f87171" /> <span style={{ fontSize:'0.8rem', color:'#f87171' }}>Error occurred</span></>}
                  </div>
                )}
                <div className={`code-output ${output?.success===false?'error':output?.success?'success':''}`}
                  style={{ flex:1, overflowY:'auto' }}>
                  {output?.stdout || output?.stderr || (output===null ? '// Click "Run Code" to execute…' : '// (no output)')}
                </div>
              </div>
            )}
            {tab === 'issues' && (
              <div style={{ flex:1, overflowY:'auto' }}>
                {mistakes.length === 0
                  ? <div className="empty-state"><div className="empty-icon">✅</div><h3>No issues found!</h3><p>Your code looks clean.</p></div>
                  : mistakes.map((m, i) => <MistakeTag key={i} m={m} />)
                }
              </div>
            )}
            {tab === 'ai' && (
              <div style={{ flex:1, overflow:'hidden', display:'flex', flexDirection:'column' }}>
                <div style={{ display:'flex', gap:8, marginBottom:8 }}>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleAskAiHelp('Give me a hint to complete this code.')}
                    disabled={aiLoading}
                    style={{ flex:1, justifyContent:'center' }}
                  >
                    <Lightbulb size={14} /> Hint
                  </button>
                  <button
                    className="btn btn-secondary"
                    onClick={() => handleAskAiHelp(output?.stderr ? `Help me fix this error: ${output.stderr}` : 'Review my code and suggest one improvement.')}
                    disabled={aiLoading}
                    style={{ flex:1, justifyContent:'center' }}
                  >
                    <Bug size={14} /> Fix Error
                  </button>
                </div>

                <div style={{ flex:1, overflowY:'auto', padding:'4px 0 8px', fontSize:'0.83rem', lineHeight:1.6 }}>
                  {aiMessages.map((message, idx) => (
                    <div
                      key={idx}
                      className={`playground-ai-bubble ${message.role === 'user' ? 'user' : 'assistant'}`}
                      style={{
                        marginBottom: 10,
                        padding: '10px 12px',
                        borderRadius: 12,
                        background: message.role === 'user' ? 'var(--bg-secondary)' : 'var(--bg-glass)',
                        border: '1px solid var(--border)',
                        color: message.role === 'user' ? 'var(--text-primary)' : 'var(--text-secondary)',
                      }}
                    >
                      {message.role === 'assistant' ? (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            code(props) {
                              const { children, className, ...rest } = props;
                              const match = /language-(\w+)/.exec(className || '');
                              if (!match) {
                                return <code className="playground-inline-code" {...rest}>{children}</code>;
                              }
                              return (
                                <pre className="playground-code-block">
                                  <code {...rest}>{children}</code>
                                </pre>
                              );
                            },
                          }}
                        >
                          {message.content}
                        </ReactMarkdown>
                      ) : (
                        <span style={{ whiteSpace: 'pre-wrap' }}>{message.content}</span>
                      )}
                    </div>
                  ))}
                  {aiLoading && (
                    <div style={{ display:'flex', gap:8, padding:12 }}>
                      <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
                    </div>
                  )}
                </div>

                <div style={{ display:'flex', gap:8 }}>
                  <textarea
                    value={aiQuestion}
                    onChange={(e) => setAiQuestion(e.target.value)}
                    onKeyDown={handleAiQuestionKeyDown}
                    placeholder="Ask AI to help complete your code or fix errors..."
                    rows={2}
                    style={{
                      flex: 1,
                      resize: 'none',
                      borderRadius: 10,
                      border: '1px solid var(--border)',
                      background: 'var(--bg-secondary)',
                      color: 'var(--text-primary)',
                      padding: '8px 10px',
                      fontSize: '0.8rem',
                    }}
                    disabled={aiLoading}
                  />
                  <button
                    className="btn btn-primary"
                    onClick={() => handleAskAiHelp()}
                    disabled={!aiQuestion.trim() || aiLoading}
                    style={{ alignSelf:'stretch', justifyContent:'center' }}
                  >
                    Ask
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
