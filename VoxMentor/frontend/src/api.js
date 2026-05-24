import axios from 'axios';

const BACKEND_PORT = import.meta.env.VITE_BACKEND_PORT || '8000';
const API_BASE = import.meta.env.VITE_API_BASE_URL
  || `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}/api`;
const BACKEND_ORIGIN = API_BASE.replace(/\/api\/?$/, '');

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const isTransientNetworkError = (error) => {
  const code = error?.code || '';
  const message = String(error?.message || '').toLowerCase();
  return code === 'ERR_NETWORK' || message.includes('network error') || message.includes('connection refused');
};

async function postWithRetry(url, payload, retries = 1, delayMs = 700) {
  let lastError;
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    try {
      return await api.post(url, payload);
    } catch (error) {
      lastError = error;
      if (!isTransientNetworkError(error) || attempt === retries) break;
      await sleep(delayMs);
    }
  }
  throw lastError;
}

// Attach token from localStorage
api.interceptors.request.use(cfg => {
  const token = localStorage.getItem('voxmentor_token');
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});

// ── Auth ───────────────────────────────────────────────────────────
export const register = (data) => api.post('/users/register', data);
export const login    = (data) => api.post('/users/login', data);
export const getProfile = (uid) => api.get(`/users/profile/${uid}`);

// ── Chat (streaming) ───────────────────────────────────────────────
export async function* streamChat({ user_id, message, language, mode, session_id, onSessionId, signal }) {
  const token = localStorage.getItem('voxmentor_token');
  const resp = await fetch(`${API_BASE}/chat/`, {
    method: 'POST',
    signal,
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({ user_id, message, language, mode: mode || 'tutor', session_id: session_id || null }),
  });

  if (!resp.ok) {
    const errText = await resp.text().catch(() => '');
    throw new Error(errText || `Chat request failed with status ${resp.status}`);
  }
  if (!resp.body) {
    throw new Error('Chat response stream is unavailable');
  }

  const reader = resp.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      buffer += chunk;

      // Extract and strip the session ID marker \x00SID:{id}\x00 if present
      const sidMatch = buffer.match(/\x00SID:([a-f0-9]{24})\x00/);
      if (sidMatch) {
        if (onSessionId) onSessionId(sidMatch[1]);
        buffer = buffer.replace(/\x00SID:[a-f0-9]{24}\x00/g, '');
      }

      if (buffer) {
        yield buffer;
        buffer = '';
      }
    }
    if (buffer) yield buffer;
  } catch (error) {
    if (error?.name === 'AbortError' || signal?.aborted) {
      throw new Error('aborted');
    }
    throw new Error('Chat stream was interrupted. Please retry.');
  }
}

export const getSessions = (uid) => api.get(`/chat/sessions/${uid}`);
export const getSession  = (sid) => api.get(`/chat/session/${sid}`);

// ── Code ───────────────────────────────────────────────────────────
export const runCode      = (code, language, user_id) => api.post('/code/run', { code, language, user_id });
export const analyzeCode  = (code, language)           => api.post('/code/analyze', { code, language });
export const getLanguages = ()                          => api.get('/code/languages');
export const explainPlaygroundCode = (data)             => api.post('/code/ai-explain', data);
export const helpPlaygroundCode    = (data)             => api.post('/code/ai-help', data);

// ── Visualizer ─────────────────────────────────────────────────────
export const getPresets  = ()           => api.get('/visualize/presets');
export const visualize   = (algorithm, language, custom_input = '', custom_target = '') => api.post('/visualize/', { algorithm, language, custom_input, custom_target });

// ── Progress ───────────────────────────────────────────────────────
export const getProgress    = (uid)    => api.get(`/progress/${uid}`);
export const updateProgress = (data)   => api.post('/progress/update', data);
export const getProgressForecast = (uid) => api.get(`/learning-plus/forecast/${uid}`);

