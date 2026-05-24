import { useState, useRef, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { streamChat, speechToText, textToSpeech } from '../api';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
  Send, Mic, MicOff, Volume2, Trash2, Cpu, 
  Sparkles, MessageSquare, Layout, Square
} from 'lucide-react';

const QUICK_PROMPTS = [
  'Explain how loops work',
  'What is recursion?',
  'Difference between list and tuple',
  'Memory allocation in C',
  'Big O notation guide',
];

function Message({ msg, onListen, voiceBusy }) {
  const isUser = msg.role === 'user';
  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 24,
      width: '100%',
      animation: 'fadeIn 0.4s ease forwards'
    }}>
      {!isUser && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10, marginLeft: 4 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 10, 
            background: 'var(--grad-ai)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 15px rgba(59, 201, 219, 0.3)'
          }}>
            <Cpu size={18} color="#fff" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-primary)', fontWeight: 600 }}>VoxMentor</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>AI Assistant</span>
          </div>
        </div>
      )}
      
      <div className={`chat-bubble ${isUser ? 'user' : 'assistant glass'}`} style={{
        maxWidth: isUser ? '80%' : '100%',
        padding: isUser ? '12px 20px' : '24px',
        borderRadius: isUser ? '16px 16px 4px 16px' : '20px',
        border: isUser ? 'none' : '1px solid var(--border-glass)',
        background: isUser ? 'var(--grad-primary)' : 'var(--bg-glass)',
        boxShadow: isUser ? '0 8px 20px rgba(79, 140, 255, 0.25)' : 'var(--shadow-md)',
        color: 'var(--text-primary)',
        fontSize: '0.95rem',
        lineHeight: 1.7
      }}>
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <ReactMarkdown remarkPlugins={[remarkGfm]}
            components={{
              code(props) {
                const { children, className, node, ...rest } = props;
                const match = /language-(\w+)/.exec(className || '');
                return !match
                  ? <code style={{ background:'rgba(0,0,0,0.3)', padding:'2px 6px', borderRadius:4, fontFamily:'var(--font-code)', fontSize:'0.85em', color: 'var(--accent-cyan)' }} {...rest}>{children}</code>
                  : (
                    <div style={{ margin:'20px 0', borderRadius:'12px', overflow:'hidden', border:'1px solid var(--border)' }}>
                      <div style={{ background:'var(--bg-secondary)', padding:'10px 16px', fontSize:'0.75rem', color:'var(--text-muted)', fontWeight:600, display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)' }}>
                        <span style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}>{match[1] || 'code'}</span>
                        <button style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: '0.7rem' }}>Copy Code</button>
                      </div>
                      <pre style={{ background:'#0d1117', padding:'18px', margin:0, overflowX:'auto', fontFamily:'var(--font-code)', fontSize:'0.85rem', color:'#e6edf3' }}>
                        <code>{children}</code>
                      </pre>
                    </div>
                  );
              },
              p: ({ children }) => <div style={{ marginBottom: '1.2rem' }}>{children}</div>,
              h2: ({ children }) => <h3 style={{ marginTop:24, marginBottom:12, color:'var(--text-primary)', fontSize:'1.1rem', fontWeight: 700 }}>{children}</h3>,
              h3: ({ children }) => <h4 style={{ marginTop:18, marginBottom:8, color:'var(--text-primary)', fontSize:'1rem', fontWeight: 600 }}>{children}</h4>,
              ul: ({ children }) => <ul style={{ paddingLeft:24, margin:'12px 0' }}>{children}</ul>,
              li: ({ children }) => <li style={{ marginBottom:6, color:'var(--text-secondary)' }}>{children}</li>,
            }}
          >
            {msg.content}
          </ReactMarkdown>
        )}
      </div>
      
      {!isUser && msg.content && !msg.streaming && (
        <div style={{ display: 'flex', gap: 12, marginTop: 12, marginLeft: 4 }}>
          <button className="btn-ghost" style={{ fontSize: '0.75rem', gap: 4 }}><Sparkles size={14} /> Regenerate</button>
          <button
            className="btn-ghost"
            style={{ fontSize: '0.75rem', gap: 4 }}
            onClick={() => onListen?.(msg.content)}
            disabled={voiceBusy}
          >
            <Volume2 size={14} /> Listen
          </button>
        </div>
      )}
    </div>
  );
}

export default function Chat() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const [messages, setMessages] = useState([{
    role: 'assistant',
    content: `Hello **${user?.name?.split(' ')[0] || 'there'}**. I'm VoxMentor, your AI programming companion. 

I'm ready to assist with structured tutoring, debugging, or code analysis. What's on your mind today?`,
  }]);
  const [input, setInput] = useState(searchParams.get('topic') || '');
  const [sessionId, setSessionId] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceBusy, setVoiceBusy] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [transcribing, setTranscribing] = useState(false);
  const [cloudSttEnabled, setCloudSttEnabled] = useState(() => localStorage.getItem('voxmentor_cloud_stt_disabled') !== '1');
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);
  const audioRef = useRef(null);
  const audioUrlRef = useRef('');
  const ttsSessionRef = useRef(0);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  const sendMessage = async (text = input) => {
    if (!text.trim() || streaming) return;
    const userMsg = { role:'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setStreaming(true);
    abortControllerRef.current = new AbortController();

    const aiMsg = { role:'assistant', content:'', streaming: true };
    setMessages(prev => [...prev, aiMsg]);

    try {
      for await (const chunk of streamChat({
        user_id: user.user_id, message: text, language: 'python', mode: 'auto',
        session_id: sessionId,
        onSessionId: (id) => setSessionId(id),
        signal: abortControllerRef.current.signal,
      })) {
        aiMsg.content += chunk;
        setMessages(prev => [...prev.slice(0, -1), { ...aiMsg }]);
      }
      setMessages(prev => [...prev.slice(0, -1), { ...aiMsg, streaming: false }]);
    } catch (error) {
      if (error?.message === 'aborted') {
        if (!aiMsg.content.trim()) {
          aiMsg.content = 'Reply stopped.';
        }
        setMessages(prev => [...prev.slice(0, -1), { ...aiMsg, streaming: false }]);
      } else {
        aiMsg.content = 'System Error: Failed to establish connection with the AI engine. Please verify your environment configuration and API credentials.';
        setMessages(prev => [...prev.slice(0, -1), { ...aiMsg, streaming: false }]);
      }
    }
    abortControllerRef.current = null;
    setStreaming(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      const chunks = [];
      mr.ondataavailable = e => chunks.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        try {
          setTranscribing(true);

          const submitTranscript = async (text) => {
            if (!text?.trim()) return false;
            setInput(text);
            if (!streaming) {
              await sendMessage(text);
            }
            return true;
          };

          if (!cloudSttEnabled) {
            const localText = await transcribeLocally();
            if (!(await submitTranscript(localText))) {
              alert('Local STT failed. Please try again.');
            }
            return;
          }

          const audioBlob = new Blob(chunks, { type: 'audio/webm' });
          const runtimeSttModel = import.meta.env.VITE_ELEVENLABS_STT_MODEL_ID || 'scribe_v1';
          const resp = await speechToText(audioBlob, { modelId: runtimeSttModel });
          const text = resp?.data?.transcript?.trim();
          if (await submitTranscript(text)) {
            return;
          }
          const fallbackText = await transcribeLocally();
          if (!(await submitTranscript(fallbackText))) {
            alert('STT did not return text. Please try again.');
          }
        } catch (error) {
          const fallbackText = await transcribeLocally();
          if (await submitTranscript(fallbackText)) {
            return;
          }

          const status = error?.response?.status;
          if (status === 401) {
            setCloudSttEnabled(false);
            localStorage.setItem('voxmentor_cloud_stt_disabled', '1');
            alert('ElevenLabs STT is unauthorized for this key/account. Switched to local STT fallback for this browser session.');
          } else {
            alert('STT failed. Please try again.');
          }
        } finally {
          setTranscribing(false);
        }
      };
      mr.start();
      setMediaRecorder(mr);
      setRecording(true);
    } catch { alert('Microphone permission denied'); }
  };

  const stopRecording = () => { mediaRecorder?.stop(); setRecording(false); };

  const retryCloudStt = () => {
    setCloudSttEnabled(true);
    localStorage.removeItem('voxmentor_cloud_stt_disabled');
  };

  const transcribeLocally = () => new Promise((resolve) => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      resolve('');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onresult = (event) => {
      const text = event?.results?.[0]?.[0]?.transcript || '';
      resolve(text.trim());
    };
    recognition.onerror = () => resolve('');
    recognition.onend = () => resolve('');

    try {
      recognition.start();
      setTimeout(() => recognition.stop(), 4500);
    } catch {
      resolve('');
    }
  });

  const splitTextForTts = (text, maxChars = 1200) => {
    const normalized = (text || '').replace(/\s+/g, ' ').trim();
    if (!normalized) return [];

    const sentences = normalized.split(/(?<=[.!?])\s+/);
    const chunks = [];
    let current = '';

    for (const sentence of sentences) {
      if (!sentence) continue;
      if ((current + ' ' + sentence).trim().length <= maxChars) {
        current = (current ? `${current} ${sentence}` : sentence).trim();
        continue;
      }
      if (current) chunks.push(current);

      if (sentence.length <= maxChars) {
        current = sentence;
      } else {
        for (let index = 0; index < sentence.length; index += maxChars) {
          chunks.push(sentence.slice(index, index + maxChars));
        }
        current = '';
      }
    }
    if (current) chunks.push(current);
    return chunks;
  };

  const playTextAsSpeech = async (text) => {
    if (voiceBusy) return;
    if (!text?.trim()) return;

    try {
      ttsSessionRef.current += 1;
      const sessionId = ttsSessionRef.current;
      setVoiceBusy(true);
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (audioUrlRef.current) {
        URL.revokeObjectURL(audioUrlRef.current);
        audioUrlRef.current = '';
      }

      const plainText = text.replace(/[#*_`>\-]/g, ' ');
      const chunks = splitTextForTts(plainText, 1200);
      for (const chunk of chunks) {
        if (sessionId !== ttsSessionRef.current) break;

        const response = await textToSpeech(chunk);
        const blob = response.data;
        const url = URL.createObjectURL(blob);
        audioUrlRef.current = url;

        await new Promise((resolve, reject) => {
          const audio = new Audio(url);
          audioRef.current = audio;
          audio.onended = () => {
            URL.revokeObjectURL(url);
            if (audioUrlRef.current === url) audioUrlRef.current = '';
            audioRef.current = null;
            resolve(true);
          };
          audio.onerror = () => {
            URL.revokeObjectURL(url);
            if (audioUrlRef.current === url) audioUrlRef.current = '';
            audioRef.current = null;
            reject(new Error('audio_playback_failed'));
          };
          audio.play().catch(reject);
        });
      }
    } catch {
      // no-op
    } finally {
      setVoiceBusy(false);
    }
  };

  const speakResponse = async () => {
    const lastAssistantMessage = [...messages].reverse().find(
      (message) => message.role === 'assistant' && message.content?.trim()
    );
    if (!lastAssistantMessage) return;
    await playTextAsSpeech(lastAssistantMessage.content);
  };

  const stopAll = () => {
    ttsSessionRef.current += 1;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (recording) {
      stopRecording();
    }
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = '';
    }
    setVoiceBusy(false);
    setStreaming(false);
  };

  useEffect(() => () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = '';
    }
  }, []);

  return (
    <div className="fade-in" style={{ 
      display:'flex', flexDirection:'column', height:'calc(100vh - 64px)', 
      maxWidth: 1000, margin: '0 auto', position: 'relative' 
    }}>
      {/* Background Glows */}
      <div className="bg-orb orb-cyan" />
      <div className="bg-orb orb-purple" />

      {/* Header Panel */}
      <div className="glass" style={{ 
        display:'flex', justifyContent:'space-between', alignItems:'center', 
        padding: '16px 24px', borderRadius: 16, marginBottom: 24,
        border: '1px solid var(--border-glass)'
      }}>
        <div style={{ display:'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ 
            width: 40, height: 40, borderRadius: 12, background: 'rgba(59, 201, 219, 0.1)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(59, 201, 219, 0.2)'
          }}>
            <MessageSquare size={20} color="var(--accent-cyan)" />
          </div>
          <div>
            <h1 style={{ fontSize:'1.1rem', fontWeight:700, margin: 0 }}>AI Tutor Workspace</h1>
          </div>
        </div>
        
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          <button className="btn btn-secondary btn-icon" onClick={speakResponse} title="Read last response" disabled={voiceBusy}>
            <Volume2 size={16} />
          </button>
          <button
            className="btn btn-secondary btn-icon"
            onClick={stopAll}
            title="Stop AI reply and audio"
            disabled={!streaming && !voiceBusy && !recording}
          >
            <Square size={16} />
          </button>
          <button className="btn btn-secondary btn-icon" onClick={() => { setMessages(messages[0] ? [messages[0]] : []); setSessionId(null); }} title="Clear chat">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* Main Chat Content */}
      <div className="chat-messages" style={{ 
        flex:1, overflowY:'auto', paddingRight:8, 
        display:'flex', flexDirection:'column',
        marginBottom: 20
      }}>
        {messages.map((msg, i) => (
          <Message
            key={i}
            msg={msg}
            onListen={playTextAsSpeech}
            voiceBusy={voiceBusy}
          />
        ))}
        
        {streaming && (
          <div style={{ display:'flex', gap:8, alignSelf:'flex-start', padding:'16px 24px', background:'var(--bg-glass)', borderRadius: 20, border: '1px solid var(--border-glass)' }}>
            <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Bottom Area */}
      <div style={{ position: 'sticky', bottom: 0, paddingBottom: 10, background: 'transparent' }}>
        
        {/* Quick Prompts */}
        {messages.length <= 1 && (
          <div style={{ display:'flex', gap:10, flexWrap:'wrap', justifyContent: 'center', marginBottom: 20 }}>
            {QUICK_PROMPTS.map(p => (
              <button key={p} onClick={() => sendMessage(p)}
                style={{ 
                  padding:'8px 16px', borderRadius: 20, background:'var(--bg-glass)',
                  border:'1px solid var(--border-glass)', color:'var(--text-secondary)', fontSize:'0.8rem',
                  cursor:'pointer', transition:'var(--transition)', fontWeight: 500
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor='var(--accent-cyan)'; e.currentTarget.style.color='var(--text-primary)'; e.currentTarget.style.background='var(--bg-card-hover)'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor='var(--border-glass)'; e.currentTarget.style.color='var(--text-secondary)'; e.currentTarget.style.background='var(--bg-glass)'; }}
              >{p}</button>
            ))}
          </div>
        )}

        {/* Input Bar */}
        <div className="glass" style={{ 
          padding:'12px', borderRadius: 20, border: '1px solid var(--border-glass)',
          boxShadow: '0 20px 50px rgba(0,0,0,0.4)', position: 'relative'
        }}>
          <div style={{ display:'flex', gap:12, alignItems:'center' }}>
            <textarea ref={textareaRef}
              className="input-glow"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={'Ask VoxMentor anything...'}
              rows={1}
              style={{ 
                flex:1, background: 'transparent', border: 'none', padding: '12px 0',
                resize:'none', minHeight: 48, maxHeight: 200, fontSize: '1rem',
                color: 'var(--text-primary)', outline: 'none'
              }}
              disabled={streaming || transcribing}
            />

            <div style={{ display: 'flex', gap: 10, paddingRight: 4 }}>
              <button className={`btn ${recording ? 'btn-danger' : 'btn-glass'}`}
                onClick={recording ? stopRecording : startRecording}
                disabled={streaming || transcribing}
                style={{
                  width: 46,
                  height: 46,
                  borderRadius: 14,
                  position:'relative',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: 0,
                }}>
                {recording && <span className="voice-ring" />}
                {recording ? <MicOff size={28} /> : <Mic size={28} />}
              </button>
              
              <button className="btn btn-primary" onClick={() => (streaming ? stopAll() : sendMessage())}
                disabled={(!input.trim() && !streaming) || transcribing} 
                style={{ width: 46, height: 46, padding: 0, borderRadius: 14 }}>
                {streaming ? <Square size={18} /> : <Send size={20} />}
              </button>
            </div>
          </div>
        </div>
        
        <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 12 }}>
          {!cloudSttEnabled && (
            <button
              className="btn-ghost"
              onClick={retryCloudStt}
              style={{ fontSize:'0.75rem', color:'var(--warning)', fontWeight: 600 }}
              title="Retry ElevenLabs STT"
            >
              Cloud STT disabled (401). Click to retry.
            </button>
          )}
          <span style={{ fontSize:'0.75rem', color:'var(--text-muted)', fontWeight: 500 }}>
             <Layout size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> Shift + Enter for new line
          </span>
          <span style={{ fontSize:'0.75rem', color:'var(--text-muted)', fontWeight: 500 }}>
             <Sparkles size={12} style={{ verticalAlign: 'middle', marginRight: 4 }} /> Powered by VoxMentor AI Engine
          </span>
        </div>
      </div>
    </div>
  );
}