// ── Skill Tree ─────────────────────────────────────────────────────
export const getSkillTree  = (uid)    => api.get(`/skill-tree/${uid}`);
export const unlockNode    = (uid, node_id) => api.post('/skill-tree/unlock', { user_id: uid, node_id });
export const completeNode  = (uid, node_id) => api.post('/skill-tree/complete', { user_id: uid, node_id });
export const getSkillModules = (uid) => api.get(`/skill-tree/${uid}`);
export const getModuleExplanation = (user_id, skill_id, module_id) =>
  api.post('/skill-tree/module/explain', { user_id, skill_id, module_id });
export const askModuleDoubt = (user_id, skill_id, module_id, message) =>
  postWithRetry('/skill-tree/module/chat', { user_id, skill_id, module_id, message }, 1, 900);
export const startModuleTest = (user_id, skill_id, module_id) =>
  api.post('/skill-tree/module/test/start', { user_id, skill_id, module_id });
export const submitModuleTest = (user_id, skill_id, module_id, selected_index) =>
  api.post('/skill-tree/module/test/submit', { user_id, skill_id, module_id, selected_index });
export const startFinalSkillTest = (user_id, skill_id) =>
  api.post('/skill-tree/skill/final/start', { user_id, skill_id });
export const submitFinalSkillTest = (user_id, skill_id, selected_indices) =>
  api.post('/skill-tree/skill/final/submit', { user_id, skill_id, selected_indices });

// ── Learning+ (Adaptive, Roadmaps, Projects, Interviews, Revision) ─────────
export const getAdaptivePath = (user_id, skill_id = 'python_fundamentals') =>
  api.post('/learning-plus/adaptive-path', { user_id, skill_id });

export const createGoalRoadmap = (user_id, goal) =>
  api.post('/learning-plus/roadmap', { user_id, goal });
export const getGoalRoadmaps = (user_id) =>
  api.get(`/learning-plus/roadmap/${user_id}`);

export const startProjectLearning = (user_id, goal, language = 'python') =>
  api.post('/learning-plus/projects/start', { user_id, goal, language });
export const reviewProjectLearning = (user_id, project_id, code, notes = '') =>
  api.post('/learning-plus/projects/review', { user_id, project_id, code, notes });

export const startMockInterview = (user_id, difficulty = 'intermediate', language = 'python', duration_minutes = 30) =>
  api.post('/learning-plus/interview/start', { user_id, difficulty, language, duration_minutes });
export const getMockInterviewHint = (user_id, interview_id, question_index = 0) =>
  api.post('/learning-plus/interview/hint', { user_id, interview_id, question_index });
export const submitMockInterview = (user_id, interview_id, answers) =>
  api.post('/learning-plus/interview/submit', { user_id, interview_id, answers });

export const getSpacedRevisionQueue = (user_id) =>
  api.get(`/learning-plus/spaced-revision/${user_id}`);

// ── Practice ───────────────────────────────────────────────────────
export const generateChallenge = (data)   => api.post('/practice/generate', data);
export const getDailyChallenge = (uid, language = 'python') => {
  const safeLanguage = language && language !== 'undefined' ? language : 'python';
  return api.get(`/practice/daily/${uid}?language=${encodeURIComponent(safeLanguage)}`);
};
export const submitSolution    = (data)   => api.post('/practice/submit', data);

// ── Journal ────────────────────────────────────────────────────────
export const saveJournal = (data) => api.post('/journal/', data);
export const getJournal  = (uid)  => api.get(`/journal/${uid}`);

// ── System Health ───────────────────────────────────────────────────────────
export const getSystemHealth = () => axios.get(`${BACKEND_ORIGIN}/health`);

// ── Voice ──────────────────────────────────────────────────────────
export const speechToText = (audioBlob, options = {}) => {
  const form = new FormData();
  form.append('audio', audioBlob, 'recording.webm');
  if (options.modelId) {
    form.append('model_id', options.modelId);
  }
  return api.post('/voice/stt', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
export const textToSpeech = (text) => {
  const form = new FormData();
  form.append('text', text);
  return api.post('/voice/tts', form, {
    responseType: 'blob',
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

export default api;
